#!/usr/bin/env python3
"""Calculate observed and projected LLM costs from harness JSONL output."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int


def _non_negative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def extract_usage(row: dict[str, Any]) -> Usage:
    """Read token counts from either a row's usage object or top-level fields."""
    usage = row.get("usage", row)
    if not isinstance(usage, dict):
        raise ValueError("usage must be an object")

    input_value = usage.get("input_tokens", usage.get("prompt_tokens"))
    output_value = usage.get("output_tokens", usage.get("completion_tokens"))
    if input_value is None or output_value is None:
        raise ValueError("missing input/output token counts")

    return Usage(
        input_tokens=_non_negative_int(input_value, "input_tokens"),
        output_tokens=_non_negative_int(output_value, "output_tokens"),
    )


def load_usage(path: Path) -> list[Usage]:
    rows: list[Usage] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError("row must be a JSON object")
                rows.append(extract_usage(value))
            except (json.JSONDecodeError, ValueError) as exc:
                raise ValueError(f"{path}:{line_number}: {exc}") from exc
    if not rows:
        raise ValueError(f"{path}: no usage rows found")
    return rows


def summarize_costs(
    usages: Iterable[Usage],
    input_price_per_million: float,
    output_price_per_million: float,
    daily_volume_multiplier: float,
) -> dict[str, float | int]:
    records = list(usages)
    if not records:
        raise ValueError("at least one usage record is required")
    if min(input_price_per_million, output_price_per_million) < 0:
        raise ValueError("token prices must be non-negative")
    if daily_volume_multiplier <= 0:
        raise ValueError("daily volume multiplier must be positive")

    total_input = sum(record.input_tokens for record in records)
    total_output = sum(record.output_tokens for record in records)
    total_cost = (
        total_input * input_price_per_million
        + total_output * output_price_per_million
    ) / 1_000_000
    mean_cost = total_cost / len(records)

    return {
        "items": len(records),
        "input_tokens": total_input,
        "output_tokens": total_output,
        "observed_cost_usd": total_cost,
        "mean_cost_per_item_usd": mean_cost,
        "projected_cost_per_1k_items_usd": mean_cost * 1_000,
        "projected_cost_at_100x_usd": (
            mean_cost * 1_000 * 100 * daily_volume_multiplier
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Project LLM costs from token counts logged in a harness JSONL file."
    )
    parser.add_argument("results", type=Path, help="Harness result JSONL file")
    parser.add_argument(
        "--input-price",
        type=float,
        required=True,
        metavar="USD_PER_MILLION",
        help="Input-token price in USD per million tokens",
    )
    parser.add_argument(
        "--output-price",
        type=float,
        required=True,
        metavar="USD_PER_MILLION",
        help="Output-token price in USD per million tokens",
    )
    parser.add_argument(
        "--daily-volume-multiplier",
        type=float,
        default=1.0,
        help="Expected daily-volume multiplier used by the 100x projection (default: 1)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        summary = summarize_costs(
            load_usage(args.results),
            args.input_price,
            args.output_price,
            args.daily_volume_multiplier,
        )
    except (OSError, ValueError) as exc:
        raise SystemExit(f"error: {exc}") from exc
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

