import json
import sys
import signal
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from core.config import ConfigLoader
from core.fetcher import UnifiedFetcher
from core.parser import ConfigParser
from core.processor import Processor
from core.validator import Validator
from core.output import OutputManager

# Global Control Flags
PAUSED = False
STOP_REQUESTED = False

def control_monitor(console):
    """Background thread to monitor user input/hotkeys (simulated via menu)."""
    global PAUSED, STOP_REQUESTED
    # In a real terminal, we might use `keyboard` or `pynput` for global hotkeys.
    # In this environment/standard CLI, we handle signals or blocking input.
    # Since we have progress bars running, blocking input on main thread is hard.
    # We will use SIGINT (Ctrl+C) to trigger the menu.
    pass

def signal_handler(sig, frame):
    """Handle Ctrl+C to show interactive menu."""
    global PAUSED, STOP_REQUESTED
    PAUSED = True
    print("\n")
    Console().print(Panel("⚠️  Process Paused! Control Menu:", style="bold yellow"))

    while True:
        choice = Prompt.ask(
            "Choose action",
            choices=["resume", "stats", "skip", "quit"],
            default="resume"
        )

        if choice == "resume":
            PAUSED = False
            print("Resuming...")
            break
        elif choice == "stats":
            print("Current Stats: [Placeholder for live stats]")
        elif choice == "skip":
            print("Skipping current stage...")
            # Logic to skip needs architectural support (state checking)
            break
        elif choice == "quit":
            STOP_REQUESTED = True
            PAUSED = False
            print("Quitting gracefully...")
            break

def main():
    # Register Signal Handler for "Hot Key" (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)

    console = Console()
    console.print(Panel.fit("Unified Proxy Collector (Universal Edition)", style="bold green"))

    # 1. Load Config
    config_loader = ConfigLoader()
    config = config_loader.config
    console.print(f"[blue]Loaded configuration from {config_loader.config_path}[/blue]")

    # 2. Load Sources
    with console.status("Loading sources..."):
        http_sources = []
        try:
            with open(config["fetcher"]["sources"]["http_file"], "r") as f:
                http_sources = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        except:
            pass

        telegram_channels = []
        try:
            with open(config["fetcher"]["sources"]["telegram_file"], "r") as f:
                telegram_channels = json.load(f)
        except:
            pass

    console.print(f"[blue]Loaded {len(http_sources)} HTTP sources and {len(telegram_channels)} Telegram channels.[/blue]")

    # Check Stop
    if STOP_REQUESTED: sys.exit(0)

    # 3. Fetch
    fetcher = UnifiedFetcher(config)
    raw_data = fetcher.fetch_all(telegram_channels, http_sources)

    # Flatten content
    all_content = []
    for item in raw_data:
        all_content.extend(item['content'])

    console.print(f"[green]Fetched {len(all_content)} raw items.[/green]")
    if len(all_content) > 0:
        print(f"Sample content (first 500 chars): {all_content[0][:500]}")

    # Check Stop
    if STOP_REQUESTED: sys.exit(0)

    # 4. Parse
    config_parser = ConfigParser(config)
    extracted_configs = config_parser.parse(all_content)
    console.print(f"[green]Extracted {len(extracted_configs)} unique config strings.[/green]")

    # 5. Process (Dedup, GeoIP, Score, Filter)
    processor = Processor(config)
    processed_configs = processor.process(extracted_configs)
    processor.close()
    console.print(f"[green]Processed {len(processed_configs)} configs (Enriched, Scored & Filtered).[/green]")

    # Check Stop
    if STOP_REQUESTED: sys.exit(0)

    # 6. Validate
    validator = Validator(config)
    processed_configs = validator.validate_configs(processed_configs)
    console.print(f"[green]Validated: {len(processed_configs)} configs are alive.[/green]")

    # 7. Output
    output_manager = OutputManager(config)
    output_manager.save(processed_configs)
    console.print(Panel.fit(f"Done! Outputs saved to {config['output']['directory']}", style="bold green"))

if __name__ == "__main__":
    main()
