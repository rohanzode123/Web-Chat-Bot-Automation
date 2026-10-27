# RZ-Work Component Library & Automation Handling Matrix

This document is the permanent reference guide for all **49 RZ-Work components** across 10 categories, detailing how **Bot Test Studio** automates, tests, and validates each component.

---

## 1. User Input Components
Interactive elements where the bot solicits data or choices from the user.

| Component | Description | DOM / Widget Behavior | Automation Handling Strategy |
| :--- | :--- | :--- | :--- |
| **Message** | Bot sends a message bubble | Standard bot bubble (`div[class*="_messageWrapper_"]`) | Waits for arrival, strips noise, captures text for intent matching. |
| **Name** | Asks for user's full name | Standard bottom input box or inline field | Types string character-by-character; presses `Enter`. |
| **Phone** | Asks for phone number | Validates 10 digits; may format with country code | Types digits; verifies no validation rejection (e.g. `10 digit`). |
| **Email** | Asks for email address | **Inline form node** (`input[placeholder*='mail']`) with dedicated `Submit` button | Types valid email format into the inline input, clicks `button._submitBtn_`. |
| **Date/Appointment** | Asks for appointment / date | **Mantine DatePicker** calendar overlay | Selects day cell `button[class*='DatePicker-day']`, clicks `Submit`, formats as `DD/MM/YYYY`. |
| **Time** | Asks for appointment time | Time slot buttons or time picker dropdown | Clicks matching time slot pill (e.g. `11:00 AM`) or types time string. |
| **Address** | Asks for address | Bottom input bar becomes re-enabled | Types full address text; presses `Enter`. |
| **Custom Input** | Custom text / regex inputs | Standard input box with custom validation | Types `ExpectedAnswer`; checks bot acceptance. |
| **Multiple Choice** | Multiple choice buttons | Button pills (`button:not([aria-label])`) | Matches `ExpectedAnswer` to button label text and clicks it. |
| **Yes/No** | Binary Yes/No choice | Two distinct buttons `[Yes]` and `[No]` | Clicks the matching button directly (`CLICK:Yes` or `CLICK:No`). |
| **Image Multi Choice** | Visual cards with action buttons | Card containers with images and CTA buttons | Locates card with matching title/caption and clicks its button. |
| **Multi Select** | Checklist of options | Checkboxes with a final `Submit` button | Checks all requested options in `ExpectedAnswer` (comma-separated), clicks `Submit`. |
| **Form** | Multi-field inline card | Single card with 2+ inputs (e.g., Name + Phone) | Iterates each field, fills values sequentially, clicks card `Submit`. |
| **Rating** | Star rating or satisfaction scale | 5 clickable stars or 5 sentiment emojis | Clicks the nth star or matching emoji (😡 🙁 😐 🙂 😃). |
| **Database Hub** | Syncs data to internal database | Background server event | Verifies bot confirmation bubble after database commit. |
| **Welcome Screen** | Initial splash / greeting | Hero card or greeting bubble on widget load | Waits for greeting stabilization before starting test steps. |

---

## 2. Media & Rich Content
Visual assets, maps, file transfers, and embeds.

| Component | Description | Automation Handling Strategy |
| :--- | :--- | :--- |
| **Locate Me (List)** | Predefined branch/store location list | Clicks matching branch name item in the list. |
| **Locate Me (Pin)** | Map pin / GPS coordinate prompt | Emits coordinates or clicks "Use Current Location" pin. |
| **Media Display** | Displays images, videos, audio, YouTube | Verifies media element (`<img>`, `<video>`, `<iframe>`) is rendered and visible. |
| **Media Download** | Downloadable brochure, invoice, or PDF | Asserts `<a>` tag with valid download URL or file link exists. |
| **Media Upload** | Prompts user to upload attachment | Uses Playwright `setInputFiles` to upload test file attachment. |
| **Carousel** | Horizontally swipeable image cards | Scrolls carousel horizontally to find matching item and clicks its CTA button. |
| **Text Carousel** | Horizontally swipeable text cards | Scans carousel card headers, clicks matching button. |
| **Iframe** | Embedded third-party webpage | Switches Playwright target context into iframe if interactions are required. |
| **Window Event** | `postMessage` communication with parent window | Listens to `window.postMessage` events dispatched by the widget. |

---

## 3. Link & URL
Outbound links and redirects.

| Component | Description | Automation Handling Strategy |
| :--- | :--- | :--- |
| **Link URL** | Send external web links / button CTAs | Verifies button/link exists with expected destination URL. |

---

## 4. Ticketing
Support ticket integrations.

| Component | Description | Automation Handling Strategy |
| :--- | :--- | :--- |
| **Ticket** | Create or update ticket in CRM/helpdesk | Validates ticket creation confirmation message and captured ticket ID. |

---

## 5. Logic & Flow
Flow control, branching decisions, and routing.

| Component | Description | Automation Handling Strategy |
| :--- | :--- | :--- |
| **Conditional** | Splits flow into branches based on user input or variables | LLM / Intent matcher evaluates user input and follows the branched question. |
| **Goal** | Conversion / milestone tracking | Asserts the goal completion event or message is reached. |
| **A/B Testing** | Splits users into Path A vs Path B | Dynamically identifies which branch is active based on the prompt received. |
| **Chat Switch** | Switches between rooms / bots | Follows session redirect to new chat room. |

---

## 6. Integration & API
External webhooks, calendars, and payment services.

| Component | Description | Automation Handling Strategy |
| :--- | :--- | :--- |
| **Google Map** | Interactive map location selection | Interacts with map canvas or sends place name. |
| **Webhook** | REST API call to external backend | Waits for external API response without timing out. |
| **Streaming Webhook** | Streaming token responses from backend/LLM | Listens until streaming stops and typing indicator disappears. |
| **Payment Integrations** | Razorpay / Stripe payment gateway prompt | Detects payment trigger card / button. |
| **Calendly** | Calendly appointment booking embed | Interacts with Calendly iframe to select slot and confirm. |
| **Google Calendar** | Google Calendar appointment sync | Selects available date/time slot on calendar. |
| **Google Sheets** | Read/write data to Google Sheets | Verifies successful write confirmation from bot. |
| **Dialog Flow** | Dialogflow NLP intent matching | Uses LLM semantic matcher to evaluate natural language understanding. |

---

## 7. Communication & Variables
Runtime session state and outbound email notifications.

| Component | Description | Automation Handling Strategy |
| :--- | :--- | :--- |
| **Set Variable** | Stores user inputs into variables (e.g. `user_phone`) | Tracks variable persistence across multi-turn conversation. |
| **Send Email** | Outbound notification email dispatched | Verifies email dispatched confirmation from bot. |
| **Gmail** | Send email via connected Gmail account | Verifies email dispatched confirmation from bot. |

---

## 8. GenAI & Voice
AI models, speech, and entity extraction.

| Component | Description | Automation Handling Strategy |
| :--- | :--- | :--- |
| **GenAI** | Dynamic LLM-generated bot responses | Evaluates semantic correctness using Gemini / OpenAI LLM judge. |
| **Intent** | Intent detection node | Tests whether user natural phrases trigger the intended flow path. |
| **Entity** | Extracts entities (dates, locations, numbers) | Submits text containing entities; verifies extraction in subsequent step. |

---

## 9. Agent & Live Chat
Human escalation and agent handoffs.

| Component | Description | Automation Handling Strategy |
| :--- | :--- | :--- |
| **Agent Live Chat** | Transfer conversation to human agent | Detects transfer message (e.g. *"Connecting to an agent..."*). |
| **Team Live Chat** | Transfer to specific department queue | Detects queue message (e.g. *"Transferred to Sales team"*). |

---

## 10. Block and End Flow
Modular blocks and flow conclusion.

| Component | Description | Automation Handling Strategy |
| :--- | :--- | :--- |
| **Block** | Reusable sub-flow module | Traverses seamlessly through the encapsulated block nodes. |
| **End the flow** | Conversation concludes | Detects input disablement / end of flow; gracefully completes suite with **PASS 100%**. |

