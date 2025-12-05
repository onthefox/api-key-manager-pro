import re
import base64
import json
import html

class ConfigParser:
    def __init__(self, config):
        self.config = config.get("parser")
        self.allowed_protocols = self.config.get("protocols", [])

        # Regex patterns covering all requested protocols + new ones
        self.patterns = {
            'vmess': r"(?<![\w-])(vmess://[^\s<>#]+)",
            'vless': r"(?<![\w-])(vless://(?:(?!=reality)[^\s<>#])+(?=[\s<>#]))",
            'reality': r"(?<![\w-])(vless://[^\s<>#]+?security=reality[^\s<>#]*)",
            'shadowsocks': r"(?<![\w-])(ss://[^\s<>#]+)",
            'trojan': r"(?<![\w-])(trojan://[^\s<>#]+)",
            'tuic': r"(?<![\w-])(tuic://[^\s<>#]+)",
            'hysteria': r"(?<![\w-])(hysteria://[^\s<>#]+)",
            'hysteria2': r"(?<![\w-])(hy2://[^\s<>#]+)",
            'juicity': r"(?<![\w-])(juicity://[^\s<>#]+)",
            'wireguard': r"(?<![\w-])(wireguard://[^\s<>#]+)",
            'ssh': r"(?<![\w-])(ssh://[^\s<>#]+)"
        }

    def parse(self, content_list):
        """
        Parses a list of text content (messages or file lines) and extracts config links.
        Returns a list of unique config strings.
        """
        extracted_configs = []

        for text in content_list:
            if not text:
                continue

            # Universal cleanup: unescape HTML entities (covers HTML/XML/XHTML sources)
            text = html.unescape(text)

            for protocol, pattern in self.patterns.items():
                # Check if protocol is enabled in config
                if self.allowed_protocols and protocol not in self.allowed_protocols and protocol != "reality":
                     # "reality" is technically vless but often treated separately.
                     # If vless is allowed, reality usually implies vless.
                     if protocol == "reality" and "vless" not in self.allowed_protocols:
                         continue
                     elif protocol != "reality":
                         continue

                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    clean_match = self._cleanup_match(match, protocol)
                    if clean_match:
                        extracted_configs.append(clean_match)

        return list(set(extracted_configs))

    def _cleanup_match(self, match, protocol):
        # Remove trailing hash/remarks temporarily for cleaner normalization
        # But we might want to keep it if we want to preserve titles.
        # Project 3 removed titles for dedup. Let's keep title for now, Processor will handle dedup.
        match = match.strip()

        if protocol == 'shadowsocks':
             if "…" in match: return None

        return match

    # ... (Helpers from previous step for Node Info Extraction remain implicitly useful for Processor)
