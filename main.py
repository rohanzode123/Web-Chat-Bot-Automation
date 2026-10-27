"""
Main CLI entry point for the Automated Conversational Test Runner.
Orchestrates test case loading from Excel, multi-turn session grouping,
browser automation, comparison, and reporting.
"""

import os
import sys
import argparse
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import yaml
import pandas as pd
from rich.console import Console
from rich.panel import Panel

from comparator import AnswerComparator
from reporter import TestReporter
from runner import ChatbotRunner

console = Console()


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file."""
    if not os.path.exists(config_path):
        console.print(f"[bold red]Configuration file not found:[/bold red] {config_path}")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_test_cases(excel_path: str, config: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Read test cases from Excel file using configured column names.
    Auto-generates TestID if missing.
    Also extracts optional setup messages from PreMessages sheet if present.
    """
    if not os.path.exists(excel_path):
        console.print(f"[bold red]Excel test cases file not found:[/bold red] {excel_path}")
        sys.exit(1)

    col_map = config.get("excel", {}).get("columns", {})
    col_id = col_map.get("test_id", "TestID")
    col_q = col_map.get("question", "Question")
    col_exp = col_map.get("expected_answer", "ExpectedAnswer")
    col_cat = col_map.get("category", "Category")
    col_conv = col_map.get("conversation", "Conversation")
    col_mode = col_map.get("mode", "Mode")

    pre_messages_sheet = config.get("excel", {}).get("pre_messages_sheet", "PreMessages")

    # Load main sheet
    xl = pd.ExcelFile(excel_path)
    main_sheet = xl.sheet_names[0]
    df = pd.read_excel(xl, sheet_name=main_sheet)

    test_cases: List[Dict[str, Any]] = []
    for idx, row in df.iterrows():
        # Clean question
        q_val = str(row.get(col_q, "")).strip() if pd.notna(row.get(col_q)) else ""
        if not q_val:
            continue  # Skip blank rows

        # TestID (auto-generate if missing)
        tid = str(row.get(col_id, "")).strip() if (col_id in row and pd.notna(row.get(col_id))) else ""
        if not tid:
            tid = f"TC_{idx + 1:03d}"

        # Conversation grouping key (defaults to TestID if not specified)
        conv_key = str(row.get(col_conv, "")).strip() if (col_conv in row and pd.notna(row.get(col_conv))) else tid

        expected = str(row.get(col_exp, "")).strip() if (col_exp in row and pd.notna(row.get(col_exp))) else ""
        category = str(row.get(col_cat, "General")).strip() if (col_cat in row and pd.notna(row.get(col_cat))) else "General"
        mode = str(row.get(col_mode, "")).strip() if (col_mode in row and pd.notna(row.get(col_mode))) else None

        test_cases.append({
            "TestID": tid,
            "Conversation": conv_key,
            "Question": q_val,
            "ExpectedAnswer": expected,
            "Category": category,
            "Mode": mode
        })

    # Load PreMessages if sheet exists
    pre_messages: List[str] = list(config.get("pre_messages", []))
    if pre_messages_sheet in xl.sheet_names:
        df_pre = pd.read_excel(xl, sheet_name=pre_messages_sheet)
        for _, prow in df_pre.iterrows():
            for c in ["Message", "Question", "PreMessage"]:
                if c in prow and pd.notna(prow[c]):
                    val = str(prow[c]).strip()
                    if val and val not in pre_messages:
                        pre_messages.append(val)
                    break

    return test_cases, pre_messages


async def run_tests(args: argparse.Namespace):
    """Main execution orchestrator."""
    config = load_config(args.config)

    # CLI Overrides
    if args.headless is not None:
        config["bot"]["headless"] = args.headless
    if args.mode:
        config["comparison"]["mode"] = args.mode

    excel_file = args.excel or config.get("excel", {}).get("input_file", "test_cases.xlsx")
    test_cases, pre_messages = load_test_cases(excel_file, config)

    # Filter by --only TestID or Conversation
    if args.only:
        target = args.only.strip()
        test_cases = [tc for tc in test_cases if tc["TestID"] == target or tc["Conversation"] == target]
        if not test_cases:
            console.print(f"[bold red]No tests found matching --only '{args.only}'[/bold red]")
            return

    # Filter by --limit N
    if args.limit and args.limit > 0:
        test_cases = test_cases[:args.limit]

    console.print(Panel.fit(
        f"[bold cyan]Chatbot Automated Test Runner[/bold cyan]\n"
        f"[dim]URL:[/dim] {config['bot']['url'][:70]}...\n"
        f"[dim]Total Tests To Run:[/dim] {len(test_cases)} | "
        f"[dim]Mode:[/dim] {config['comparison']['mode']} | "
        f"[dim]Headless:[/dim] {config['bot']['headless']}",
        border_style="cyan"
    ))

    if pre_messages:
        console.print(f"[dim]Pre-Messages configured ({len(pre_messages)}):[/dim] {pre_messages}\n")

    # Initialize modules
    reporter = TestReporter()
    comparator = AnswerComparator(
        default_mode=config["comparison"].get("mode", "semantic"),
        rapidfuzz_threshold=config["comparison"].get("rapidfuzz_threshold", 80),
        llm_provider=config["comparison"].get("llm_provider", "auto"),
        gemini_model=config["comparison"].get("gemini_model", "gemini-1.5-flash"),
        openai_model=config["comparison"].get("openai_model", "gpt-4o-mini")
    )
    runner = ChatbotRunner(config=config, reporter=reporter, comparator=comparator)

    await runner.start_browser(headless=config["bot"]["headless"])

    try:
        last_conv_key: Optional[str] = None

        for idx, tc in enumerate(test_cases):
            conv_key = tc["Conversation"]
            # Check if this step is a continuation of the same conversation
            is_multi_turn = (last_conv_key is not None and conv_key == last_conv_key)

            result = await runner.run_step(
                test_case=tc,
                is_multi_turn=is_multi_turn,
                pre_messages=pre_messages if not is_multi_turn else None
            )
            reporter.add_result(result)
            last_conv_key = conv_key

    finally:
        await runner.close_browser()

    # Generate Excel Report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = reporter.generate_excel_report(timestamp)

    # Print Terminal Summary
    reporter.print_terminal_summary()
    console.print(f"[bold green]✔ Excel Report Generated:[/bold green] [bold cyan]{report_file}[/bold cyan]\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automated Conversational Test Runner for Web Chatbots")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml (default: config.yaml)")
    parser.add_argument("--excel", default=None, help="Path to test cases Excel file (default: from config)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of test cases to run")
    parser.add_argument("--only", default=None, help="Run only a specific TestID or Conversation key")
    parser.add_argument("--mode", choices=["exact", "contains", "semantic"], default=None, help="Override comparison mode")
    
    # Headless toggle
    parser.add_argument("--headless", dest="headless", action="store_true", default=None, help="Run in headless browser mode")
    parser.add_argument("--headed", dest="headless", action="store_false", help="Run with visible browser window")
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run_tests(args))
