import socket
import concurrent.futures
import time
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

class Validator:
    def __init__(self, config):
        self.config = config.get("validator")
        self.enabled = self.config.get("enabled", True)
        self.timeout = self.config.get("timeout", 2)
        self.max_workers = self.config.get("max_workers", 50)
        self.max_latency = self.config.get("max_latency", 2000)

    def validate_tcp(self, host, port):
        try:
            start_time = time.time()
            sock = socket.create_connection((host, int(port)), timeout=self.timeout)
            latency = (time.time() - start_time) * 1000
            sock.close()
            return latency
        except:
            return None

    def validate_configs(self, processed_configs):
        if not self.enabled:
            return processed_configs

        validated_configs = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        ) as progress:
            task = progress.add_task("Validating configs...", total=len(processed_configs))

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_config = {}

                for item in processed_configs:
                    info = item.get('info', {})
                    ip = info.get('ip')
                    port = info.get('port')

                    # Regex fallback for port if not extracted by Processor
                    if (not port) and ip and item['config']:
                        import re
                        match = re.search(f"{re.escape(ip)}:(\\d+)", item['config'])
                        if match:
                            port = match.group(1)

                    if ip and port:
                        future = executor.submit(self.validate_tcp, ip, port)
                        future_to_config[future] = item
                    else:
                        # Can't validate without IP:Port.
                        # If "Selectivity" demands robust error handling, we mark as -1 or discard.
                        # Let's keep but mark invalid.
                        item['latency'] = -1
                        # validated_configs.append(item) # Optional: Don't append if strict
                        progress.update(task, advance=1)

                for future in concurrent.futures.as_completed(future_to_config):
                    item = future_to_config[future]
                    try:
                        latency = future.result()
                        if latency is not None:
                            if latency <= self.max_latency:
                                item['latency'] = round(latency, 2)
                                validated_configs.append(item)
                    except:
                        pass
                    finally:
                        progress.update(task, advance=1)

        return validated_configs
