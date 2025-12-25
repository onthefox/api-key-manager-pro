import json
import yaml
from pathlib import Path

class ConfigLoader:
    DEFAULT_CONFIG = {
        "fetcher": {
            "timeout": 20,
            "max_retries": 3,
            "max_workers": 20,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "sources": {
                "http_file": "data/sources/http_sources.txt",
                "telegram_file": "data/sources/telegram_channels_large.json"
            }
        },
        "parser": {
            "protocols": ["vmess", "vless", "trojan", "shadowsocks", "tuic", "hysteria", "hysteria2", "juicity", "ssh", "wireguard"],
            "parse_modes": ["html", "xml", "json", "base64"]
        },
        "processor": {
            "geoip_db": "data/geoip/GeoLite2-Country.mmdb",
            "deduplicate": True,
            "filters": {
                "allowed_countries": [], # Empty list = all allowed
                "blocked_countries": ["IR", "CN", "RU"],
                "allowed_protocols": [],
                "min_score": 0,
                "exclude_ports": []
            },
            "scoring": {
                "weights": {
                    "security": 2,
                    "sni": 2,
                    "alpn": 2,
                    "flow": 2,
                    "headerType": 1,
                    "path": 1,
                    "obfs": 1,
                    "mport": 1
                }
            }
        },
        "validator": {
            "enabled": True,
            "timeout": 2,
            "max_workers": 50,
            "max_latency": 2000 # ms
        },
        "output": {
            "directory": "output",
            "formats": ["json", "txt", "yaml"],
            "categorize_by": ["protocol", "country"],
            "best_of_limit": 100,
            "filename_format": "{protocol}_{country}.txt"
        }
    }

    def __init__(self, config_path="config.yaml"):
        self.config = self.DEFAULT_CONFIG.copy()
        self.config_path = config_path
        self.load()

    def load(self):
        """Loads config from file, overriding defaults."""
        path = Path(self.config_path)
        if not path.exists():
            # Try json if yaml not found, or create default yaml
            json_path = path.with_suffix(".json")
            if json_path.exists():
                self._load_from_json(json_path)
            else:
                self.save() # Create default config file
                return

        if path.suffix in ['.yaml', '.yml']:
            self._load_from_yaml(path)
        elif path.suffix == '.json':
            self._load_from_json(path)

    def _load_from_yaml(self, path):
        try:
            with open(path, 'r') as f:
                loaded = yaml.safe_load(f)
                if loaded:
                    self._merge(self.config, loaded)
        except Exception as e:
            print(f"Error loading YAML config: {e}")

    def _load_from_json(self, path):
        try:
            with open(path, 'r') as f:
                loaded = json.load(f)
                if loaded:
                    self._merge(self.config, loaded)
        except Exception as e:
            print(f"Error loading JSON config: {e}")

    def _merge(self, base, update):
        """Recursively merge update dict into base dict."""
        for k, v in update.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                self._merge(base[k], v)
            else:
                base[k] = v

    def save(self):
        """Saves current config to file."""
        path = Path(self.config_path)
        try:
            with open(path, 'w') as f:
                if path.suffix in ['.yaml', '.yml']:
                    yaml.dump(self.config, f, default_flow_style=False)
                else:
                    json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, section, key=None):
        """Safe getter."""
        if section not in self.config:
            return None
        if key is None:
            return self.config[section]
        return self.config[section].get(key)
