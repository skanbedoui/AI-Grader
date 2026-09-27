#!/usr/bin/env python3
"""Run the system and judge over a dataset split and write per-item JSONL."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import get_openai_model, get_ollama_model, get_provider  # noqa: E402
from model_client import generate_response  # noqa: E402

load_dotenv(ROOT / ".env")


def load_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_json_object(text: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} returned invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must return a JSON object")
    return value


def system_request(row: dict[str, Any]) -> str:
    return (
        f"Language: {row['language']}\n\n"
        f"Code snippet:\n```{row['language']}\n{row['code_snippet']}\n```"
    )


def judge_request(row: dict[str, Any], comment: str) -> str:
    return (
        f"Language: {row['language']}\n\n"
        f"Code snippet:\n```{row['language']}\n{row['code_snippet']}\n```\n\n"
        f"Candidate review comment:\n{comment}"
    )


def model_metadata() -> dict[str, str]:
    provider = get_provider()
    model = get_ollama_model() if provider == "ollama" else get_openai_model()
    return {"provider": provider, "model": model}


def run(args: argparse.Namespace) -> tuple[Path, int]:
    dataset_path = ROOT / "data" / "golden_set.jsonl"
    system_prompt = load_prompt(ROOT / "prompts" / "system_prompt_v1.md")
    judge_prompt = load_prompt(ROOT / "prompts" / "judge_prompt_v1.md")
    output_dir = ROOT / "results"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"{args.split}_{timestamp}.jsonl"
    metadata = model_metadata()
    error_count = 0

    with dataset_path.open(encoding="utf-8") as source, output_path.open("w", encoding="utf-8") as target:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("split") != args.split:
                continue

            result: dict[str, Any] = {
                "id": row["id"],
                "split": args.split,
                "input": {
                    "language": row["language"],
                    "code_snippet": row["code_snippet"],
                },
                "system_model": metadata,
                "judge_model": metadata,
            }
            try:
                system_started = time.perf_counter()
                system_output = generate_response(system_request(row), system_prompt)
                system_latency_ms = (time.perf_counter() - system_started) * 1000
                parsed_system = parse_json_object(system_output.text, "system")
                comment = parsed_system.get("comment")
                if not isinstance(comment, str):
                    raise ValueError("system JSON must contain a string 'comment'")

                judge_started = time.perf_counter()
                judge_output = generate_response(judge_request(row, comment), judge_prompt)
                judge_latency_ms = (time.perf_counter() - judge_started) * 1000
                verdict = parse_json_object(judge_output.text, "judge")

                result.update({
                    "system_output": {
                        "comment": comment,
                        "raw": system_output.text,
                        "usage": system_output.usage,
                        "latency_ms": round(system_latency_ms, 2),
                    },
                    "judge_verdict": {
                        **verdict,
                        "raw": judge_output.text,
                        "usage": judge_output.usage,
                        "latency_ms": round(judge_latency_ms, 2),
                    },
                    "human_labels": {
                        "label_1": row["label_1"],
                        "label_2": row["label_2"],
                    },
                    "status": "ok",
                })
            except Exception as exc:  # Keep one result row for every input item.
                error_count += 1
                result.update({"status": "error", "error": f"line {line_number}: {exc}"})

            target.write(json.dumps(result, ensure_ascii=False) + "\n")

    return output_path, error_count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("dev", "test"), required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    output_path, error_count = run(args)
    print(f"Wrote results to {output_path}")
    if error_count:
        print(f"Completed with {error_count} item error(s).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
