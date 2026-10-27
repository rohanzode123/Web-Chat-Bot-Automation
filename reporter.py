"""
Reporting module for generating styled Excel test reports and live terminal logs.
"""

import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()


class TestReporter:
    def __init__(self, output_dir: str = "."):
        self.output_dir = output_dir
        self.results: List[Dict[str, Any]] = []
        os.makedirs(output_dir, exist_ok=True)

    def log_test_start(self, test_id: str, question: str, category: str, is_retry: bool = False):
        """Print test start in terminal."""
        retry_str = " (Retry)" if is_retry else ""
        console.print(
            f"[bold cyan]▶ [{test_id}]{retry_str}[/bold cyan] "
            f"[dim]({category})[/dim] Question: [white]{question}[/white]"
        )

    def log_test_result(self, result: Dict[str, Any]):
        """Print test result in terminal with rich formatting."""
        status = result.get("Status", "UNKNOWN")
        test_id = result.get("TestID", "")
        time_ms = result.get("ResponseTimeMs", 0)
        score = result.get("Score", 0.0)
        reason = result.get("Reason", "")
        actual = result.get("ActualAnswer", "")
        
        # Color badge
        if status == "PASS":
            badge = "[bold white on green] PASS [/bold white on green]"
        elif status == "FAIL":
            badge = "[bold white on red] FAIL [/bold white on red]"
        elif status in ["ERROR", "TIMEOUT"]:
            badge = "[bold white on dark_orange] " + status + " [/bold white on dark_orange]"
        else:
            badge = f"[bold white on blue] {status} [/bold white on blue]"

        console.print(
            f"  {badge} [bold]{test_id}[/bold] "
            f"Score: [yellow]{score}%[/yellow] "
            f"Time: [magenta]{time_ms}ms[/magenta] | "
            f"[dim]{reason}[/dim]"
        )
        if actual:
            preview = actual.replace("\n", " ")
            if len(preview) > 100:
                preview = preview[:97] + "..."
            console.print(f"  [dim]Actual:[/dim] [cyan]{preview}[/cyan]")
        console.print("")

    def add_result(self, result: Dict[str, Any]):
        """Record a test result."""
        self.results.append(result)

    def generate_excel_report(self, timestamp: Optional[str] = None) -> str:
        """
        Generate results_<timestamp>.xlsx with Results and Summary sheets.
        Applies green, red, and orange row highlights.
        """
        if not timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"results_{timestamp}.xlsx"
        filepath = os.path.join(self.output_dir, filename)

        wb = openpyxl.Workbook()
        
        # ----------------------------------------------------
        # Sheet 1: Results
        # ----------------------------------------------------
        ws_results = wb.active
        ws_results.title = "Results"

        headers = [
            "TestID",
            "Category",
            "Question",
            "ExpectedAnswer",
            "ActualAnswer",
            "Status",
            "Score",
            "Reason",
            "ResponseTimeMs",
            "Screenshot"
        ]
        ws_results.append(headers)

        # Style header
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        for col_num in range(1, len(headers) + 1):
            cell = ws_results.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment

        # Status Fills and Fonts
        pass_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
        pass_font = Font(name="Calibri", size=10, color="006100")

        fail_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
        fail_font = Font(name="Calibri", size=10, color="9C0006")

        warn_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
        warn_font = Font(name="Calibri", size=10, color="9C6500")

        regular_font = Font(name="Calibri", size=10)
        thin_border = Border(
            left=Side(style="thin", color="D9D9D9"),
            right=Side(style="thin", color="D9D9D9"),
            top=Side(style="thin", color="D9D9D9"),
            bottom=Side(style="thin", color="D9D9D9")
        )

        for row_idx, r in enumerate(self.results, start=2):
            status = str(r.get("Status", "")).upper()
            row_data = [
                r.get("TestID", ""),
                r.get("Category", ""),
                r.get("Question", ""),
                r.get("ExpectedAnswer", ""),
                r.get("ActualAnswer", ""),
                status,
                r.get("Score", 0),
                r.get("Reason", ""),
                r.get("ResponseTimeMs", 0),
                r.get("Screenshot", "")
            ]
            ws_results.append(row_data)

            # Determine row fill
            if status == "PASS":
                row_fill = pass_fill
                status_font = pass_font
            elif status == "FAIL":
                row_fill = fail_fill
                status_font = fail_font
            else:  # ERROR, TIMEOUT
                row_fill = warn_fill
                status_font = warn_font

            for col_idx in range(1, len(headers) + 1):
                cell = ws_results.cell(row=row_idx, column=col_idx)
                cell.fill = row_fill
                cell.border = thin_border
                cell.font = status_font if col_idx == 6 else regular_font

                # Alignments
                if col_idx in [1, 2, 6]:
                    cell.alignment = Alignment(horizontal="center", vertical="top")
                elif col_idx in [7, 9]:
                    cell.alignment = Alignment(horizontal="right", vertical="top")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

                # Add hyperlink for screenshot if available
                if col_idx == 10 and cell.value and os.path.exists(str(cell.value)):
                    cell.hyperlink = os.path.abspath(str(cell.value))
                    cell.font = Font(name="Calibri", size=10, underline="single", color="0563C1")

        # Auto-adjust column widths
        for col in ws_results.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                # Consider first line length for wrapped text
                first_line = val_str.split("\n")[0]
                if len(first_line) > max_len:
                    max_len = len(first_line)
            ws_results.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)

        # ----------------------------------------------------
        # Sheet 2: Summary
        # ----------------------------------------------------
        ws_summary = wb.create_sheet(title="Summary")
        ws_summary.views.sheetView[0].showGridLines = True

        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.get("Status") == "PASS")
        failed_tests = sum(1 for r in self.results if r.get("Status") == "FAIL")
        error_tests = sum(1 for r in self.results if r.get("Status") in ["ERROR", "TIMEOUT"])
        pass_pct = round((passed_tests / total_tests * 100), 1) if total_tests > 0 else 0.0

        response_times = [r.get("ResponseTimeMs", 0) for r in self.results if r.get("ResponseTimeMs", 0) > 0]
        avg_resp_time = round(sum(response_times) / len(response_times), 1) if response_times else 0

        # Title Block
        ws_summary.merge_cells("A1:D1")
        title_cell = ws_summary["A1"]
        title_cell.value = "Chatbot Automated Test Execution Summary"
        title_cell.font = Font(name="Calibri", size=16, bold=True, color="1F4E79")
        title_cell.alignment = Alignment(horizontal="left", vertical="center")

        ws_summary["A2"] = f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ws_summary["A2"].font = Font(name="Calibri", size=10, italic=True, color="595959")

        # Metrics Table
        metrics = [
            ("Total Test Cases", total_tests, None),
            ("Passed", passed_tests, pass_fill),
            ("Failed", failed_tests, fail_fill if failed_tests > 0 else None),
            ("Errors / Timeouts", error_tests, warn_fill if error_tests > 0 else None),
            ("Pass Percentage", f"{pass_pct}%", pass_fill if pass_pct >= 80 else fail_fill),
            ("Average Response Time", f"{avg_resp_time} ms", None),
        ]

        # Table Header
        ws_summary["A4"] = "Metric"
        ws_summary["B4"] = "Value"
        ws_summary["A4"].font = header_font
        ws_summary["A4"].fill = header_fill
        ws_summary["B4"].font = header_font
        ws_summary["B4"].fill = header_fill

        for idx, (label, val, fill) in enumerate(metrics, start=5):
            c_label = ws_summary.cell(row=idx, column=1, value=label)
            c_val = ws_summary.cell(row=idx, column=2, value=val)
            c_label.font = Font(name="Calibri", size=11, bold=True)
            c_val.font = Font(name="Calibri", size=11, bold=True)
            c_label.border = thin_border
            c_val.border = thin_border
            c_val.alignment = Alignment(horizontal="center")
            if fill:
                c_val.fill = fill

        ws_summary.column_dimensions["A"].width = 28
        ws_summary.column_dimensions["B"].width = 18

        wb.save(filepath)
        return filepath

    def print_terminal_summary(self):
        """Display a final stylized summary table in terminal."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.get("Status") == "PASS")
        failed = sum(1 for r in self.results if r.get("Status") == "FAIL")
        errors = sum(1 for r in self.results if r.get("Status") in ["ERROR", "TIMEOUT"])
        pct = round(passed / total * 100, 1) if total > 0 else 0

        times = [r.get("ResponseTimeMs", 0) for r in self.results if r.get("ResponseTimeMs", 0) > 0]
        avg_time = round(sum(times) / len(times), 1) if times else 0

        table = Table(title="Test Execution Summary", show_header=True, header_style="bold cyan")
        table.add_column("Total", justify="center")
        table.add_column("Passed", justify="center", style="green")
        table.add_column("Failed", justify="center", style="red")
        table.add_column("Errors/Timeouts", justify="center", style="yellow")
        table.add_column("Pass Rate", justify="center", style="bold green" if pct >= 80 else "bold red")
        table.add_column("Avg Response Time", justify="center", style="magenta")

        table.add_row(
            str(total),
            str(passed),
            str(failed),
            str(errors),
            f"{pct}%",
            f"{avg_time} ms"
        )

        console.print("\n")
        console.print(table)
        console.print("\n")

