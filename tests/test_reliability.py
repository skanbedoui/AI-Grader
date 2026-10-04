#!/usr/bin/env python3
"""Unit tests for Yasmine's LLM Judge & Reliability track."""

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.judge_client import parse_json_response
from harness.reliability import compute_cohen_kappa, human_consensus_label, PADDING_TEXT


class TestReliabilityTrack(unittest.TestCase):

    def test_parse_json_response_clean(self):
        text = '{"verdict": "good", "correct": true, "useful": true, "reason": "looks good"}'
        parsed = parse_json_response(text)
        self.assertEqual(parsed["verdict"], "good")
        self.assertTrue(parsed["correct"])

    def test_parse_json_response_with_markdown_fences(self):
        text = '```json\n{"verdict": "bad", "correct": false, "useful": false, "reason": "vague"}\n```'
        parsed = parse_json_response(text)
        self.assertEqual(parsed["verdict"], "bad")
        self.assertFalse(parsed["correct"])

    def test_parse_json_response_embedded(self):
        text = 'Here is the JSON output:\n{"winner": "A", "reason": "more specific"}'
        parsed = parse_json_response(text)
        self.assertEqual(parsed["winner"], "A")

    def test_human_consensus_label(self):
        self.assertEqual(human_consensus_label("good", "good"), "good")
        self.assertEqual(human_consensus_label("bad", "bad"), "bad")
        self.assertEqual(human_consensus_label("good", "bad"), "good")

    def test_compute_cohen_kappa_perfect_agreement(self):
        y_true = ["good", "bad", "good", "bad", "good"]
        y_pred = ["good", "bad", "good", "bad", "good"]
        pct_agree, kappa = compute_cohen_kappa(y_true, y_pred)
        self.assertEqual(pct_agree, 100.0)
        self.assertEqual(kappa, 1.0)

    def test_compute_cohen_kappa_partial_agreement(self):
        y_true = ["good", "good", "bad", "bad", "good"]
        y_pred = ["good", "bad", "bad", "bad", "good"]
        pct_agree, kappa = compute_cohen_kappa(y_true, y_pred)
        self.assertEqual(pct_agree, 80.0)
        self.assertGreater(kappa, 0.0)

    def test_padding_text_exists(self):
        self.assertIn("readability", PADDING_TEXT)


if __name__ == "__main__":
    unittest.main()
