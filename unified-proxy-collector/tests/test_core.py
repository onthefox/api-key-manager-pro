import unittest
from unittest.mock import patch
from core.config import ConfigLoader
from core.parser import ConfigParser
from core.processor import Processor
from core.validator import Validator
from core.output import OutputManager

class TestUnifiedCollector(unittest.TestCase):

    def setUp(self):
        self.config_loader = ConfigLoader()
        self.config = self.config_loader.config

        # Test Data
        self.sample_configs = [
            "vmess://eyJhZGQiOiIxMjcuMC4wLjEiLCJwb3J0IjoiNDQzIiwicHMiOiJUZXN0Vk1FU1MiLCJ0bHMiOiJ0bHMifQ==",
            "vless://uuid@127.0.0.1:443?security=tls&type=ws&sni=test.com#TestVLESS",
            "ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTpwYXNzd29yZA==@1.2.3.4:8888#TestSS"
        ]

    def test_config_loader(self):
        self.assertIsNotNone(self.config.get("fetcher"))
        self.assertEqual(self.config["fetcher"]["timeout"], 20)

    def test_parser(self):
        parser = ConfigParser(self.config)
        # Mock HTML content containing links
        html_content = [
            "Here is a config: vmess://eyJhZGQiOiIxMjcuMC4wLjEiLCJwb3J0IjoiNDQzIiwicHMiOiJUZXN0Vk1FU1MiLCJ0bHMiOiJ0bHMifQ==",
            "Another one <br> vless://uuid@127.0.0.1:443?security=tls&type=ws&sni=test.com#TestVLESS"
        ]
        parsed = parser.parse(html_content)
        self.assertEqual(len(parsed), 2)
        self.assertTrue(any("vmess" in p for p in parsed))

    def test_processor(self):
        processor = Processor(self.config)
        processed = processor.process(self.sample_configs)

        self.assertEqual(len(processed), 3)
        vmess_item = next(p for p in processed if p['info']['protocol'] == 'vmess')

        # Check Enrichment (IP extraction)
        self.assertEqual(vmess_item['info']['ip'], "127.0.0.1")
        self.assertEqual(vmess_item['info']['port'], "443")

        # Check Scoring (TLS bonus)
        # Base(1) + TLS(2) = 3 (weights in config)
        self.assertGreaterEqual(vmess_item['score'], 1)

    @patch('socket.create_connection')
    def test_validator(self, mock_socket):
        # Mock successful connection
        mock_socket.return_value.close.return_value = None

        validator = Validator(self.config)
        # Using processed output from previous step manually constructed
        processed_input = [
            {'config': 'c1', 'info': {'ip': '1.1.1.1', 'port': 80}, 'score': 10},
            {'config': 'c2', 'info': {'ip': '2.2.2.2', 'port': 80}, 'score': 5}
        ]

        validated = validator.validate_configs(processed_input)
        self.assertEqual(len(validated), 2)
        self.assertIsNotNone(validated[0]['latency'])

    def test_output_manager(self):
        output = OutputManager(self.config)
        test_data = [
            {'config': 'test_conf', 'info': {'protocol': 'vmess', 'country': 'US'}, 'score': 10, 'latency': 50}
        ]

        # Mock file writing to avoid clutter
        with patch("builtins.open", unittest.mock.mock_open()) as mock_file:
            output.save(test_data)
            # Should open JSON, YAML, TXT files
            self.assertTrue(mock_file.called)

if __name__ == '__main__':
    unittest.main()
