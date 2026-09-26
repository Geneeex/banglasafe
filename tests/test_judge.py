import json
import unittest

from banglasafe.judge import _parse


class ParseReasoningTests(unittest.TestCase):
    def test_truncated_json_preserves_unicode_reasoning(self):
        for reasoning in ("বাংলা যুক্তি", "café — safe"):
            payload = json.dumps({"label": "REFUSE", "reasoning": reasoning}, ensure_ascii=False)
            for suffix_length in (1, 2):
                with self.subTest(reasoning=reasoning, suffix_length=suffix_length):
                    self.assertEqual(_parse(payload[:-suffix_length]), ("REFUSE", reasoning))

    def test_truncated_json_decodes_json_escapes(self):
        for reasoning, ensure_ascii in (("বাংলা যুক্তি", True), ("first line\nsecond line", False)):
            payload = json.dumps({"label": "POLICY", "reasoning": reasoning}, ensure_ascii=ensure_ascii)
            with self.subTest(reasoning=reasoning):
                self.assertEqual(_parse(payload[:-1]), ("POLICY", reasoning))

    def test_truncated_escape_keeps_recoverable_reasoning(self):
        reasoning = "বাংলা " + r"\u09"
        payload = '{"label": "REFUSE", "reasoning": "' + reasoning
        self.assertEqual(_parse(payload), ("REFUSE", reasoning))

    def test_complete_json_preserves_unicode_reasoning(self):
        reasoning = "বাংলা যুক্তি"
        payload = json.dumps({"label": "REFUSE", "reasoning": reasoning}, ensure_ascii=False)
        self.assertEqual(_parse(payload), ("REFUSE", reasoning))
