# Bot Test Studio & RZ-Work Automated Conversational Test Runner

An enterprise-grade test automation platform and live execution studio engineered specifically for the **RZ-Work Web Bot**. 

It provides two interfaces:
1. **Bot Test Studio (Full-Stack Web App)**: A dedicated web application (FastAPI + React + Tailwind + Playwright + WebSockets) where you upload an Excel/CSV test suite, trigger automated test runs, and watch the runner interact with your live bot inside a pixel-perfect replica of the RZ-Work chat widget with character-by-character typing and real-time status updates.
2. **CLI Test Runner**: A headless/headed command-line runner that executes Excel test suites, streams live progress in the terminal via `rich`, and generates formatted Excel reports (`results_<timestamp>.xlsx`) with row-level color coding and summary metrics.

---

## Key Features

- **Pixel-Accurate Widget Simulation**:
  - Live chat panel styled identically to the real RZ-Work preview widget (warm glass background `rgba(67, 59, 54, 0.94)`, `0px 15px 15px 15px` rounded bot bubbles, crisp white user bubbles, "Ask ELI" header with avatar, animated typing dots, and "Powered by rz-work" footer).
  - Character-by-character human-like typing simulation in the preview widget synchronized with backend Playwright keystrokes.
- **Robust Playwright Automation**:
  - Deep selector detection for RZ-Work DOM (`_innerWelcome_`, `_greeting_`, `_conversation_`, `_messageWrapper_`, `_loader_`).
  - Automatic iframe detection and resolution.
  - Flake-resistant waiting with typing-indicator disappearance checks, quiet period (*no new messages for N seconds*, default: 3.0s), and a 30s safety timeout.
- **Multi-Turn Chat Sessions**:
  - Test cases sharing the same `Conversation` or `TestID` run consecutively inside the **same ongoing chat session** without page reloads.
  - Non-grouped test cases start in a clean, fresh session.
- **Interactive Button Directives (`CLICK:Label`)**:
  - Automatically clicks matching button chips or quick replies when a question begins with `CLICK:Label` (e.g. `CLICK:Submit`).
- **Setup & Pre-Messages**:
  - Supports automated introductory inputs (e.g., Name, Phone, Email) before custom questions, configurable via an optional `PreMessages` Excel sheet or settings modal.
- **Pluggable 3-Mode Answer Comparison**:
  - `exact`: Normalized match (case-insensitive, whitespace collapsed, punctuation stripped).
  - `contains`: Checks if expected response or keywords are present in the actual bot response.
  - `semantic` (**Default - Zero API Key Required**): Uses RapidFuzz token matching (0–100 score, configurable threshold: 80). If an LLM API key (`GEMINI_API_KEY` or `OPENAI_API_KEY`) is provided in `.env`, it can evaluate semantic intent via AI, falling back cleanly to RapidFuzz if no key is present.
- **Comprehensive Quality Reporting**:
  - Millisecond-precision response time tracking (dispatch to first bot bubble, and dispatch to last bot bubble).
  - High-resolution screenshot capture on failures.
  - Excel and CSV result export with summary metrics (Total, Passed, Failed, Pass %, Avg Time).

---

## Project Structure

```
Web Automation/
├── backend/                  # Full-stack Web App Backend
│   ├── main.py              # FastAPI app (REST API, WebSocket, static frontend server)
│   ├── runner.py            # Playwright automation engine with live event streaming
│   ├── judge.py             # Answer comparison engine (Exact, Contains, RapidFuzz, LLM)
│   └── config.yaml          # Selectors, timeouts, thresholds, and execution settings
├── frontend/                 # React + Vite + Tailwind CSS Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx         # Navigation, target URL, theme toggle, settings
│   │   │   ├── LiveChat.jsx       # Real-time RZ-Work phone widget mockup
│   │   │   ├── ControlBar.jsx     # Run, Pause, Resume, Stop, Re-run, Delays, Downloads
│   │   │   ├── TestTable.jsx      # Drag-and-drop upload, filters, results table, metrics
│   │   │   ├── DetailModal.jsx    # Expanded Q&A modal with failure screenshot preview
│   │   │   └── SettingsModal.jsx  # Config drawer (modes, threshold, timeouts, pre-messages)
│   │   ├── App.jsx          # Application state & WebSocket manager
│   │   └── index.css        # Tailwind styles & animations
│   ├── dist/                # Pre-built production frontend assets
│   ├── package.json
│   └── vite.config.js
├── main.py                  # Standalone CLI test runner entry point
├── runner.py                # Standalone CLI Playwright runner
├── comparator.py            # Standalone CLI answer comparator
├── reporter.py              # Standalone CLI OpenPyXL Excel & terminal reporter
├── config.yaml              # Root configuration for CLI runner
├── test_cases.xlsx          # 5-row sample Excel test suite with multi-turn flows
├── screenshots/             # Output folder for failure screenshots
├── requirements.txt         # Python dependencies
├── .env.example             # Optional LLM API key template
└── README.md                # Documentation and guide
```

---

## Installation & Setup

### 1. Prerequisites
- Python 3.9+ (Python 3.10+ recommended)
- Node.js 18+ (for frontend development)
- Chromium browser binaries (installed via Playwright)

### 2. Set Up Python Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate       # On Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
```

### 3. Optional: Install Frontend Dependencies (For Frontend Dev)
The production build is already compiled into `frontend/dist/`. If you want to modify frontend components:
```bash
cd frontend
npm install
cd ..
```

### 4. Optional: Configure LLM API Keys
If you want to use OpenAI or Google Gemini for semantic judging instead of the built-in RapidFuzz engine:
```bash
cp .env.example .env
# Edit .env and set your key:
# GEMINI_API_KEY=your_key_here
# or
# OPENAI_API_KEY=your_key_here
```
> **Note**: If no keys are set, the app automatically falls back to **RapidFuzz** token matching (threshold: 80%), working out of the box with zero external dependencies.

---

## Running the Application

### Option A: Bot Test Studio (Full-Stack Web App) — Recommended

Run the FastAPI backend, which serves both the API, WebSocket server, and the pre-built React frontend:

```bash
./venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
Then open your browser at:
👉 **`http://localhost:8000`**

#### Frontend Development Mode (Hot Reloading)
To run the frontend dev server with instant HMR:
```bash
# Terminal 1: Backend
./venv/bin/uvicorn backend.main:app --port 8000 --reload

# Terminal 2: Frontend
cd frontend
npm run dev
# Opens at http://localhost:5173
```

---

### Option B: Standalone CLI Test Runner

Run tests directly from the terminal without launching the web app:

```bash
# 1. Run all tests in headless mode (default)
./venv/bin/python3 main.py

# 2. Run with visible Chromium browser
./venv/bin/python3 main.py --headed

# 3. Run a specific test case or conversation
./venv/bin/python3 main.py --only TC_001
./venv/bin/python3 main.py --only CONV_002

# 4. Limit the number of tests executed
./venv/bin/python3 main.py --limit 2

# 5. Override comparison mode
./venv/bin/python3 main.py --mode exact
./venv/bin/python3 main.py --mode contains
./venv/bin/python3 main.py --mode semantic

# 6. Specify custom test file or configuration
./venv/bin/python3 main.py --excel my_tests.xlsx --config backend/config.yaml
```

CLI runs generate a color-coded timestamped Excel file (`results_<timestamp>.xlsx`) with hyperlinks to failure screenshots and print a live summary dashboard in the terminal.

---

## Excel Test Suite Format (`test_cases.xlsx`)

The system reads `.xlsx`, `.xls`, or `.csv` files. Column headers are configurable in `config.yaml`.

### Form / Lead Bot Schema (`TestCases` sheet)

For bots that ask the user questions (e.g. Lead Generation, Form-Filling, Surveys), use **`Query`** and **`ExpectedAnswer`**:

| TestID | Conversation | Category | Query (Bot Question) | ExpectedAnswer (Your Reply) |
| :--- | :--- | :--- | :--- | :--- |
| `TC_001` | `CONV_001` | `Lead Flow` | `What's your Name?` | `Rohan Sharma` |
| `TC_002` | `CONV_001` | `Lead Flow` | `What's your phone number?` | `9876543210` |
| `TC_003` | `CONV_001` | `Lead Flow` | `What's your email?` | `rohan@example.com` |
| `TC_004` | `CONV_001` | `Lead Flow` | `Enter permanent address?` | `42 Park Avenue, Mumbai` |

### Key Capabilities:
1. **Dynamic Query Matching (Out-of-Order Support)**:
   The automation listens to what the bot asks in the chat window, searches across **all rows** in the uploaded sheet for a matching `Query` (using token-level fuzzy matching), extracts your `ExpectedAnswer` from that row, and forwards it to the bot.
   > **Note**: It does not matter what order the rows are in! If `"What's your Name?"` is on row 3, the runner finds row 3, forwards `"Rohan Sharma"`, and continues.
2. **Fail-Safe Suite Execution (Never Breaks on Failure)**:
   If a test case fails, times out, or encounters an unexpected prompt:
   - The failure is recorded with full reason and screenshot.
   - The test status updates to `FAIL` / `TIMEOUT` in the live UI table.
   - **The runner does NOT stop or crash!** It automatically proceeds to execute the next test case / conversation group until the entire suite is complete.
3. **Multi-Turn Chat Sessions (`Conversation`)**:
   Rows sharing the same `Conversation` key (e.g. `CONV_001`) run consecutively in the same ongoing chat session. When switching to a new conversation (e.g. `CONV_002`), the runner automatically opens a fresh session.
4. **Interactive Directives (`CLICK:` & `DATE:`)**:
   - `CLICK:Label`: Clicks that matching button chip or quick-reply (e.g. `CLICK:Submit`).
   - `DATE:<day_or_keyword>`: Selects a specific date on an interactive calendar picker and clicks Submit (e.g. `DATE:28`, `DATE:today`, `DATE:tomorrow`). If you enter `28` or `CLICK:Submit` while a calendar is open, the runner also automatically ensures the date is selected before submitting!
5. **Optional Setup Sheet (`PreMessages`)**:
   Add a `PreMessages` sheet with columns `Step`, `PreMessage`, and `Description` to send automated introductory inputs before test execution.

---

## Answer Comparison Modes

| Mode | Evaluation Logic | Best Used For |
| :--- | :--- | :--- |
| **`exact`** | Normalizes both strings (lowercased, stripped, whitespace collapsed, punctuation removed) and checks for identical text. | Fixed disclaimer texts, system errors, exact validation errors. |
| **`contains`** | Checks whether the expected string or all required keywords appear in the bot's response. | Checking for presence of specific links, phone numbers, or key phrases. |
| **`semantic`** *(Default)* | Evaluates whether the actual response means the same as the expected response. If no LLM key is configured, uses **RapidFuzz** token set ratio (0-100 score, threshold 80). If an API key is present in `.env`, queries Gemini or OpenAI and returns score + reasoning. | General conversational replies where wording may slightly vary. |

---

## Configuration Settings (`backend/config.yaml`)

```yaml
bot:
  url: "https://staging.rz-work.io/web_bot/?h=99c3077e-4288-4b48-b9e6-6888f7e72ebd+website&preview=1"
  headless: true
  viewport:
    width: 1280
    height: 800

selectors:
  iframe: null
  input_box: "input[placeholder*='message' i], input[class*='_input_'], input[type='text'], input[type='tel']"
  send_button: "button[aria-label='Send message'], button[class*='_sendButton']"
  bot_message_bubble: "div[data-bot-messagebox-bubble='true'], div[class*='_messageWrapper_'], div[class*='_greeting_']"
  user_message_bubble: "div[class*='_userMessageBox_'], div[class*='_userMessage']"
  typing_indicator: "div[class*='_loader_'], div[class*='typing'], div[class*='_loaderGlass_']"
  quick_reply_button: "button:not([aria-label]), div[role='button']"

timeouts:
  page_load_ms: 60000
  greeting_wait_ms: 15000
  bot_reply_timeout_s: 30
  quiet_period_s: 3.0
  typing_delay_ms: 40
  message_delay_ms: 800

comparison:
  mode: "semantic"
  rapidfuzz_threshold: 80
  llm_provider: "auto"

execution:
  max_retries: 2
  screenshot_on_failure: true
  screenshots_dir: "screenshots"
```

---

## Verification & Testing Performed

1. **DOM & Selector Extraction**: Real RZ-Work preview widget inspected; selectors verified for welcome view, transition to conversation stream, input field, and typing indicator.
2. **Live Execution**: Ran full 5-row test suite with multi-turn flows against live RZ-Work bot.
3. **Failure Capture**: Verified automatic high-res screenshot capture in `screenshots/` on failed evaluations.
4. **WebSocket Live Sync**: Verified streaming events (`user_typing`, `bot_typing_start`, `bot_bubble_arrived`, `test_step_result`, `suite_finished`) driving the frontend React UI in real time.
5. **Excel/CSV Export**: Verified downloading customized timestamped Excel sheets with summary statistics and formatted pass/fail color fills.
