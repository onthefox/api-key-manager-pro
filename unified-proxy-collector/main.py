import argparse
import sys
from core.tui.app import ProxyCollectorApp

def main():
    parser = argparse.ArgumentParser(description="Unified Proxy Collector")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode (no TUI)")
    parser.add_argument("--workers", type=int, default=50, help="Number of threads (Headless only)")
    parser.add_argument("--fetch-http", action="store_true", default=True)
    parser.add_argument("--fetch-telegram", action="store_true", default=True)
    parser.add_argument("--validate", action="store_true", default=True)

    args = parser.parse_args()

    if args.headless:
        # Run legacy CLI mode
        from rich.console import Console
        from rich.panel import Panel
        from core.config import ConfigLoader
        from core.fetcher import UnifiedFetcher
        from core.parser import ConfigParser
        from core.processor import Processor
        from core.validator import Validator
        from core.output import OutputManager
        import json

        console = Console()
        console.print(Panel.fit("Unified Proxy Collector (Headless)", style="bold green"))

        config_loader = ConfigLoader()
        config = config_loader.config

        # Override config with args if needed
        if args.workers:
            config["fetcher"]["max_workers"] = args.workers

        # Load Sources
        http_sources = []
        try:
            with open(config["fetcher"]["sources"]["http_file"], "r") as f:
                http_sources = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        except: pass

        telegram_channels = []
        try:
            with open(config["fetcher"]["sources"]["telegram_file"], "r") as f:
                telegram_channels = json.load(f)
        except: pass

        fetcher = UnifiedFetcher(config)
        raw_data = fetcher.fetch_all(telegram_channels, http_sources)

        all_content = []
        for item in raw_data:
            all_content.extend(item['content'])

        parser = ConfigParser(config)
        extracted = parser.parse(all_content)

        processor = Processor(config)
        processed = processor.process(extracted)

        if args.validate:
            validator = Validator(config)
            processed = validator.validate_configs(processed)

        output = OutputManager(config)
        output.save(processed)
        console.print("[green]Job Complete.[/green]")

    else:
        # Run TUI
        app = ProxyCollectorApp()
        app.run()

if __name__ == "__main__":
    main()
