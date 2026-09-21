import tempfile
import unittest
from pathlib import Path

from cost_model import Usage, extract_usage, load_usage, summarize_costs


class CostModelTests(unittest.TestCase):
    def test_extracts_current_and_legacy_usage_names(self) -> None:
        self.assertEqual(
            extract_usage({"usage": {"input_tokens": 10, "output_tokens": 4}}),
            Usage(10, 4),
        )
        self.assertEqual(
            extract_usage({"prompt_tokens": 8, "completion_tokens": 2}),
            Usage(8, 2),
        )

    def test_sums_system_and_judge_usage(self) -> None:
        row = {
            "system_output": {
                "comment": "No issue found.",
                "usage": {"input_tokens": 100, "output_tokens": 10},
            },
            "judge_verdict": {
                "verdict": "good",
                "usage": {"input_tokens": 130, "output_tokens": 20},
            },
        }
        self.assertEqual(extract_usage(row), Usage(230, 30))

    def test_prefers_combined_usage_over_component_usage(self) -> None:
        row = {
            "usage": {"input_tokens": 12, "output_tokens": 3},
            "system_usage": {"input_tokens": 8, "output_tokens": 2},
            "judge_usage": {"input_tokens": 4, "output_tokens": 1},
        }
        self.assertEqual(extract_usage(row), Usage(12, 3))

    def test_calculates_observed_and_projected_cost(self) -> None:
        summary = summarize_costs([Usage(100, 50), Usage(300, 50)], 2.0, 8.0, 2.0)
        self.assertEqual(summary["items"], 2)
        self.assertAlmostEqual(summary["observed_cost_usd"], 0.0016)
        self.assertAlmostEqual(summary["mean_cost_per_item_usd"], 0.0008)
        self.assertAlmostEqual(summary["projected_cost_per_1k_items_usd"], 0.8)
        self.assertAlmostEqual(summary["projected_cost_at_100x_usd"], 160.0)

    def test_reports_bad_jsonl_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.jsonl"
            path.write_text('{"usage":{"input_tokens":1}}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, r"run\.jsonl:1"):
                load_usage(path)


if __name__ == "__main__":
    unittest.main()
