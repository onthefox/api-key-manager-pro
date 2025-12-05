from textual.widgets import RichLog, Static, DataTable, Header, Footer
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from rich.text import Text

class PanelHeader(Static):
    """Header for a panel"""
    def __init__(self, title: str, id: str = None):
        super().__init__(title, id=id, classes="panel-title")

class LogPanel(Vertical):
    """Left Panel: Real-time logs"""
    def compose(self) -> ComposeResult:
        yield PanelHeader("WORKFLOW LOGS", id="log-header")
        yield RichLog(id="log-widget", wrap=True, markup=True, highlight=True)

    def log(self, message, level="INFO"):
        log_widget = self.query_one("#log-widget", RichLog)
        color = "green" if level == "INFO" else "yellow" if level == "WARNING" else "red"
        log_widget.write(Text(f"[{level}] {message}", style=color))

class MetricsPanel(Vertical):
    """Center Panel: Success Metrics"""
    def compose(self) -> ComposeResult:
        yield PanelHeader("OPERATIONAL METRICS", id="metrics-header")
        yield DataTable(id="metrics-table")

    def on_mount(self):
        table = self.query_one("#metrics-table", DataTable)
        table.add_columns("Metric", "Value", "Delta")
        table.add_rows([
            ("Fetched Items", "0", "+0"),
            ("Parsed Configs", "0", "+0"),
            ("Unique Configs", "0", "+0"),
            ("Validated Alive", "0", "+0"),
            ("Avg Latency", "0ms", "~"),
            ("Top Score", "0", "-")
        ])

    def update_metric(self, row_idx, value, delta):
        table = self.query_one("#metrics-table", DataTable)
        table.update_cell_at(row_idx, 1, str(value))
        table.update_cell_at(row_idx, 2, str(delta))

class FailurePanel(Vertical):
    """Right Panel: Failure Diagnostics"""
    def compose(self) -> ComposeResult:
        yield PanelHeader("FAILURE TAXONOMY", id="failure-header")
        yield RichLog(id="failure-widget", wrap=True, markup=True)

    def log_error(self, source, error):
        log_widget = self.query_one("#failure-widget", RichLog)
        log_widget.write(Text(f"[{source}] {error}", style="bold red"))
