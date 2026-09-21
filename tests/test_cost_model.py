import math
import tempfile
import unittest
from pathlib import Path

from cost_model import CallUsage, ItemUsage, Prices, calculate_costs, extract_item_usage, load_results


class CostModelTests(unittest.TestCase):
    PRICES = Prices(2.0, 8.0, 3.0, 12.0)

    def item(self, si=100, so=20, ji=150, jo=30):
        return ItemUsage(CallUsage(si, so), CallUsage(ji, jo))

    def test_standard_cost_calculation_with_different_prices(self):
        measured = calculate_costs([self.item()], self.PRICES, 10)["measurement"]
        self.assertAlmostEqual(measured["system_cost_usd"], 0.00036)
        self.assertAlmostEqual(measured["judge_cost_usd"], 0.00081)
        self.assertAlmostEqual(measured["total_cost_usd"], 0.00117)

    def test_zero_tokens_cost_zero(self):
        result = calculate_costs([self.item(0, 0, 0, 0)], self.PRICES, 0)
        self.assertEqual(result["measurement"]["total_cost_usd"], 0)
        self.assertEqual(result["projection"]["estimated_daily_cost_usd"], 0)

    def test_empty_results_rejected(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            calculate_costs([], self.PRICES, 10)

    def test_negative_tokens_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-negative integer"):
            extract_item_usage({"system_usage": {"input_tokens": -1, "output_tokens": 2}, "judge_usage": {"input_tokens": 3, "output_tokens": 4}})

    def test_negative_and_non_finite_prices_rejected(self):
        for invalid in (-1.0, math.nan, math.inf):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, "finite, non-negative"):
                calculate_costs([self.item()], Prices(invalid, 1, 1, 1), 10)

    def test_missing_required_usage_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing judge_usage"):
            extract_item_usage({"system_usage": {"input_tokens": 1, "output_tokens": 2}})

    def test_multiple_items_aggregate_without_double_counting(self):
        measured = calculate_costs([self.item(), self.item()], self.PRICES, 10)["measurement"]
        self.assertEqual(measured["item_count"], 2)
        self.assertEqual(measured["tokens"]["system_input"], 200)
        self.assertAlmostEqual(measured["average_cost_per_item_usd"], 0.00117)

    def test_per_1k_daily_and_100x_projection(self):
        projection = calculate_costs([self.item()], self.PRICES, 500)["projection"]
        self.assertAlmostEqual(projection["cost_per_1k_items_usd"], 1.17)
        self.assertAlmostEqual(projection["estimated_daily_cost_usd"], 0.585)
        self.assertEqual(projection["volume_at_100x"], 50_000)
        self.assertAlmostEqual(projection["estimated_cost_at_100x_usd"], 58.5)

    def test_nested_usage_and_legacy_token_names_supported(self):
        record = extract_item_usage({"system_output": {"usage": {"prompt_tokens": 10, "completion_tokens": 2}}, "judge_verdict": {"usage": {"input_tokens": 20, "output_tokens": 3}}})
        self.assertEqual(record, self.item(10, 2, 20, 3))

    def test_empty_jsonl_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.jsonl"
            path.write_text("\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "no evaluation records"):
                load_results(path)

    def test_malformed_jsonl_reports_line(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.jsonl"
            path.write_text("not json\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, r"bad\.jsonl:1"):
                load_results(path)

    def test_negative_daily_volume_rejected(self):
        with self.assertRaisesRegex(ValueError, "daily_volume"):
            calculate_costs([self.item()], self.PRICES, -1)


if __name__ == "__main__":
    unittest.main()
