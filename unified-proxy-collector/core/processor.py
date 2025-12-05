import geoip2.database
import re
import urllib.parse
import os
import json
import base64

class Processor:
    def __init__(self, config):
        self.config = config.get("processor")
        self.geoip_db_path = self.config.get("geoip_db")
        self.reader = None
        self.dedup_enabled = self.config.get("deduplicate", True)
        self.filters = self.config.get("filters", {})
        self.score_weights = self.config.get("scoring", {}).get("weights", {})

        try:
            if os.path.exists(self.geoip_db_path):
                self.reader = geoip2.database.Reader(self.geoip_db_path)
        except Exception as e:
            pass

    def process(self, configs):
        # 1. Deduplicate
        if self.dedup_enabled:
            unique_configs = list(set(configs))
        else:
            unique_configs = configs

        processed_configs = []

        for config in unique_configs:
            # 2. Enrich & Parse details
            info = self.enrich(config)

            # 3. Filter
            if self._is_filtered(info):
                continue

            # 4. Score
            score = self.calculate_score(config, info)

            processed_configs.append({
                "config": config,
                "info": info,
                "score": score,
                "latency": None # Placeholder for validator
            })

        # 5. Sort (Default by score)
        processed_configs.sort(key=lambda x: x['score'], reverse=True)
        return processed_configs

    def _is_filtered(self, info):
        """Returns True if config should be dropped based on filters."""
        allowed_countries = self.filters.get("allowed_countries", [])
        blocked_countries = self.filters.get("blocked_countries", [])
        allowed_protocols = self.filters.get("allowed_protocols", [])
        min_score = self.filters.get("min_score", 0)
        exclude_ports = self.filters.get("exclude_ports", [])

        # Country filter
        country = info.get("country", "NA")
        if allowed_countries and country not in allowed_countries:
            return True
        if country in blocked_countries:
            return True

        # Protocol filter
        if allowed_protocols and info.get("protocol") not in allowed_protocols:
            return True

        # Port filter
        if info.get("port") and int(info.get("port")) in exclude_ports:
            return True

        return False

    def enrich(self, config_str):
        info = {
            "country": "NA",
            "ip": None,
            "port": None,
            "protocol": "unknown",
            "security": "unknown"
        }

        # Determine protocol
        if config_str.startswith("vmess://"): info["protocol"] = "vmess"
        elif config_str.startswith("vless://"): info["protocol"] = "vless"
        elif config_str.startswith("ss://"): info["protocol"] = "shadowsocks"
        elif config_str.startswith("trojan://"): info["protocol"] = "trojan"
        elif config_str.startswith("tuic://"): info["protocol"] = "tuic"
        elif config_str.startswith("hysteria://"): info["protocol"] = "hysteria"
        elif config_str.startswith("hy2://"): info["protocol"] = "hysteria2"
        elif config_str.startswith("wireguard://"): info["protocol"] = "wireguard"
        elif config_str.startswith("ssh://"): info["protocol"] = "ssh"

        # Try to extract IP/Port
        # Simplified logic. For full "Universality", we should strictly parse each proto.
        # But regex for IP is 90% effective for enrichment.

        ip_match = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", config_str)
        if ip_match:
            info["ip"] = ip_match.group(0)

        # If vmess, decode json to get IP/Port/Security accurately
        if info["protocol"] == "vmess":
            try:
                b64 = config_str.replace("vmess://", "")
                decoded = base64.b64decode(b64).decode("utf-8", errors="ignore")
                data = json.loads(decoded)
                info["ip"] = data.get("add")
                info["port"] = data.get("port")
                info["security"] = data.get("tls", "none")
            except:
                pass

        # GeoIP
        if info["ip"] and self.reader:
            try:
                response = self.reader.country(info["ip"])
                info["country"] = response.country.iso_code or "NA"
            except:
                pass

        return info

    def calculate_score(self, profile, info):
        # Implementation of Project 2 scoring + Extra logic
        try:
            score = 0

            # Base score
            score += 1

            # Security bonus
            if "tls" in profile or info.get("security") == "tls":
                score += self.score_weights.get("security", 0)

            # Params parsing for other bonuses
            if "?" in profile:
                params_str = profile.split("?")[1].split("#")[0]
                params = urllib.parse.parse_qs(params_str)

                if "sni" in params: score += self.score_weights.get("sni", 0)
                if "alpn" in params: score += self.score_weights.get("alpn", 0)
                if "flow" in params: score += self.score_weights.get("flow", 0)
                if "fp" in params: score += 1

            return score
        except:
            return 0

    def close(self):
        if self.reader:
            self.reader.close()
