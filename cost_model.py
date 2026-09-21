#!/usr/bin/env python3
"""Calculate measured and projected system-and-judge API costs from JSONL results."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class CallUsage:
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class ItemUsage:
    system: CallUsage
    judge: CallUsage


@dataclass(frozen=True)
class Prices:
    system_input: float
    system_output: float
    judge_input: float
    judge_output: float


def _tokens(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _price(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{field} must be a finite, non-negative number")
    return number


def _call_usage(value: Any, field: str) -> CallUsage:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    input_value = value.get("input_tokens", value.get("prompt_tokens"))
    output_value = value.get("output_tokens", value.get("completion_tokens"))
    if input_value is None or output_value is None:
        raise ValueError(f"{field} is missing input_tokens or output_tokens")
    return CallUsage(
        _tokens(input_value, f"{field}.input_tokens"),
        _tokens(output_value, f"{field}.output_tokens"),
    )


def extract_item_usage(row: dict[str, Any]) -> ItemUsage:
    """Extract system and judge usage without combining or double-counting calls."""
    system = row.get("system_usage")
    judge = row.get("judge_usage")
    if system is None and isinstance(row.get("system_output"), dict):
        system = row["system_output"].get("usage")
    if judge is None and isinstance(row.get("judge_verdict"), dict):
        judge = row["judge_verdict"].get("usage")
    if system is None:
        raise ValueError("missing system_usage (or system_output.usage)")
    if judge is None:
        raise ValueError("missing judge_usage (or judge_verdict.usage)")
    return ItemUsage(_call_usage(system, "system_usage"), _call_usage(judge, "judge_usage"))


def load_results(path: Path) -> list[ItemUsage]:
    records: list[ItemUsage] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError("row must be a JSON object")
                records.append(extract_item_usage(row))
            except (json.JSONDecodeError, ValueError) as exc:
                raise ValueError(f"{path}:{line_number}: {exc}") from exc
    if not records:
        raise ValueError(f"{path}: no evaluation records found")
    return records


def calculate_costs(
    records: Iterable[ItemUsage], prices: Prices, daily_volume: int
) -> dict[str, Any]:
    items = list(records)
    if not items:
        raise ValueError("at least one evaluation record is required")
    daily_volume = _tokens(daily_volume, "daily_volume")
    checked_prices = Prices(
        _price(prices.system_input, "system_input_price"),
        _price(prices.system_output, "system_output_price"),
        _price(prices.judge_input, "judge_input_price"),
        _price(prices.judge_output, "judge_output_price"),
    )
    system_input = sum(item.system.input_tokens for item in items)
    system_output = sum(item.system.output_tokens for item in items)
    judge_input = sum(item.judge.input_tokens for item in items)
    judge_output = sum(item.judge.output_tokens for item in items)
    system_cost = (system_input * checked_prices.system_input + system_output * checked_prices.system_output) / 1_000_000
    judge_cost = (judge_input * checked_prices.judge_input + judge_output * checked_prices.judge_output) / 1_000_000
    total_cost = system_cost + judge_cost
    average = total_cost / len(items)
    return {
        "measurement": {
            "item_count": len(items),
            "tokens": {"system_input": system_input, "system_output": system_output, "judge_input": judge_input, "judge_output": judge_output},
            "prices_usd_per_million_tokens": asdict(checked_prices),
            "system_cost_usd": system_cost,
            "judge_cost_usd": judge_cost,
            "total_cost_usd": total_cost,
            "average_cost_per_item_usd": average,
        },
        "projection": {
            "cost_per_1k_items_usd": average * 1_000,
            "daily_volume": daily_volume,
            "estimated_daily_cost_usd": average * daily_volume,
            "volume_at_100x": daily_volume * 100,
            "estimated_cost_at_100x_usd": average * daily_volume * 100,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Calculate observed and projected costs from harness JSONL usage.")
    parser.add_argument("results", type=Path, help="Per-item harness result JSONL")
    for call in ("system", "judge"):
        for direction in ("input", "output"):
            parser.add_argument(f"--{call}-{direction}-price", type=float, required=True, metavar="USD_PER_MILLION")
    parser.add_argument("--daily-volume", type=int, required=True, metavar="ITEMS")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    prices = Prices(args.system_input_price, args.system_output_price, args.judge_input_price, args.judge_output_price)
    try:
        report = calculate_costs(load_results(args.results), prices, args.daily_volume)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"error: {exc}") from exc
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
