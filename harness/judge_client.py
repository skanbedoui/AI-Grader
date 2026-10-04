#!/usr/bin/env python3
"""Judge client module providing pointwise and compare-mode evaluation calls."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from model_client import generate_response  # noqa: E402

POINTWISE_PROMPT_PATH = ROOT / "prompts" / "judge_prompt_v1.md"
COMPARE_PROMPT_PATH = ROOT / "prompts" / "judge_prompt_compare.md"


def load_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_json_response(text: str) -> dict[str, Any]:
    """Parse JSON object from model output, handling potential markdown code blocks."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Remove triple backticks and potential json language identifier
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    
    try:
        val = json.loads(cleaned)
        if isinstance(val, dict):
            return val
    except json.JSONDecodeError:
        pass
    
    # Try finding the first JSON object using regex
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            val = json.loads(match.group(0))
            if isinstance(val, dict):
                return val
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse valid JSON object from response: {text!r}")


def call_pointwise_judge(
    code_snippet: str,
    comment: str,
    language: str = "python",
    prompt_path: Path | None = None,
) -> dict[str, Any]:
    """Call the pointwise judge to grade a single review comment against a code snippet."""
    if prompt_path is None:
        prompt_path = POINTWISE_PROMPT_PATH

    system_prompt = load_prompt(prompt_path)
    user_prompt = (
        f"Language: {language}\n\n"
        f"Code snippet:\n```{language}\n{code_snippet}\n```\n\n"
        f"Candidate review comment:\n{comment}"
    )

    model_output = generate_response(user_prompt, system_prompt)
    parsed = parse_json_response(model_output.text)

    # Standardize types and fallback defaults
    verdict = str(parsed.get("verdict", "bad")).lower()
    if verdict not in ("good", "bad"):
        verdict = "bad"

    # Support both boolean and string representation
    raw_correct = parsed.get("correct", parsed.get("correctness", False))
    correct = True if str(raw_correct).lower() in ("true", "good", "yes", "1") else False

    raw_useful = parsed.get("useful", parsed.get("usefulness", False))
    useful = True if str(raw_useful).lower() in ("true", "good", "yes", "1") else False

    reason = str(parsed.get("reason", ""))

    return {
        "verdict": verdict,
        "correct": correct,
        "useful": useful,
        "reason": reason,
        "raw": model_output.text,
        "usage": model_output.usage,
    }


def call_compare_judge(
    code_snippet: str,
    comment_a: str,
    comment_b: str,
    language: str = "python",
    prompt_path: Path | None = None,
) -> dict[str, Any]:
    """Call compare-mode judge to select the better of two comments (diagnostic for position bias)."""
    if prompt_path is None:
        prompt_path = COMPARE_PROMPT_PATH

    system_prompt = load_prompt(prompt_path)
    user_prompt = (
        f"Language: {language}\n\n"
        f"Code snippet:\n```{language}\n{code_snippet}\n```\n\n"
        f"Comment A:\n{comment_a}\n\n"
        f"Comment B:\n{comment_b}"
    )

    model_output = generate_response(user_prompt, system_prompt)
    parsed = parse_json_response(model_output.text)

    winner = str(parsed.get("winner", "tie")).upper()
    if winner not in ("A", "B", "TIE"):
        winner = "TIE"

    reason = str(parsed.get("reason", ""))

    return {
        "winner": winner,
        "reason": reason,
        "raw": model_output.text,
        "usage": model_output.usage,
    }
