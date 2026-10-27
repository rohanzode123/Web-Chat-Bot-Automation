"""
Playwright-based test runner for RZ-Work web chatbot.
Handles page lifecycle, iframe detection, human-like typing,
typing-indicator waiting, multi-turn flows, and retries.
"""

import os
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Locator

from comparator import AnswerComparator, ComparisonResult
from reporter import TestReporter


class ChatbotRunner:
    def __init__(self, config: Dict[str, Any], reporter: TestReporter, comparator: AnswerComparator):
        self.config = config
        self.reporter = reporter
        self.comparator = comparator

        # Bot and Execution settings
        self.bot_url = config["bot"]["url"]
        self.headless = config["bot"].get("headless", True)
        self.viewport = config["bot"].get("viewport", {"width": 1280, "height": 800})
        
        # Selectors
        self.selectors = config.get("selectors", {})
        self.iframe_selector = self.selectors.get("iframe")
        self.input_selector = self.selectors.get(
            "input_box",
            "input[placeholder*='message' i], input[class*='_input_'], input[type='text'], input[type='tel']"
        )
        self.send_btn_selector = self.selectors.get(
            "send_button",
            "button[aria-label='Send message'], button[class*='_sendButton']"
        )
        self.bot_bubble_selector = self.selectors.get(
            "bot_message_bubble",
            "div[data-bot-messagebox-bubble='true'], div[class*='_messageWrapper_'], div[class*='_greeting_']"
        )
        self.user_bubble_selector = self.selectors.get(
            "user_message_bubble",
            "div[class*='_userMessageBox_'], div[class*='_userMessage']"
        )
        self.typing_selector = self.selectors.get(
            "typing_indicator",
            "div[class*='_loader_'], div[class*='typing'], div[class*='_loaderGlass_']"
        )
        self.button_selector = self.selectors.get(
            "quick_reply_button",
            "button:not([aria-label]), div[role='button']"
        )

        # Timeouts
        self.timeouts = config.get("timeouts", {})
        self.page_load_ms = self.timeouts.get("page_load_ms", 60000)
        self.greeting_wait_ms = self.timeouts.get("greeting_wait_ms", 15000)
        self.bot_reply_timeout_s = float(self.timeouts.get("bot_reply_timeout_s", 30))
        self.quiet_period_s = float(self.timeouts.get("quiet_period_s", 3.0))
        self.typing_delay_ms = int(self.timeouts.get("typing_delay_ms", 40))

        # Retries & Screenshots
        self.max_retries = int(config.get("execution", {}).get("max_retries", 2))
        self.screenshot_on_failure = config.get("execution", {}).get("screenshot_on_failure", True)
        self.screenshots_dir = config.get("execution", {}).get("screenshots_dir", "screenshots")
        os.makedirs(self.screenshots_dir, exist_ok=True)

        # Internal state
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.current_frame = None  # None means main page
        self.current_bot_bubble_count = 0

    async def start_browser(self, headless: Optional[bool] = None):
        """Launch the Playwright browser."""
        if headless is not None:
            self.headless = headless
            
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )

    async def close_browser(self):
        """Close browser and clean up Playwright resources."""
        if self.context:
            await self.context.close()
            self.context = None
        if self.browser:
            await self.browser.close()
            self.browser = None
        if hasattr(self, "playwright") and self.playwright:
            await self.playwright.stop()
            self.playwright = None

    async def start_new_session(self, pre_messages: Optional[List[str]] = None) -> bool:
        """
        Open a clean page session, wait for widget greeting to load,
        and optionally send pre-messages.
        """
        if self.context:
            await self.context.close()

        self.context = await self.browser.new_context(viewport=self.viewport)
        self.page = await self.context.new_page()

        # Navigate to the preview URL
        await self.page.goto(self.bot_url, wait_until="networkidle", timeout=self.page_load_ms)

        # Detect iframe if needed
        self.current_frame = None
        if self.iframe_selector:
            try:
                frame_loc = self.page.frame_locator(self.iframe_selector)
                # verify input exists inside frame
                if await frame_loc.locator(self.input_selector).count() > 0:
                    self.current_frame = frame_loc
            except Exception:
                pass

        # If not explicitly matched, auto-detect across page frames
        if not self.current_frame:
            for frame in self.page.frames:
                if frame != self.page.main_frame:
                    try:
                        if await frame.locator(self.input_selector).count() > 0:
                            self.current_frame = frame
                            break
                    except Exception:
                        pass

        # Target context (page or frame)
        target = self.current_frame if self.current_frame else self.page

        # Wait for input box to appear
        input_loc = target.locator(self.input_selector).first
        await input_loc.wait_for(state="visible", timeout=self.greeting_wait_ms)

        # Wait for bot greeting to stabilize
        await self.page.wait_for_timeout(3000)

        # Initialize bot bubble count for this fresh session
        # On fresh load, the welcome greeting counts as bubble 0
        bubbles = await self._get_bot_bubbles()
        self.current_bot_bubble_count = max(len(bubbles), 1)

        # Handle PreMessages if specified
        if pre_messages:
            for pmsg in pre_messages:
                if str(pmsg).strip():
                    await self._send_single_message(str(pmsg).strip())
                    _, _, _, self.current_bot_bubble_count = await self._wait_for_bot_reply(
                        previous_count=self.current_bot_bubble_count
                    )

        return True

    async def _get_target(self):
        """Returns the active page or frame."""
        return self.current_frame if self.current_frame else self.page

    async def _get_bot_bubbles(self) -> List[Dict[str, Any]]:
        """
        Extract all distinct bot message bubbles and any buttons/quick replies
        associated with them. Scopes within the active conversation stream
        to prevent capturing background welcome layer artifacts.
        """
        target = await self._get_target()
        return await target.evaluate('''() => {
            const conv = document.querySelector('div[class*="_conversation_"]');
            const root = conv || document.body;
            const selectors = [
                'div[data-bot-messagebox-bubble="true"]',
                'div[class*="_messageWrapper_"]'
            ];
            if (!conv) {
                selectors.push('div[class*="_greeting_"]');
            }
            
            const botEls = Array.from(root.querySelectorAll(selectors.join(',')));
            
            // Filter out nested duplicates
            const distinct = [];
            for (const el of botEls) {
                if (!distinct.some(parent => parent.contains(el) && parent !== el)) {
                    distinct.push(el);
                }
            }
            
            return distinct.map(el => {
                const buttons = Array.from(
                    el.querySelectorAll('button:not([aria-label]), div[role="button"], [class*="quickReply"]')
                ).map(b => (b.innerText || '').trim()).filter(Boolean);
                
                return {
                    text: (el.innerText || '').trim(),
                    buttons: buttons
                };
            });
        }''')

    async def _send_single_message(self, text: str):
        """Type and send a single text message or click a matching button."""
        target = await self._get_target()

        # Check if text exactly matches a clickable button/chip on screen
        button_matches = target.locator(f"button:has-text(\"{text}\")")
        if await button_matches.count() > 0 and await button_matches.first.is_visible():
            await button_matches.first.click()
            return

        input_loc = target.locator(self.input_selector).first
        await input_loc.click()

        # Clear input first
        await input_loc.fill("")
        
        # Human-like typing
        await input_loc.press_sequentially(text, delay=self.typing_delay_ms)
        await self.page.wait_for_timeout(200)

        # Press Enter
        await self.page.keyboard.press("Enter")
        await self.page.wait_for_timeout(300)

        # Fallback: if input is still not empty, click send button
        val = await input_loc.input_value()
        if val.strip():
            send_btn = target.locator(self.send_btn_selector).first
            if await send_btn.count() > 0 and await send_btn.is_visible():
                await send_btn.click()

    async def _wait_for_bot_reply(
        self,
        previous_count: int
    ) -> Tuple[str, int, int, int]:
        """
        Wait until bot replies and typing stops.
        Returns: (actual_answer, first_reply_ms, last_reply_ms, new_total_count)
        """
        target = await self._get_target()
        t_start = time.perf_counter()
        first_reply_ms: Optional[int] = None
        last_reply_ms: Optional[int] = None
        last_seen_count = previous_count
        last_change_time = time.perf_counter()

        while (time.perf_counter() - t_start) < self.bot_reply_timeout_s:
            await self.page.wait_for_timeout(250)
            now = time.perf_counter()

            current_bubbles = await self._get_bot_bubbles()

            # Check typing indicator
            is_typing = await target.evaluate('''() => {
                const loaders = document.querySelectorAll(
                    'div[class*=\"_loader_\"], div[class*=\"typing\"], div[class*=\"_loaderGlass_\"]'
                );
                return loaders.length > 0;
            }''')

            # Did a new bubble arrive?
            if len(current_bubbles) > last_seen_count:
                if first_reply_ms is None:
                    first_reply_ms = round((now - t_start) * 1000)
                last_reply_ms = round((now - t_start) * 1000)
                last_seen_count = len(current_bubbles)
                last_change_time = now
            elif len(current_bubbles) > previous_count and not is_typing:
                # No new messages for quiet_period_s and typing stopped
                if (now - last_change_time) >= self.quiet_period_s:
                    break

        # Final snapshot of bubbles
        final_bubbles = await self._get_bot_bubbles()
        new_bubbles = final_bubbles[previous_count:]

        # Join new bubbles and format buttons
        bubble_texts = []
        for b in new_bubbles:
            txt = b["text"]
            # Append buttons if they are not already part of the text
            if b["buttons"]:
                btn_str = ", ".join(b["buttons"])
                if not any(btn in txt for btn in b["buttons"]):
                    txt += f"\n[Buttons: {btn_str}]"
            if txt:
                bubble_texts.append(txt)

        actual_answer = "\n".join(bubble_texts)
        return (
            actual_answer,
            first_reply_ms or (last_reply_ms or 0),
            last_reply_ms or 0,
            len(final_bubbles)
        )

    async def _capture_failure_screenshot(self, test_id: str) -> str:
        """Capture and save a failure screenshot."""
        if not self.screenshot_on_failure or not self.page:
            return ""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in test_id)
        path = os.path.join(self.screenshots_dir, f"{safe_id}_{timestamp}.png")
        try:
            await self.page.screenshot(path=path)
            return path
        except Exception:
            return ""

    async def run_step(
        self,
        test_case: Dict[str, Any],
        is_multi_turn: bool = False,
        pre_messages: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Execute a single test case step with automatic retry on failure/error.
        """
        test_id = str(test_case.get("TestID", ""))
        question = str(test_case.get("Question", ""))
        expected = str(test_case.get("ExpectedAnswer", ""))
        category = str(test_case.get("Category", "General"))
        mode = test_case.get("Mode") or self.comparator.default_mode

        last_result: Optional[Dict[str, Any]] = None

        for attempt in range(1 + self.max_retries):
            is_retry = attempt > 0
            self.reporter.log_test_start(test_id, question, category, is_retry=is_retry)

            try:
                # If first attempt and not multi-turn continuation, start fresh session
                if not is_multi_turn or is_retry:
                    await self.start_new_session(pre_messages=pre_messages)

                # Send question
                await self._send_single_message(question)

                # Wait for bot response
                actual_answer, first_ms, last_ms, new_count = await self._wait_for_bot_reply(
                    previous_count=self.current_bot_bubble_count
                )
                self.current_bot_bubble_count = new_count

                # If no answer arrived within timeout
                if not actual_answer.strip():
                    status = "TIMEOUT"
                    score = 0.0
                    reason = f"No bot response received within {self.bot_reply_timeout_s}s timeout"
                else:
                    # Compare answer
                    comp: ComparisonResult = self.comparator.compare(
                        expected=expected,
                        actual=actual_answer,
                        mode=mode
                    )
                    status = comp.status
                    score = comp.score
                    reason = comp.reason

                screenshot_path = ""
                if status != "PASS":
                    screenshot_path = await self._capture_failure_screenshot(test_id)

                last_result = {
                    "TestID": test_id,
                    "Category": category,
                    "Question": question,
                    "ExpectedAnswer": expected,
                    "ActualAnswer": actual_answer,
                    "Status": status,
                    "Score": score,
                    "Reason": reason,
                    "ResponseTimeMs": last_ms,
                    "Screenshot": screenshot_path
                }

                # If passed, no retry needed
                if status == "PASS":
                    self.reporter.log_test_result(last_result)
                    return last_result

            except Exception as e:
                screenshot_path = await self._capture_failure_screenshot(test_id)
                last_result = {
                    "TestID": test_id,
                    "Category": category,
                    "Question": question,
                    "ExpectedAnswer": expected,
                    "ActualAnswer": "",
                    "Status": "ERROR",
                    "Score": 0.0,
                    "Reason": f"Error: {str(e)}",
                    "ResponseTimeMs": 0,
                    "Screenshot": screenshot_path
                }

            # If failed/errored on this attempt, log warning
            if attempt < self.max_retries:
                print(f"  [Attempt {attempt + 1} failed ({last_result.get('Status')}): Retrying...]")
                await self.page.wait_for_timeout(2000)

        # Return final result after all retries exhausted
        self.reporter.log_test_result(last_result)
        return last_result
