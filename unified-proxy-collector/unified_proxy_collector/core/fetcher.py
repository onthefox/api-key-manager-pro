import requests
import time
import concurrent.futures
import logging
from bs4 import BeautifulSoup
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.console import Console

logger = logging.getLogger("unified_proxy_collector")

class UnifiedFetcher:
    def __init__(self, config):
        self.config = config.get("fetcher")
        self.max_workers = self.config.get("max_workers", 20)
        self.timeout = self.config.get("timeout", 20)
        self.max_retries = self.config.get("max_retries", 3)
        self.user_agent = self.config.get("user_agent")

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.user_agent
        })
        self.console = Console()

    def fetch_url_with_retry(self, url):
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                logger.debug(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(1)
                continue
        logger.warning(f"Failed to fetch {url} after {self.max_retries} attempts")
        return None

    def fetch_telegram_channel(self, channel_name):
        """
        Scrapes a Telegram channel's web preview (t.me/s/...)
        Returns a list of message texts.
        """
        # Support full URL or just username
        if channel_name.startswith("http"):
            url = channel_name
            if "t.me/s/" not in url and "t.me/" in url:
                url = url.replace("t.me/", "t.me/s/")
        else:
            url = f"https://t.me/s/{channel_name}"

        html_content = self.fetch_url_with_retry(url)
        if not html_content:
            return []

        try:
            soup = BeautifulSoup(html_content, "html.parser") # bs4 handles html/xml/xhtml
            messages = soup.find_all("div", class_="tgme_widget_message_text")
            extracted_texts = []
            for msg in messages:
                text = msg.get_text(separator="\n")
                extracted_texts.append(text)
            return extracted_texts
        except Exception:
            return []

    def fetch_all(self, telegram_channels, http_sources):
        """
        Fetches data from both Telegram channels and HTTP sources concurrently.
        """
        results = []

        total_tasks = len(telegram_channels) + len(http_sources)
        if total_tasks == 0:
            return []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=self.console
        ) as progress:
            task_id = progress.add_task("Fetching sources...", total=total_tasks)

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit HTTP tasks
                http_futures = {
                    executor.submit(self.fetch_url_with_retry, url): ("http", url)
                    for url in http_sources
                }

                # Submit Telegram tasks
                tg_futures = {
                    executor.submit(self.fetch_telegram_channel, channel): ("telegram", channel)
                    for channel in telegram_channels
                }

                futures = {**http_futures, **tg_futures}

                for future in concurrent.futures.as_completed(futures):
                    source_type, source = futures[future]
                    try:
                        data = future.result()
                        if data:
                            if source_type == "http":
                                # Determine if it's XML/Json/HTML?
                                # For now, just pass content. The Parser will handle types.
                                results.append({"type": "http", "source": source, "content": [data]})
                            else:
                                if isinstance(data, list) and data:
                                     results.append({"type": "telegram", "source": source, "content": data})
                    except Exception:
                        pass
                    finally:
                        progress.update(task_id, advance=1)

        return results
