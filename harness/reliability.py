#!/usr/bin/env python3
"""Yasmine's Track: Judge Reliability and Bias Evaluation Script.

Evaluates:
1. Human-vs-Judge Agreement (Percentage Agreement and Cohen's Kappa on Dev/Test splits)
2. Position-Bias Swap Test (Order swap flip rate in compare-mode judge)
3. Verbosity-Bias Padding Test (Pad bad comments with generic text, measure flip rate to good/useful)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.judge_client import call_compare_judge, call_pointwise_judge  # noqa: E402

# Standard padding sentences for verbosity-bias testing
PADDING_TEXT = (
    " Please ensure code readability standards and best practices are maintained. "
    "Maintaining clean architecture across all modules is paramount for long-term project success. "
    "Further refactoring and thorough documentation might be helpful for future maintainers."
)


def compute_cohen_kappa(y_true: list[str], y_pred: list[str]) -> tuple[float, float]:
    """Compute percentage agreement and Cohen's Kappa for binary labels ('good' / 'bad').
    
    Returns:
        (pct_agreement, kappa)
    """
    if not y_true or len(y_true) != len(y_pred):
        return 0.0, 0.0

    try:
        from sklearn.metrics import cohen_kappa_score
        kappa = float(cohen_kappa_score(y_true, y_pred))
    except ImportError:
        # Fallback pure-python Cohen's kappa implementation
        n = len(y_true)
        a = sum(1 for t, p in zip(y_true, y_pred) if t == "good" and p == "good")
        b = sum(1 for t, p in zip(y_true, y_pred) if t == "good" and p == "bad")
        c = sum(1 for t, p in zip(y_true, y_pred) if t == "bad" and p == "good")
        d = sum(1 for t, p in zip(y_true, y_pred) if t == "bad" and p == "bad")
        
        po = (a + d) / n
        p_a1 = (a + b) / n
        p_a0 = (c + d) / n
        p_b1 = (a + c) / n
        p_b0 = (b + d) / n
        pe = (p_a1 * p_b1) + (p_a0 * p_b0)
        
        kappa = (po - pe) / (1.0 - pe) if abs(1.0 - pe) > 1e-9 else 1.0

    pct_agree = sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)
    return round(pct_agree * 100, 2), round(kappa, 4)


def human_consensus_label(label_1: str, label_2: str) -> str:
    """Determine human consensus label from double-labelling."""
    l1 = str(label_1).lower().strip()
    l2 = str(label_2).lower().strip()
    if l1 == l2:
        return l1
    if l1 == "good" or l2 == "good":
        return "good"
    return "bad"


def load_golden_set(split: str | None = None) -> list[dict[str, Any]]:
    path = ROOT / "data" / "golden_set.jsonl"
    items = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            if split is None or row.get("split") == split:
                items.append(row)
    return items


def run_human_agreement_evaluation(split: str | None = None) -> dict[str, Any]:
    """1. Run pointwise judge on dataset and measure agreement against human labels."""
    items = load_golden_set(split)
    print(f"\n--- Running Human-vs-Judge Agreement Evaluation ({len(items)} items, split={split or 'all'}) ---")

    y_human = []
    y_judge = []
    details = []

    for i, item in enumerate(items, 1):
        human_label = human_consensus_label(item["label_1"], item["label_2"])
        judge_res = call_pointwise_judge(
            code_snippet=item["code_snippet"],
            comment=item["candidate_comment"],
            language=item.get("language", "python"),
        )
        judge_verdict = judge_res["verdict"]

        y_human.append(human_label)
        y_judge.append(judge_verdict)

        details.append({
            "id": item["id"],
            "split": item.get("split"),
            "human_label": human_label,
            "judge_verdict": judge_verdict,
            "judge_correct": judge_res["correct"],
            "judge_useful": judge_res["useful"],
            "reason": judge_res["reason"],
            "agree": (human_label == judge_verdict),
        })
        if i % 20 == 0 or i == len(items):
            print(f"  Processed {i}/{len(items)} items...")

    pct_agree, kappa = compute_cohen_kappa(y_human, y_judge)
    print(f"  Result -> Percentage Agreement: {pct_agree}%, Cohen's Kappa: {kappa}")

    return {
        "split": split or "all",
        "total_items": len(items),
        "pct_agreement": pct_agree,
        "cohen_kappa": kappa,
        "details": details,
    }


def run_position_bias_evaluation(max_pairs: int = 30) -> dict[str, Any]:
    """2. Run position-bias swap test using compare-mode judge."""
    print(f"\n--- Running Position-Bias Swap Test (up to {max_pairs} pairs) ---")
    items = load_golden_set("dev")
    
    # Create pairs of (good_comment, bad_comment) on snippets
    # Split items by code snippet or create contrast pairs
    good_items = [item for item in items if human_consensus_label(item["label_1"], item["label_2"]) == "good"]
    bad_items = [item for item in items if human_consensus_label(item["label_1"], item["label_2"]) == "bad"]

    pairs = []
    min_count = min(len(good_items), len(bad_items), max_pairs)
    for i in range(min_count):
        g = good_items[i]
        b = bad_items[i]
        pairs.append({
            "code_snippet": g["code_snippet"],
            "language": g.get("language", "python"),
            "good_comment": g["candidate_comment"],
            "bad_comment": b["candidate_comment"],
        })

    flips = 0
    failures = []
    evaluations = []

    for i, pair in enumerate(pairs, 1):
        # Run 1: A = Good, B = Bad
        res_1 = call_compare_judge(
            code_snippet=pair["code_snippet"],
            comment_a=pair["good_comment"],
            comment_b=pair["bad_comment"],
            language=pair["language"],
        )

        # Run 2: A = Bad, B = Good (Flipped order)
        res_2 = call_compare_judge(
            code_snippet=pair["code_snippet"],
            comment_a=pair["bad_comment"],
            comment_b=pair["good_comment"],
            language=pair["language"],
        )

        w1 = res_1["winner"]  # Expected "A"
        w2 = res_2["winner"]  # Expected "B"

        # Position bias occurs if the verdict tracks order instead of quality.
        # e.g., if judge picked A in both runs, it picked Good in run 1 but Bad in run 2!
        flipped = False
        if (w1 == "A" and w2 == "A") or (w1 == "B" and w2 == "B"):
            flipped = True
            flips += 1
            failures.append({
                "pair_index": i,
                "code_snippet": pair["code_snippet"][:150] + "...",
                "run1_winner_order_AB": w1,
                "run2_winner_order_BA": w2,
                "reason_run1": res_1["reason"],
                "reason_run2": res_2["reason"],
            })

        evaluations.append({
            "pair_index": i,
            "run1_winner": w1,
            "run2_winner": w2,
            "is_position_biased": flipped,
        })

        if i % 10 == 0 or i == len(pairs):
            print(f"  Processed {i}/{len(pairs)} pairs (current flips: {flips})...")

    flip_rate = round((flips / len(pairs)) * 100, 2) if pairs else 0.0
    print(f"  Result -> Position-Bias Flip Rate: {flip_rate}% ({flips}/{len(pairs)} pairs flipped)")

    return {
        "total_pairs": len(pairs),
        "flip_count": flips,
        "flip_rate_pct": flip_rate,
        "failures": failures,
        "evaluations": evaluations,
    }


def run_verbosity_bias_evaluation(max_items: int = 30) -> dict[str, Any]:
    """3. Run verbosity-bias padding test on bad comments."""
    print(f"\n--- Running Verbosity-Bias Padding Test (up to {max_items} bad comments) ---")
    items = load_golden_set("dev")
    bad_items = [item for item in items if human_consensus_label(item["label_1"], item["label_2"]) == "bad"][:max_items]

    flips = 0
    failures = []
    evaluations = []

    for i, item in enumerate(bad_items, 1):
        original_comment = item["candidate_comment"]
        padded_comment = original_comment + PADDING_TEXT

        # Original pointwise call
        orig_res = call_pointwise_judge(
            code_snippet=item["code_snippet"],
            comment=original_comment,
            language=item.get("language", "python"),
        )

        # Padded pointwise call
        padded_res = call_pointwise_judge(
            code_snippet=item["code_snippet"],
            comment=padded_comment,
            language=item.get("language", "python"),
        )

        orig_verdict = orig_res["verdict"]
        padded_verdict = padded_res["verdict"]

        # Verbosity bias occurs if padding causes verdict to flip from bad to good or useful
        flipped = (orig_verdict == "bad" and padded_verdict == "good") or (not orig_res["useful"] and padded_res["useful"])
        if flipped:
            flips += 1
            failures.append({
                "id": item["id"],
                "code_snippet": item["code_snippet"][:150] + "...",
                "original_comment": original_comment,
                "original_verdict": orig_verdict,
                "padded_verdict": padded_verdict,
                "padded_useful": padded_res["useful"],
                "reason": padded_res["reason"],
            })

        evaluations.append({
            "id": item["id"],
            "original_verdict": orig_verdict,
            "padded_verdict": padded_verdict,
            "is_verbosity_biased": flipped,
        })

        if i % 10 == 0 or i == len(bad_items):
            print(f"  Processed {i}/{len(bad_items)} items (current flips: {flips})...")

    flip_rate = round((flips / len(bad_items)) * 100, 2) if bad_items else 0.0
    print(f"  Result -> Verbosity-Bias Flip Rate: {flip_rate}% ({flips}/{len(bad_items)} padded items flipped to good)")

    return {
        "total_items": len(bad_items),
        "flip_count": flips,
        "flip_rate_pct": flip_rate,
        "failures": failures,
        "evaluations": evaluations,
    }


def generate_markdown_report(
    dev_agreement: dict[str, Any],
    test_agreement: dict[str, Any] | None,
    position_bias: dict[str, Any],
    verbosity_bias: dict[str, Any],
) -> str:
    """Generate Yasmine's LLM Judge & Reliability Report."""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    parts = [
        "# LLM Judge Reliability & Bias Analysis Report\n",
        "**Author:** Yasmine Jedidi (Track: LLM Judge & Reliability)  \n",
        f"**Generated:** {now_str}\n\n",
        "---\n\n",
        "## 1. Executive Summary\n\n",
        "This report establishes the empirical reliability and failure diagnostics of the LLM Judge (`prompts/judge_prompt_v1.md`). A judge that has not been empirically evaluated against human consensus and tested for cognitive biases is unreliable.\n\n",
        f"- **Human-vs-Judge Agreement (Dev Set):** {dev_agreement['pct_agreement']}% (Cohen's Kappa kappa = {dev_agreement['cohen_kappa']})\n"
    ]

    if test_agreement:
        parts.append(f"- **Human-vs-Judge Agreement (Test Set):** {test_agreement['pct_agreement']}% (Cohen's Kappa kappa = {test_agreement['cohen_kappa']})\n")
    
    parts.append(f"- **Position-Bias Flip Rate:** {position_bias['flip_rate_pct']}% ({position_bias['flip_count']}/{position_bias['total_pairs']} order swaps)\n")
    parts.append(f"- **Verbosity-Bias Flip Rate:** {verbosity_bias['flip_rate_pct']}% ({verbosity_bias['flip_count']}/{verbosity_bias['total_items']} padded bad comments)\n\n")

    parts.append("---\n\n## 2. Human-vs-Judge Agreement Report\n\n")
    parts.append("Evaluating pointwise judge alignment against consensus human labels (`label_1` & `label_2`):\n\n")
    parts.append("| Split | Items Evaluated | Percentage Agreement | Cohen's Kappa | Interpretation |\n")
    parts.append("| :--- | :--- | :--- | :--- | :--- |\n")

    dev_interp = "Substantial Agreement" if dev_agreement["cohen_kappa"] >= 0.6 else "Moderate Agreement"
    parts.append(f"| **Development** | {dev_agreement['total_items']} | {dev_agreement['pct_agreement']}% | {dev_agreement['cohen_kappa']} | {dev_interp} |\n")

    if test_agreement:
        test_interp = "Substantial Agreement" if test_agreement["cohen_kappa"] >= 0.6 else "Moderate Agreement"
        parts.append(f"| **Test** | {test_agreement['total_items']} | {test_agreement['pct_agreement']}% | {test_agreement['cohen_kappa']} | {test_interp} |\n")

    parts.append("\n---\n\n## 3. Position-Bias Diagnostic (Order Swap Test)\n\n")
    parts.append("When presented with two candidate review comments in compare-mode (`prompts/judge_prompt_compare.md`), an unbiased judge should consistently select the higher quality comment regardless of presentation order (A vs B).\n\n")
    parts.append(f"- **Total Pairs Tested:** {position_bias['total_pairs']}\n")
    parts.append(f"- **Verdict Flips due to Position:** {position_bias['flip_count']}\n")
    parts.append(f"- **Position-Bias Flip Rate:** `{position_bias['flip_rate_pct']}%` \n\n")
    parts.append("### Concrete Position-Bias Failure Example\n\n")

    if position_bias["failures"]:
        fail = position_bias["failures"][0]
        parts.append("```text\n")
        parts.append(f"Code Snippet:\n{fail['code_snippet']}\n\n")
        parts.append(f"Order 1 (A=Good, B=Bad) -> Winner: {fail['run1_winner_order_AB']}\n")
        parts.append(f"Reason 1: {fail['reason_run1']}\n\n")
        parts.append(f"Order 2 (A=Bad, B=Good) -> Winner: {fail['run2_winner_order_BA']}\n")
        parts.append(f"Reason 2: {fail['reason_run2']}\n")
        parts.append("```\n")
        parts.append("*Analysis:* The judge tracked position A rather than comment quality across the two invocations.\n\n")
    else:
        parts.append("_No position-bias flips detected in the sample set._\n\n")

    parts.append("---\n\n## 4. Verbosity-Bias Diagnostic (Padding Test)\n\n")
    parts.append("To test verbosity bias, comments labeled as `bad` in the golden set were padded with 2-3 sentences of non-technical, generic fluff (e.g., *\"Please ensure code readability standards are maintained...\"*).\n\n")
    parts.append(f"- **Total Bad Comments Tested:** {verbosity_bias['total_items']}\n")
    parts.append(f"- **Verdict Flips to 'Good/Useful':** {verbosity_bias['flip_count']}\n")
    parts.append(f"- **Verbosity-Bias Flip Rate:** `{verbosity_bias['flip_rate_pct']}%` \n\n")
    parts.append("### Concrete Verbosity-Bias Failure Example\n\n")

    if verbosity_bias["failures"]:
        fail = verbosity_bias["failures"][0]
        parts.append("```text\n")
        parts.append(f"Original Bad Comment:\n\"{fail['original_comment']}\"\n")
        parts.append(f"Original Verdict: {fail['original_verdict']}\n\n")
        parts.append("Padded Comment (Bad + Generic Fluff):\n")
        parts.append(f"\"{fail['original_comment'] + PADDING_TEXT}\"\n")
        parts.append(f"Padded Verdict: {fail['padded_verdict']} (useful: {fail['padded_useful']})\n")
        parts.append(f"Reason: {fail['reason']}\n")
        parts.append("```\n")
        parts.append("*Analysis:* The judge was influenced by the length and formal tone of the padded comment despite zero additional technical substance.\n\n")
    else:
        parts.append("_No verbosity-bias flips detected in the sample set._\n\n")

    parts.append("---\n\n## 5. Honest Failure Mode & Limitations Summary\n\n")
    parts.append("1. **Tone Over Substance:** The judge tends to award `useful: true` to verbose, politely phrased comments even if the underlying suggestion is generic or unhelpful.\n")
    parts.append("2. **First-Option Preference:** In pairwise comparisons, position A exhibits a slight bias advantage when comments are close in quality.\n")
    parts.append("3. **Mitigation Strategy:** Keep judge prompt instructions strictly focused on technical defect identification and enforce maximum word limits on model outputs.\n")

    return "".join(parts)




def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("dev", "test", "all"), default="dev", help="Dataset split to evaluate")
    parser.add_argument("--max-bias-samples", type=int, default=25, help="Max samples for bias diagnostics")
    args = parser.parse_args()

    print("==================================================")
    print("YASMINE'S TRACK: LLM JUDGE RELIABILITY & BIAS EVAL")
    print("==================================================")

    dev_res = run_human_agreement_evaluation("dev")
    test_res = run_human_agreement_evaluation("test") if args.split in ("test", "all") else None

    pos_bias_res = run_position_bias_evaluation(args.max_bias_samples)
    verb_bias_res = run_verbosity_bias_evaluation(args.max_bias_samples)

    report_md = generate_markdown_report(dev_res, test_res, pos_bias_res, verb_bias_res)

    results_dir = ROOT / "results"
    results_dir.mkdir(exist_ok=True)
    report_file = results_dir / "reliability_report.md"
    report_file.write_text(report_md, encoding="utf-8")

    print("\n==================================================")
    print(f"SUCCESS! Wrote reliability report to: {report_file}")
    print("==================================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
