"""
FastAPI application for Bot Test Studio.
Provides REST APIs for file upload, validation, export, templates, and
WebSocket endpoint for real-time live execution and UI synchronization.
"""

import os
import io
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
import yaml
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import sys
sys.path.insert(0, os.path.dirname(__file__))

from judge import AnswerJudge
from runner import AutomationRunner

app = FastAPI(title="Bot Test Studio API", version="2.0.0")

# Enable CORS for local Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "..", "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


def load_config() -> Dict[str, Any]:
    """Load config.yaml with fallback to defaults."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


def save_config(cfg: Dict[str, Any]):
    """Persist config.yaml."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, default_flow_style=False)


# Global active runner tracking
active_runner: Optional[AutomationRunner] = None
runner_task: Optional[asyncio.Task] = None


@app.get("/api/config")
async def get_config():
    """Retrieve current configuration."""
    return load_config()


@app.post("/api/config")
async def update_config(data: Dict[str, Any]):
    """Update configuration settings."""
    cfg = load_config()
    cfg.update(data)
    save_config(cfg)
    return {"status": "ok", "config": cfg}


@app.post("/api/upload")
async def upload_test_file(file: UploadFile = File(...)):
    """
    Parse uploaded .xlsx, .xls, or .csv test file.
    Validates required columns and returns parsed test rows and setup pre-messages.
    """
    filename = file.filename.lower()
    contents = await file.read()

    cfg = load_config()
    col_map = cfg.get("excel", {}).get("columns", {})
    col_id = col_map.get("test_id", "TestID")
    col_q = col_map.get("question", "Question")
    col_exp = col_map.get("expected_answer", "ExpectedAnswer")
    col_cat = col_map.get("category", "Category")
    col_conv = col_map.get("conversation", "Conversation")
    col_mode = col_map.get("mode", "Mode")
    pre_sheet_name = cfg.get("excel", {}).get("pre_messages_sheet", "PreMessages")

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
            pre_messages = []
        elif filename.endswith((".xlsx", ".xls")):
            xl = pd.ExcelFile(io.BytesIO(contents))
            df = pd.read_excel(xl, sheet_name=xl.sheet_names[0])
            pre_messages = []
            if pre_sheet_name in xl.sheet_names:
                df_pre = pd.read_excel(xl, sheet_name=pre_sheet_name)
                for _, prow in df_pre.iterrows():
                    for c in ["PreMessage", "Message", "Question"]:
                        if c in prow and pd.notna(prow[c]):
                            val = str(prow[c]).strip()
                            if val:
                                pre_messages.append(val)
                            break
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Please upload a .xlsx or .csv file.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    # Column Validation
    found_cols = [str(c).strip() for c in df.columns]
    
    # Flexible match for Query / Question & ExpectedAnswer
    q_col_found = next((c for c in df.columns if str(c).strip().lower() in [col_q.lower(), "query", "bot_query", "question", "prompt", "user_message", "input"]), None)
    exp_col_found = next((c for c in df.columns if str(c).strip().lower() in [col_exp.lower(), "expectedanswer", "expected", "expected_answer", "answer", "user_reply", "bot_reply"]), None)

    if not q_col_found or not exp_col_found:
        missing = []
        if not q_col_found:
            missing.append(f"'Query' or 'Question'")
        if not exp_col_found:
            missing.append(f"'ExpectedAnswer'")
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {', '.join(missing)}. Detected columns: {', '.join(found_cols)}"
        )

    # Optional columns detection
    id_col_found = next((c for c in df.columns if str(c).strip().lower() in [col_id.lower(), "testid", "id"]), None)
    cat_col_found = next((c for c in df.columns if str(c).strip().lower() in [col_cat.lower(), "category", "tag"]), None)
    conv_col_found = next((c for c in df.columns if str(c).strip().lower() in [col_conv.lower(), "conversation", "session"]), None)
    mode_col_found = next((c for c in df.columns if str(c).strip().lower() in [col_mode.lower(), "mode", "comparison"]), None)

    test_cases = []
    for idx, row in df.iterrows():
        q_text = str(row[q_col_found]).strip() if pd.notna(row[q_col_found]) else ""
        if not q_text:
            continue

        tid = str(row[id_col_found]).strip() if (id_col_found and pd.notna(row[id_col_found])) else f"TC_{idx + 1:03d}"
        conv_key = str(row[conv_col_found]).strip() if (conv_col_found and pd.notna(row[conv_col_found]) and str(row[conv_col_found]).strip()) else "CONV_001"
        exp_text = str(row[exp_col_found]).strip() if pd.notna(row[exp_col_found]) else ""
        cat = str(row[cat_col_found]).strip() if (cat_col_found and pd.notna(row[cat_col_found])) else "General"
        mode = str(row[mode_col_found]).strip() if (mode_col_found and pd.notna(row[mode_col_found])) else None

        test_cases.append({
            "id": f"row_{idx + 1}",
            "TestID": tid,
            "Conversation": conv_key,
            "Query": q_text,
            "Question": q_text,
            "ExpectedAnswer": exp_text,
            "Category": cat,
            "Mode": mode,
            "Status": "PENDING",
            "Score": None,
            "ActualAnswer": "",
            "Reason": "",
            "ResponseTimeMs": 0,
            "Screenshot": ""
        })

    return {
        "status": "success",
        "filename": file.filename,
        "total_rows": len(test_cases),
        "test_cases": test_cases,
        "pre_messages": pre_messages
    }


@app.get("/api/template")
async def download_sample_template():
    """Generate and return sample Excel template with 5 example test rows."""
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "TestCases"

    headers = ["TestID", "Conversation", "Category", "Query", "ExpectedAnswer"]
    ws1.append(headers)

    sample_rows = [
        ["TC_001", "CONV_001", "Lead Flow", "What's your phone number?", "9876543210"],
        ["TC_002", "CONV_001", "Lead Flow", "What's your Name?", "Rohan Sharma"],
        ["TC_003", "CONV_001", "Lead Flow", "What's your email?", "rohan@example.com"],
        ["TC_004", "CONV_001", "Lead Flow", "Enter permanent address?", "42 Park Avenue, Mumbai"]
    ]

    for r in sample_rows:
        ws1.append(r)

    # Styling
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")

    for col_idx in range(1, len(headers) + 1):
        cell = ws1.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for col in ws1.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws1.column_dimensions[col_letter].width = max(max_len + 4, 15)

    # Optional PreMessages sheet
    ws2 = wb.create_sheet(title="PreMessages")
    ws2.append(["Step", "PreMessage", "Description"])
    ws2.append([1, "John Doe", "Optional full name setup"])
    ws2.append([2, "9876543210", "Optional phone setup"])

    for col_idx in range(1, 4):
        cell = ws2.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=test_cases_template.xlsx"}
    )


@app.post("/api/export")
async def export_results(data: Dict[str, Any]):
    """
    Export test execution results to styled Excel (.xlsx) or CSV.
    Applies color coding (Green: PASS, Red: FAIL, Orange: ERROR/TIMEOUT)
    and includes Summary sheet.
    """
    format_type = data.get("format", "xlsx").lower()
    results = data.get("results", [])

    if format_type == "csv":
        df = pd.DataFrame(results)
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        return StreamingResponse(
            io.BytesIO(buffer.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=test_results.csv"}
        )

    # Excel export with openpyxl styling
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Results"

    headers = [
        "TestID", "Category", "Query", "ExpectedAnswer",
        "ActualAnswer", "Status", "Score", "Reason", "ResponseTimeMs", "Screenshot"
    ]
    ws.append(headers)

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    pass_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    pass_font = Font(name="Calibri", size=10, color="006100")
    fail_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    fail_font = Font(name="Calibri", size=10, color="9C0006")
    warn_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
    warn_font = Font(name="Calibri", size=10, color="9C6500")

    for row_idx, r in enumerate(results, start=2):
        status = str(r.get("Status", "PENDING")).upper()
        row_vals = [
            r.get("TestID", ""),
            r.get("Category", ""),
            r.get("Query", r.get("Question", "")),
            r.get("ExpectedAnswer", ""),
            r.get("ActualAnswer", ""),
            status,
            r.get("Score", 0),
            r.get("Reason", ""),
            r.get("ResponseTimeMs", 0),
            r.get("Screenshot", "")
        ]
        ws.append(row_vals)

        fill = pass_fill if status == "PASS" else (fail_fill if status == "FAIL" else warn_fill)
        font = pass_font if status == "PASS" else (fail_font if status == "FAIL" else warn_font)

        for col_idx in range(1, len(headers) + 1):
            c = ws.cell(row=row_idx, column=col_idx)
            c.fill = fill
            if col_idx == 6:
                c.font = font
            c.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

    for col in ws.columns:
        max_len = max(len(str(c.value or "").split("\n")[0]) for c in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)

    # Summary Sheet
    ws_sum = wb.create_sheet(title="Summary")
    total = len(results)
    passed = sum(1 for r in results if r.get("Status") == "PASS")
    failed = sum(1 for r in results if r.get("Status") == "FAIL")
    errors = sum(1 for r in results if r.get("Status") in ["ERROR", "TIMEOUT"])
    pct = round(passed / total * 100, 1) if total > 0 else 0
    times = [r.get("ResponseTimeMs", 0) for r in results if r.get("ResponseTimeMs", 0) > 0]
    avg_t = round(sum(times) / len(times), 1) if times else 0

    ws_sum["A1"] = "Bot Test Studio - Execution Summary"
    ws_sum["A1"].font = Font(name="Calibri", size=14, bold=True, color="1F4E79")
    ws_sum["A2"] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    ws_sum["A4"] = "Metric"
    ws_sum["B4"] = "Value"
    ws_sum["A4"].font = header_font
    ws_sum["A4"].fill = header_fill
    ws_sum["B4"].font = header_font
    ws_sum["B4"].fill = header_fill

    summary_metrics = [
        ("Total Tests", total),
        ("Passed", passed),
        ("Failed", failed),
        ("Errors / Timeouts", errors),
        ("Pass Percentage", f"{pct}%"),
        ("Average Response Time", f"{avg_t} ms")
    ]
    for idx, (m, v) in enumerate(summary_metrics, start=5):
        ws_sum.cell(row=idx, column=1, value=m).font = Font(bold=True)
        ws_sum.cell(row=idx, column=2, value=v).font = Font(bold=True)

    ws_sum.column_dimensions["A"].width = 25
    ws_sum.column_dimensions["B"].width = 18

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.get("/api/screenshots/{filename}")
async def get_screenshot(filename: str):
    """Serve screenshot images for failure modal preview."""
    safe_name = os.path.basename(filename)
    path = os.path.join(SCREENSHOTS_DIR, safe_name)
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Screenshot not found")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Bi-directional WebSocket connection for:
    - Starting, pausing, resuming, and stopping test runs.
    - Streaming real-time character typing, bot bubbles, timings, and results.
    """
    global active_runner, runner_task
    await websocket.accept()

    async def emit_to_client(event_type: str, data: Dict[str, Any]):
        try:
            await websocket.send_text(json.dumps({
                "type": event_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }))
        except Exception:
            pass

    try:
        while True:
            text = await websocket.receive_text()
            msg = json.loads(text)
            action = msg.get("action")

            if action == "start":
                # Cancel any existing running task
                if active_runner:
                    active_runner.stop()
                    if runner_task and not runner_task.done():
                        runner_task.cancel()

                test_cases = msg.get("test_cases", [])
                bot_url = msg.get("bot_url")
                overrides = msg.get("config_overrides", {})
                pre_messages = msg.get("pre_messages", [])

                cfg = load_config()
                if bot_url:
                    cfg["bot"]["url"] = bot_url
                if overrides:
                    if "typing_delay_ms" in overrides:
                        cfg["timeouts"]["typing_delay_ms"] = int(overrides["typing_delay_ms"])
                    if "message_delay_ms" in overrides:
                        cfg["timeouts"]["message_delay_ms"] = int(overrides["message_delay_ms"])
                    if "mode" in overrides:
                        cfg["comparison"]["mode"] = overrides["mode"]
                    if "rapidfuzz_threshold" in overrides:
                        cfg["comparison"]["rapidfuzz_threshold"] = float(overrides["rapidfuzz_threshold"])
                    if "headless" in overrides:
                        cfg["bot"]["headless"] = bool(overrides["headless"])

                judge = AnswerJudge(
                    default_mode=cfg["comparison"].get("mode", "semantic"),
                    rapidfuzz_threshold=cfg["comparison"].get("rapidfuzz_threshold", 80),
                    llm_provider=cfg["comparison"].get("llm_provider", "auto"),
                    gemini_model=cfg["comparison"].get("gemini_model", "gemini-1.5-flash"),
                    openai_model=cfg["comparison"].get("openai_model", "gpt-4o-mini")
                )

                active_runner = AutomationRunner(
                    config=cfg,
                    judge=judge,
                    event_callback=emit_to_client
                )

                async def execution_loop(tc_list, runner_instance, pre_msgs):
                    results_list = []
                    try:
                        await runner_instance.start_browser(headless=cfg["bot"]["headless"])
                        await emit_to_client("suite_started", {"total": len(tc_list)})

                        # Detect if test suite is query-driven (bot prompts first)
                        is_query_driven = any(tc.get("Query") for tc in tc_list)

                        # Group test cases by Conversation
                        from itertools import groupby
                        grouped_convs = []
                        for key, group in groupby(tc_list, key=lambda x: str(x.get("Conversation", x.get("TestID", "")))):
                            grouped_convs.append((key, list(group)))

                        for conv_idx, (conv_key, group_tcs) in enumerate(grouped_convs):
                            if runner_instance.is_stopped:
                                break

                            if conv_idx > 0:
                                await asyncio.sleep(runner_instance.message_delay_ms / 1000.0)

                            try:
                                if is_query_driven:
                                    # Run dynamic query-matching conversation flow
                                    group_res = await runner_instance.run_query_matching_flow(
                                        test_cases=group_tcs,
                                        pre_messages=pre_msgs
                                    )
                                    results_list.extend(group_res)
                                else:
                                    # Standard question-driven step-by-step
                                    for idx, tc in enumerate(group_tcs):
                                        if runner_instance.is_stopped:
                                            break
                                        is_multi_turn = (idx > 0)
                                        try:
                                            res = await runner_instance.run_single_step(
                                                test_case=tc,
                                                is_multi_turn=is_multi_turn,
                                                pre_messages=pre_msgs if not is_multi_turn else None
                                            )
                                            results_list.append(res)
                                        except Exception as step_err:
                                            screenshot_path = await runner_instance._capture_failure_screenshot(tc.get("TestID", f"TC_{idx}"))
                                            res = {
                                                "id": tc.get("id"),
                                                "TestID": tc.get("TestID", f"TC_{idx}"),
                                                "Category": tc.get("Category", "General"),
                                                "Question": tc.get("Question", tc.get("Query", "")),
                                                "Query": tc.get("Query", tc.get("Question", "")),
                                                "ExpectedAnswer": tc.get("ExpectedAnswer", ""),
                                                "ActualAnswer": "",
                                                "Status": "ERROR",
                                                "Score": 0.0,
                                                "Reason": f"Error: {str(step_err)}",
                                                "ResponseTimeMs": 0,
                                                "Screenshot": screenshot_path
                                            }
                                            results_list.append(res)
                                            await emit_to_client("test_step_result", res)

                            except Exception as conv_err:
                                # Catch any unexpected error in conversation group and continue to next!
                                for tc in group_tcs:
                                    if not any(r.get("id") == tc.get("id") for r in results_list):
                                        res = {
                                            "id": tc.get("id"),
                                            "TestID": tc.get("TestID", ""),
                                            "Category": tc.get("Category", "General"),
                                            "Question": tc.get("Question", tc.get("Query", "")),
                                            "Query": tc.get("Query", tc.get("Question", "")),
                                            "ExpectedAnswer": tc.get("ExpectedAnswer", ""),
                                            "ActualAnswer": "",
                                            "Status": "ERROR",
                                            "Score": 0.0,
                                            "Reason": f"Flow Error: {str(conv_err)}",
                                            "ResponseTimeMs": 0,
                                            "Screenshot": ""
                                        }
                                        results_list.append(res)
                                        await emit_to_client("test_step_result", res)

                    except asyncio.CancelledError:
                        await emit_to_client("suite_stopped", {"message": "Execution stopped by user"})
                    except Exception as e:
                        await emit_to_client("suite_error", {"error": str(e)})
                    finally:
                        await runner_instance.close_browser()

                        total = len(results_list)
                        passed = sum(1 for r in results_list if r.get("Status") == "PASS")
                        failed = sum(1 for r in results_list if r.get("Status") == "FAIL")
                        errors = sum(1 for r in results_list if r.get("Status") in ["ERROR", "TIMEOUT"])
                        pct = round(passed / total * 100, 1) if total > 0 else 0
                        times = [r.get("ResponseTimeMs", 0) for r in results_list if r.get("ResponseTimeMs", 0) > 0]
                        avg_t = round(sum(times) / len(times), 1) if times else 0

                        await emit_to_client("suite_finished", {
                            "summary": {
                                "total": total,
                                "passed": passed,
                                "failed": failed,
                                "errors": errors,
                                "pass_rate": pct,
                                "avg_response_time_ms": avg_t
                            },
                            "results": results_list
                        })

                runner_task = asyncio.create_task(execution_loop(test_cases, active_runner, pre_messages))

            elif action == "pause":
                if active_runner:
                    active_runner.pause()
                    await emit_to_client("run_paused", {})

            elif action == "resume":
                if active_runner:
                    active_runner.resume()
                    await emit_to_client("run_resumed", {})

            elif action == "stop":
                if active_runner:
                    active_runner.stop()
                    await emit_to_client("run_stopped", {})

    except WebSocketDisconnect:
        if active_runner:
            active_runner.stop()
        if runner_task and not runner_task.done():
            runner_task.cancel()


# Mount frontend dist if it exists
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
