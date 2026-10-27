"""
Playwright chatbot automation runner for Bot Test Studio.
Handles real-time WebSocket event emission, human typing emulation,
`CLICK:` directive, multi-turn flows, typing indicator waits,
and pause/resume/stop control.
"""

import os
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Callable
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

import sys
sys.path.insert(0, os.path.dirname(__file__))

from judge import AnswerJudge, ComparisonResult


class AutomationRunner:
    def __init__(
        self,
        config: Dict[str, Any],
        judge: AnswerJudge,
        event_callback: Optional[Callable[[str, Dict[str, Any]], Any]] = None
    ):
        self.config = config
        self.judge = judge
        self.event_callback = event_callback

        # Config parameters
        self.bot_url = config.get("bot", {}).get("url", "")
        self.headless = config.get("bot", {}).get("headless", True)
        self.viewport = config.get("bot", {}).get("viewport", {"width": 1280, "height": 800})

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
        self.typing_selector = self.selectors.get(
            "typing_indicator",
            "div[class*='_loader_'], div[class*='typing'], div[class*='_loaderGlass_']"
        )

        self.timeouts = config.get("timeouts", {})
        self.page_load_ms = self.timeouts.get("page_load_ms", 60000)
        self.greeting_wait_ms = self.timeouts.get("greeting_wait_ms", 15000)
        self.bot_reply_timeout_s = float(self.timeouts.get("bot_reply_timeout_s", 30))
        self.quiet_period_s = float(self.timeouts.get("quiet_period_s", 3.0))
        self.typing_delay_ms = int(self.timeouts.get("typing_delay_ms", 40))
        self.message_delay_ms = int(self.timeouts.get("message_delay_ms", 800))

        self.max_retries = int(config.get("execution", {}).get("max_retries", 2))
        self.screenshot_on_failure = config.get("execution", {}).get("screenshot_on_failure", True)
        self.screenshots_dir = config.get("execution", {}).get("screenshots_dir", "screenshots")
        os.makedirs(self.screenshots_dir, exist_ok=True)

        # Control flags
        self.is_paused = False
        self.is_stopped = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Unpaused initially

        # Browser state
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.current_frame = None
        self.current_bot_bubble_count = 0

    async def emit(self, event_type: str, data: Dict[str, Any]):
        """Emit live event to listener (e.g. WebSocket)."""
        if self.event_callback:
            try:
                res = self.event_callback(event_type, data)
                if asyncio.iscoroutine(res):
                    await res
            except Exception:
                pass

    def pause(self):
        """Pause execution."""
        self.is_paused = True
        self._pause_event.clear()

    def resume(self):
        """Resume execution."""
        self.is_paused = False
        self._pause_event.set()

    def stop(self):
        """Stop execution immediately."""
        self.is_stopped = True
        self._pause_event.set()

    async def _check_pause_and_stop(self):
        """Check pause and stop states."""
        if self.is_stopped:
            raise asyncio.CancelledError("Run stopped by user")
        if self.is_paused:
            await self.emit("run_state_changed", {"state": "paused"})
            await self._pause_event.wait()
            if self.is_stopped:
                raise asyncio.CancelledError("Run stopped by user")
            await self.emit("run_state_changed", {"state": "running"})

    async def start_browser(self, headless: Optional[bool] = None):
        """Launch browser."""
        if headless is not None:
            self.headless = headless

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )

    async def close_browser(self):
        """Close browser context."""
        try:
            if self.context:
                await self.context.close()
                self.context = None
            if self.browser:
                await self.browser.close()
                self.browser = None
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
        except Exception:
            pass

    async def _get_target(self):
        """Return active frame or page."""
        return self.current_frame if self.current_frame else self.page

    async def start_new_session(self, pre_messages: Optional[List[str]] = None) -> bool:
        """Open a fresh chat session and wait for greeting."""
        await self._check_pause_and_stop()

        if self.context:
            await self.context.close()

        self.context = await self.browser.new_context(viewport=self.viewport)
        self.page = await self.context.new_page()

        await self.emit("session_starting", {"url": self.bot_url})
        await self.page.goto(self.bot_url, wait_until="networkidle", timeout=self.page_load_ms)

        # Iframe detection
        self.current_frame = None
        if self.iframe_selector:
            try:
                frame_loc = self.page.frame_locator(self.iframe_selector)
                if await frame_loc.locator(self.input_selector).count() > 0:
                    self.current_frame = frame_loc
            except Exception:
                pass

        if not self.current_frame:
            for frame in self.page.frames:
                if frame != self.page.main_frame:
                    try:
                        if await frame.locator(self.input_selector).count() > 0:
                            self.current_frame = frame
                            break
                    except Exception:
                        pass

        target = await self._get_target()

        # Wait for input box to appear
        input_loc = target.locator(self.input_selector).first
        await input_loc.wait_for(state="visible", timeout=self.greeting_wait_ms)

        # Wait for greeting to finish & stabilize
        await self.page.wait_for_timeout(3000)

        # Extract initial greeting text
        bubbles = await self._get_bot_bubbles()
        self.current_bot_bubble_count = max(len(bubbles), 1)

        greeting_text = bubbles[0]["text"] if bubbles else ""
        await self.emit("greeting_loaded", {
            "greeting": greeting_text,
            "buttons": bubbles[0]["buttons"] if bubbles else []
        })

        # Process optional setup pre-messages
        if pre_messages:
            for pmsg in pre_messages:
                await self._check_pause_and_stop()
                msg_str = str(pmsg).strip()
                if msg_str:
                    await self._send_message(msg_str, test_id="SETUP")
                    _, _, _, self.current_bot_bubble_count = await self._wait_for_bot_reply(
                        previous_count=self.current_bot_bubble_count,
                        test_id="SETUP"
                    )

        return True

    async def _get_bot_bubbles(self) -> List[Dict[str, Any]]:
        """Query distinct bot message bubbles and attached buttons, strictly excluding user bubbles."""
        target = await self._get_target()
        return await target.evaluate('''() => {
            const isUser = (el) => (
                el.closest('[class*="_userMessageBox_"]') ||
                el.closest('[class*="_userMessage"]') ||
                ((el.className || '') + '').includes('userMessage')
            );
            
            const conv = document.querySelector('div[class*="_conversation_"]');
            const root = conv || document.body;
            
            const selectors = [
                'div[data-bot-messagebox-bubble="true"]',
                'div[class*="_messageWrapper_"]',
                'div[style*="bot-messagebox"]',
                'div.DraftEditor-root'
            ];
            
            const candidates = Array.from(root.querySelectorAll(selectors.join(',')));
            const distinct = [];
            
            for (const el of candidates) {
                if (isUser(el)) continue;
                const txt = (el.innerText || '').trim();
                if (!txt || txt === 'Chat bot' || txt === 'Online' || txt.startsWith('Ask ') || txt.startsWith('Powered by')) {
                    continue;
                }
                if (!distinct.some(p => p.contains(el) && p !== el)) {
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

    async def _send_message(self, question: str, test_id: str):
        """
        Send a message or execute a CLICK: directive.
        Simulates human-like character-by-character typing with event stream.
        """
        await self._check_pause_and_stop()
        target = await self._get_target()

        raw_q = str(question).strip()

        # Check if DatePicker calendar is visible
        has_cal = await target.locator("button[class*='DatePicker-day']").count() > 0

        import re
        is_date_input = bool(
            raw_q.upper().startswith("DATE:") or
            re.match(r"^\d{1,2}[/\-]\d{1,2}[/\-]\d{4}$", raw_q) or
            re.match(r"^\d{4}[/\-]\d{1,2}[/\-]\d{1,2}$", raw_q) or
            (has_cal and raw_q.lower() in ["today", "now", "tomorrow"]) or
            (has_cal and raw_q.isdigit() and int(raw_q) <= 31)
        )

        # Directive: DATE selection on calendar picker
        if is_date_input:
            return await self._handle_date_selection(raw_q, test_id)

        # Directive: CLICK:Label
        if raw_q.startswith("CLICK:"):
            btn_label = raw_q[len("CLICK:"):].strip()

            # If calendar is open and clicking Submit without date selected, pick a date first!
            if btn_label.lower() == "submit" and has_cal:
                has_selected = await target.locator("button[class*='DatePicker-day'][data-selected='true']").count() > 0
                if not has_selected:
                    return await self._handle_date_selection("today", test_id)

            await self.emit("user_clicking", {"test_id": test_id, "button": btn_label})
            
            # Locate button with matching text
            btn_loc = target.locator(f"button:has-text(\"{btn_label}\"), [role=\"button\"]:has-text(\"{btn_label}\")").first
            if await btn_loc.count() > 0 and await btn_loc.is_visible():
                await btn_loc.click()
            else:
                # Fallback: type the button label
                await self._type_and_press_enter(btn_label, test_id)
            return None

        # Direct button match check
        btn_match = target.locator(f"button:has-text(\"{raw_q}\")").first
        if await btn_match.count() > 0 and await btn_match.is_visible():
            await self.emit("user_clicking", {"test_id": test_id, "button": raw_q})
            await btn_match.click()
            return None

        # Otherwise: standard human typing into input box
        await self._type_and_press_enter(raw_q, test_id)
        return None

    async def _handle_date_selection(self, date_spec: str, test_id: str) -> str:
        """
        Selects a date on the Mantine DatePicker widget and clicks Submit.
        Returns the date formatted in standard DD/MM/YYYY format.
        """
        import datetime
        import re

        target = await self._get_target()
        now = datetime.datetime.now()

        # Clean spec
        clean_spec = date_spec[5:].strip() if date_spec.upper().startswith("DATE:") else date_spec.strip()

        target_day = None
        target_month = None
        target_year = None

        m_dmy = re.match(r"^(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})$", clean_spec)
        m_ymd = re.match(r"^(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})$", clean_spec)

        if m_dmy:
            target_day = int(m_dmy.group(1))
            target_month = int(m_dmy.group(2))
            target_year = int(m_dmy.group(3))
        elif m_ymd:
            target_year = int(m_ymd.group(1))
            target_month = int(m_ymd.group(2))
            target_day = int(m_ymd.group(3))
        elif clean_spec.lower() in ["today", "now"]:
            target_day = now.day
            target_month = now.month
            target_year = now.year
        elif clean_spec.lower() in ["tomorrow"]:
            tom = now + datetime.timedelta(days=1)
            target_day = tom.day
            target_month = tom.month
            target_year = tom.year
        else:
            nums = re.findall(r"\b\d{1,2}\b", clean_spec)
            target_day = int(nums[-1]) if nums else now.day

        # Locate day button in Mantine calendar
        day_btn = target.locator(f"button[class*='DatePicker-day']:has-text('{target_day}')").last
        formatted_date = None

        if await day_btn.count() > 0 and await day_btn.is_visible():
            aria_label = (await day_btn.get_attribute("aria-label")) or ""
            # Parse aria-label like "28 October 2026"
            if aria_label:
                try:
                    parsed_dt = datetime.datetime.strptime(aria_label.strip(), "%d %B %Y")
                    formatted_date = parsed_dt.strftime("%d/%m/%Y")
                except Exception:
                    pass

            await day_btn.click()
            await self.page.wait_for_timeout(400)

        # Fallback date formatting if aria-label parsing was unavailable
        if not formatted_date:
            f_month = target_month if target_month else now.month
            f_year = target_year if target_year else now.year
            formatted_date = f"{target_day:02d}/{f_month:02d}/{f_year}"

        await self.emit("user_clicking", {"test_id": test_id, "button": f"Date {formatted_date}"})

        # Click Submit button on date picker
        submit_btn = target.locator("button:has-text('Submit'), [role='button']:has-text('Submit')").first
        if await submit_btn.count() > 0 and await submit_btn.is_visible():
            await self.emit("user_clicking", {"test_id": test_id, "button": "Submit"})
            await submit_btn.click()
            await self.page.wait_for_timeout(400)

        return formatted_date

    async def _type_and_press_enter(self, text: str, test_id: str):
        """Type into active input box character-by-character and emit live events."""
        target = await self._get_target()

        # Check for active, enabled inline input first (e.g. email or form node)
        inline_inps = target.locator(
            'div[class*="_messageWrapper_"] input:not([disabled]):not([readonly]), '
            '[class*="mantine-TextInput"] input:not([class*="_input_"]):not([disabled]):not([readonly])'
        )
        if await inline_inps.count() > 0 and await inline_inps.last.is_visible():
            input_loc = inline_inps.last
        else:
            # Bottom chat input bar or any enabled visible input
            active_inputs = target.locator(
                'input[class*="_input_"]:not([disabled]):not([readonly]), '
                'input[placeholder*="Here" i]:not([disabled]):not([readonly]), '
                'input[placeholder*="message" i]:not([disabled]):not([readonly]), '
                'textarea[class*="_input_"]:not([disabled]):not([readonly]), '
                'input:not([type="hidden"]):not([disabled]):not([readonly])'
            )
            count = await active_inputs.count()
            input_loc = active_inputs.last if count > 0 else target.locator(self.input_selector).first

        await input_loc.click()
        await input_loc.fill("")

        # Stream typing character-by-character
        accumulated = ""
        for char in text:
            await self._check_pause_and_stop()
            accumulated += char
            await input_loc.type(char, delay=self.typing_delay_ms)
            await self.emit("user_typing", {
                "test_id": test_id,
                "char": char,
                "current_text": accumulated,
                "full_text": text
            })

        await self.page.wait_for_timeout(200)

        # If an active inline submit button is visible (e.g. email node), click it
        submit_btn = target.locator("button:has-text('Submit'):not([disabled]), button[class*='_submitBtn_']:not([disabled])").last
        if await submit_btn.count() > 0 and await submit_btn.is_visible():
            await submit_btn.click()
            await self.emit("user_message_sent", {"test_id": test_id, "message": text})
            await self.page.wait_for_timeout(400)
            return

        # Otherwise press Enter and emit sent event
        await self.page.keyboard.press("Enter")
        await self.emit("user_message_sent", {"test_id": test_id, "message": text})
        await self.page.wait_for_timeout(300)

        # Fallback if input not cleared
        try:
            val = await input_loc.input_value(timeout=800)
            if val.strip():
                send_btn = target.locator(self.send_btn_selector).first
                if await send_btn.count() > 0 and await send_btn.is_visible():
                    await send_btn.click()
        except Exception:
            pass

    async def _wait_for_bot_reply(
        self,
        previous_count: int,
        test_id: str,
        timeout_s: Optional[float] = None
    ) -> Tuple[str, int, int, int]:
        """
        Wait until bot replies and typing indicator ceases.
        Emits live bot_typing events.
        """
        target = await self._get_target()
        t_start = time.perf_counter()
        first_reply_ms: Optional[int] = None
        last_reply_ms: Optional[int] = None
        last_seen_count = previous_count
        last_change_time = time.perf_counter()
        typing_emitted = False
        effective_timeout = timeout_s if timeout_s is not None else self.bot_reply_timeout_s

        while (time.perf_counter() - t_start) < effective_timeout:
            await self._check_pause_and_stop()
            await self.page.wait_for_timeout(200)
            now = time.perf_counter()

            # Check typing indicator
            is_typing = await target.evaluate('''() => {
                const loaders = document.querySelectorAll(
                    'div[class*=\"_loader_\"], div[class*=\"typing\"], div[class*=\"_loaderGlass_\"]'
                );
                return loaders.length > 0;
            }''')

            if is_typing and not typing_emitted:
                typing_emitted = True
                await self.emit("bot_typing_start", {"test_id": test_id})
            elif not is_typing and typing_emitted:
                typing_emitted = False
                await self.emit("bot_typing_stop", {"test_id": test_id})

            current_bubbles = await self._get_bot_bubbles()

            if len(current_bubbles) > last_seen_count:
                if first_reply_ms is None:
                    first_reply_ms = round((now - t_start) * 1000)
                last_reply_ms = round((now - t_start) * 1000)
                last_seen_count = len(current_bubbles)
                last_change_time = now

                # Emit partial reply preview
                new_ones = current_bubbles[previous_count:]
                if new_ones:
                    latest = new_ones[-1]
                    await self.emit("bot_bubble_arrived", {
                        "test_id": test_id,
                        "text": latest["text"],
                        "buttons": latest["buttons"],
                        "elapsed_ms": last_reply_ms
                    })
            elif len(current_bubbles) > previous_count and not is_typing:
                if (now - last_change_time) >= self.quiet_period_s:
                    break

        if typing_emitted:
            await self.emit("bot_typing_stop", {"test_id": test_id})

        final_bubbles = await self._get_bot_bubbles()
        new_bubbles = final_bubbles[previous_count:]

        bubble_texts = []
        all_buttons = []
        for b in new_bubbles:
            txt = b["text"]
            if b["buttons"]:
                all_buttons.extend(b["buttons"])
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
        """Capture failure screenshot and save to screenshots/."""
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

    async def run_single_step(
        self,
        test_case: Dict[str, Any],
        is_multi_turn: bool = False,
        pre_messages: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Execute one test case row with up to 2 retries on error/failure."""
        test_id = str(test_case.get("TestID", ""))
        question = str(test_case.get("Question", ""))
        expected = str(test_case.get("ExpectedAnswer", ""))
        category = str(test_case.get("Category", "General"))
        mode = test_case.get("Mode") or self.judge.default_mode

        last_result: Optional[Dict[str, Any]] = None

        for attempt in range(1 + self.max_retries):
            await self._check_pause_and_stop()
            is_retry = attempt > 0
            await self.emit("test_step_start", {
                "test_id": test_id,
                "question": question,
                "category": category,
                "is_retry": is_retry,
                "attempt": attempt + 1
            })

            try:
                # Start fresh session if needed
                if not is_multi_turn or is_retry:
                    await self.start_new_session(pre_messages=pre_messages)

                # Send question / action
                sent_date = await self._send_message(question, test_id=test_id)

                # Wait for bot response
                actual_answer, first_ms, last_ms, new_count = await self._wait_for_bot_reply(
                    previous_count=self.current_bot_bubble_count,
                    test_id=test_id
                )
                self.current_bot_bubble_count = new_count

                if not actual_answer.strip():
                    status = "TIMEOUT"
                    score = 0.0
                    reason = f"No bot response received within {self.bot_reply_timeout_s}s timeout"
                else:
                    comp: ComparisonResult = self.judge.compare(
                        expected=expected,
                        actual=actual_answer,
                        mode=mode
                    )
                    status = comp.status
                    score = comp.score
                    reason = comp.reason
                    if sent_date and status == "PASS":
                        actual_answer = sent_date

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

                if status == "PASS":
                    await self.emit("test_step_result", last_result)
                    return last_result

            except asyncio.CancelledError:
                raise
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

            if attempt < self.max_retries and not self.is_stopped:
                await self.emit("test_step_retry", {
                    "test_id": test_id,
                    "attempt": attempt + 1,
                    "status": last_result.get("Status")
                })
                await self.page.wait_for_timeout(2000)

        await self.emit("test_step_result", last_result)
        return last_result

    async def run_query_matching_flow(
        self,
        test_cases: List[Dict[str, Any]],
        pre_messages: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Dynamic Query-Matching Conversational Flow for Form/Lead Bots.
        The bot prompts first (or greets). The runner captures what the bot asked,
        matches it against the `Query` column across ALL provided test cases
        (regardless of row order, using LLM or Semantic Intent matcher), extracts
        the matching row's `ExpectedAnswer`, and forwards it to the bot.
        
        Verifies whether the bot accepted or rejected the input.
        ActualAnswer reflects what the bot captured and accepted (or the validation error if rejected).
        Repeats dynamically until all test cases are answered or the flow completes.
        If any step fails, it records the failure, captures a screenshot, and continues gracefully!
        """
        results: List[Dict[str, Any]] = []
        pending_cases = [dict(tc) for tc in test_cases]

        try:
            # 1. Start fresh session
            await self.start_new_session(pre_messages=pre_messages)

            # 2. Get initial bot prompt / greeting
            bubbles = await self._get_bot_bubbles()
            current_bot_text = bubbles[-1]["text"] if bubbles else ""

            if not current_bot_text:
                await self.page.wait_for_timeout(2500)
                bubbles = await self._get_bot_bubbles()
                current_bot_text = bubbles[-1]["text"] if bubbles else ""

            # 3. Main query-matching loop
            max_turns = len(test_cases) * 3
            turn_count = 0

            while pending_cases and not self.is_stopped and turn_count < max_turns:
                turn_count += 1
                await self._check_pause_and_stop()

                # Extract candidate queries for all pending cases
                candidate_queries = [
                    str(tc.get("Query", tc.get("Question", ""))).strip()
                    for tc in pending_cases
                ]

                # Match current bot prompt to candidate queries using LLM / Semantic matcher
                best_idx, best_score = self.judge.match_prompt_to_candidate_queries(
                    current_bot_text,
                    candidate_queries
                )

                best_tc = pending_cases[best_idx]
                best_query = candidate_queries[best_idx]
                test_id = str(best_tc.get("TestID", ""))
                answer_to_send = str(best_tc.get("ExpectedAnswer", ""))
                category = str(best_tc.get("Category", "General"))

                await self.emit("test_step_start", {
                    "test_id": test_id,
                    "id": best_tc.get("id"),
                    "question": best_query,
                    "query": best_query,
                    "expected_answer": answer_to_send,
                    "category": category,
                    "is_retry": False,
                    "attempt": 1
                })

                # Forward ExpectedAnswer to the bot
                sent_date = await self._send_message(answer_to_send, test_id=test_id)

                # Wait for the bot to reply with the next prompt (shorter wait if end of flow on last step)
                is_last_step = (len(pending_cases) == 1)
                reply_wait_timeout = 6.0 if is_last_step else None
                next_reply, first_ms, last_ms, new_count = await self._wait_for_bot_reply(
                    previous_count=self.current_bot_bubble_count,
                    test_id=test_id,
                    timeout_s=reply_wait_timeout
                )
                self.current_bot_bubble_count = new_count

                # Verify whether the bot accepted or rejected the input
                is_accepted, acceptance_msg = self.judge.verify_input_acceptance(next_reply, answer_to_send)

                screenshot_path = ""
                if not next_reply.strip() and len(pending_cases) > 1:
                    status = "TIMEOUT"
                    score = 0.0
                    actual_answer = "TIMEOUT: No bot response"
                    expected_display = answer_to_send
                    reason = f"Bot did not reply within {self.bot_reply_timeout_s}s after sending '{answer_to_send}'"
                    screenshot_path = await self._capture_failure_screenshot(test_id)
                elif not is_accepted:
                    status = "FAIL"
                    score = 0.0
                    actual_answer = acceptance_msg
                    expected_display = answer_to_send
                    reason = f"Bot rejected input '{answer_to_send}': {acceptance_msg}"
                    screenshot_path = await self._capture_failure_screenshot(test_id)
                else:
                    status = "PASS"
                    score = 100.0
                    if sent_date:
                        actual_answer = sent_date
                        expected_display = sent_date if (answer_to_send.upper().startswith("DATE:") or answer_to_send.isdigit()) else answer_to_send
                        reason = f"Bot accepted date '{sent_date}' in DD/MM/YYYY format"
                    else:
                        actual_answer = answer_to_send
                        expected_display = answer_to_send
                        reason = f"Bot accepted and captured expected response '{answer_to_send}' (matched query '{best_query}')"

                step_res = {
                    "id": best_tc.get("id"),
                    "TestID": test_id,
                    "Category": category,
                    "Query": best_query,
                    "Question": best_query,
                    "ExpectedAnswer": expected_display,
                    "ActualAnswer": actual_answer,
                    "Status": status,
                    "Score": score,
                    "Reason": reason,
                    "ResponseTimeMs": last_ms or first_ms,
                    "Screenshot": screenshot_path,
                    "NextBotPrompt": next_reply
                }
                results.append(step_res)
                await self.emit("test_step_result", step_res)
                pending_cases.remove(best_tc)

                if status == "TIMEOUT":
                    break

                # Prepare for next turn
                current_bot_text = next_reply
                await asyncio.sleep(self.message_delay_ms / 1000.0)

        except Exception as e:
            import traceback
            traceback.print_exc()

        # Any remaining cases in this session that were not reached
        for rem in pending_cases:
            test_id = str(rem.get("TestID", ""))
            q_val = str(rem.get("Query", rem.get("Question", "")))
            step_res = {
                "id": rem.get("id"),
                "TestID": test_id,
                "Category": str(rem.get("Category", "General")),
                "Query": q_val,
                "Question": q_val,
                "ExpectedAnswer": str(rem.get("ExpectedAnswer", "")),
                "ActualAnswer": "",
                "Status": "FAIL",
                "Score": 0.0,
                "Reason": "Step not reached due to prior timeout or end of flow",
                "ResponseTimeMs": 0,
                "Screenshot": ""
            }
            results.append(step_res)
            await self.emit("test_step_result", step_res)

        # Ensure returned results strictly preserve the original Excel test_cases series order
        tc_order = {tc.get("id", str(idx)): idx for idx, tc in enumerate(test_cases)}
        results.sort(key=lambda r: tc_order.get(r.get("id"), tc_order.get(r.get("TestID"), 999)))

        return results
