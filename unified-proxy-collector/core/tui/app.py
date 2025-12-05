from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer, Button, Label, Checkbox, Input
from textual.screen import ModalScreen
from textual.binding import Binding
from textual.worker import Worker
import asyncio

from core.tui.widgets import LogPanel, MetricsPanel, FailurePanel
from core.fetcher import UnifiedFetcher
from core.parser import ConfigParser
from core.processor import Processor
from core.validator import Validator
from core.output import OutputManager
from core.config import ConfigLoader

class PreFlightModal(ModalScreen):
    """Configuration Dialog before start."""
    def compose(self) -> ComposeResult:
        with Container(id="preflight-dialog"):
            yield Label("SYSTEM PRE-FLIGHT CONFIGURATION", classes="panel-title")
            yield Label("Proxy Protocols:")
            yield Checkbox("VMess / VLESS", value=True)
            yield Checkbox("Trojan / ShadowSocks", value=True)
            yield Checkbox("Hysteria / TUIC", value=True)
            yield Label("Performance:")
            yield Input(placeholder="Worker Threads (e.g. 50)", id="worker-input")
            yield Button("INITIATE SEQUENCE", variant="primary", id="start-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-btn":
            self.dismiss(True)

class ProxyCollectorApp(App):
    """Tri-Panel TUI Orchestrator"""
    CSS_PATH = "style.css"
    BINDINGS = [
        Binding("space", "toggle_workflow", "Start/Pause"),
        Binding("q", "quit", "Quit"),
        Binding("d", "toggle_dark", "Toggle Dark Mode"),
    ]

    def __init__(self):
        super().__init__()
        self.config_loader = ConfigLoader()
        self.config = self.config_loader.config
        self.is_running = False
        self.worker_task = None

        # Core Components
        self.fetcher = UnifiedFetcher(self.config)
        self.parser = ConfigParser(self.config)
        self.processor = Processor(self.config)
        self.validator = Validator(self.config)
        self.output_manager = OutputManager(self.config)

        # State metrics
        self.metrics = {
            "fetched": 0,
            "parsed": 0,
            "unique": 0,
            "validated": 0
        }

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main-layout"):
            yield LogPanel(id="log-panel", classes="panel")
            yield MetricsPanel(id="metrics-panel", classes="panel")
            yield FailurePanel(id="failure-panel", classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        self.push_screen(PreFlightModal(), self.on_preflight_complete)

    def on_preflight_complete(self, result: bool) -> None:
        if result:
            self.log_msg("System Initialized. Press SPACE to start.")

    def action_toggle_workflow(self) -> None:
        if self.is_running:
            self.is_running = False
            self.log_msg("Workflow PAUSED.", "WARNING")
        else:
            self.is_running = True
            self.log_msg("Workflow STARTED.", "INFO")
            self.run_worker(self.run_scraping_loop(), exclusive=True, group="scraper")

    async def run_scraping_loop(self):
        """Main async orchestration loop."""
        self.log_msg("Loading sources...")

        # Load sources (Async simulation)
        http_sources = []
        try:
            with open(self.config["fetcher"]["sources"]["http_file"], "r") as f:
                http_sources = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        except Exception as e:
            self.log_error("Load Sources", str(e))

        telegram_channels = []
        try:
            with open(self.config["fetcher"]["sources"]["telegram_file"], "r") as f:
                import json
                telegram_channels = json.load(f)
        except Exception as e:
            self.log_error("Load Sources", str(e))

        self.log_msg(f"Loaded {len(http_sources)} HTTP sources and {len(telegram_channels)} Channels.")

        # Fetch
        self.log_msg("Initiating Fetch Phase...")
        # Since UnifiedFetcher is synchronous (requests), we wrap it or use it as is blocking worker thread.
        # Ideally, we refactor Fetcher to be async, but for now we run it in a thread.

        raw_data = await asyncio.to_thread(self.fetcher.fetch_all, telegram_channels, http_sources)

        all_content = []
        for item in raw_data:
            if "content" in item:
                all_content.extend(item['content'])

        self.metrics["fetched"] = len(all_content)
        self.update_metrics_ui()
        self.log_msg(f"Fetched {len(all_content)} raw items.")

        if not self.is_running: return

        # Parse
        self.log_msg("Initiating Parse Phase...")
        extracted_configs = self.parser.parse(all_content)
        self.metrics["parsed"] = len(extracted_configs)
        self.update_metrics_ui()
        self.log_msg(f"Extracted {len(extracted_configs)} configs.")

        if not self.is_running: return

        # Process
        self.log_msg("Initiating Processing Phase (Dedup/GeoIP)...")
        processed_configs = await asyncio.to_thread(self.processor.process, extracted_configs)
        self.metrics["unique"] = len(processed_configs)
        self.update_metrics_ui()
        self.log_msg(f"Processed {len(processed_configs)} unique configs.")

        if not self.is_running: return

        # Validate
        self.log_msg("Initiating Validation Phase...")
        # Validator is also threaded internally, so wrapping in thread is fine
        validated_configs = await asyncio.to_thread(self.validator.validate_configs, processed_configs)
        self.metrics["validated"] = len(validated_configs)
        self.update_metrics_ui()
        self.log_msg(f"Validated {len(validated_configs)} functional proxies.")

        # Output
        self.output_manager.save(validated_configs)
        self.log_msg("Workflow Complete. Data Saved.", "INFO")
        self.is_running = False

    def log_msg(self, msg, level="INFO"):
        self.query_one("#log-panel", LogPanel).log(msg, level)

    def log_error(self, source, msg):
        self.query_one("#failure-panel", FailurePanel).log_error(source, msg)

    def update_metrics_ui(self):
        panel = self.query_one("#metrics-panel", MetricsPanel)
        panel.update_metric(0, self.metrics["fetched"], "")
        panel.update_metric(1, self.metrics["parsed"], "")
        panel.update_metric(2, self.metrics["unique"], "")
        panel.update_metric(3, self.metrics["validated"], "")

if __name__ == "__main__":
    app = ProxyCollectorApp()
    app.run()
