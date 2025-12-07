import os
import json
import yaml
from datetime import datetime

class OutputManager:
    def __init__(self, config):
        self.config = config.get("output")
        self.output_dir = self.config.get("directory", "output")
        self.formats = self.config.get("formats", ["json", "txt"])
        self.filename_format = self.config.get("filename_format", "{protocol}_{country}.txt")
        self.best_of_limit = self.config.get("best_of_limit", 100)

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def save(self, configs):
        # Universal Save Logic based on config
        if "json" in self.formats:
            self._save_json(configs)
        if "yaml" in self.formats:
            self._save_yaml(configs)
        if "txt" in self.formats:
            self._save_txt_structure(configs)
            self._save_best_of(configs)

    def _save_json(self, configs):
        filepath = os.path.join(self.output_dir, "all_configs.json")
        data = {
            "generated_at": datetime.now().isoformat(),
            "total_count": len(configs),
            "items": configs
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _save_yaml(self, configs):
        filepath = os.path.join(self.output_dir, "all_configs.yaml")
        data = {
            "generated_at": datetime.now().isoformat(),
            "total_count": len(configs),
            "items": configs
        }
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    def _save_best_of(self, configs):
        # Sort by score descending
        sorted_configs = sorted(configs, key=lambda x: x.get('score', 0), reverse=True)
        top_n = sorted_configs[:self.best_of_limit]

        filepath = os.path.join(self.output_dir, "best_proxies.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            for item in top_n:
                f.write(item['config'] + "\n")

    def _save_txt_structure(self, configs):
        """
        Saves categorized text files based on config Selectivity.
        """
        protocols_dir = os.path.join(self.output_dir, "protocols")
        countries_dir = os.path.join(self.output_dir, "countries")

        os.makedirs(protocols_dir, exist_ok=True)
        os.makedirs(countries_dir, exist_ok=True)

        by_proto = {}
        by_country = {}

        for item in configs:
            proto = item.get('info', {}).get('protocol', 'unknown')
            country = item.get('info', {}).get('country', 'NA')

            if proto not in by_proto: by_proto[proto] = []
            by_proto[proto].append(item['config'])

            if country not in by_country: by_country[country] = []
            by_country[country].append(item['config'])

        # Save Protocols
        for proto, items in by_proto.items():
            path = os.path.join(protocols_dir, f"{proto}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(items))

        # Save Countries
        for country, items in by_country.items():
            path = os.path.join(countries_dir, f"{country}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(items))
