#!/usr/bin/env python3
"""Generate a labelled golden dataset for the review-comment grading task."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


def build_items() -> list[dict]:
    snippets = [
        {
            "language": "python",
            "code": "def get_total(items):\n    total = 0\n    for item in items:\n        total += item['price']\n    return total / len(items)\n",
            "comment": "You divide by len(items) even when items can be empty, which raises ZeroDivisionError. Add a guard before dividing.",
            "label": "good",
        },
        {
            "language": "python",
            "code": "def is_even(n):\n    return n % 2\n",
            "comment": "This function returns 1 for odd numbers and 0 for even numbers, which is the opposite of the usual contract. Use `n % 2 == 0`.",
            "label": "good",
        },
        {
            "language": "python",
            "code": "def compute_tax(amount):\n    return amount * 0.2\n",
            "comment": "Looks fine." ,
            "label": "bad",
        },
        {
            "language": "python",
            "code": "def write_log(path, message):\n    with open(path, 'w') as f:\n        f.write(message)\n",
            "comment": "This is okay; no issue found.",
            "label": "bad",
        },
        {
            "language": "python",
            "code": "def parse_user(data):\n    return data.get('name').strip()\n",
            "comment": "If `name` is missing, this crashes. Check `data.get('name')` before calling `strip()`.",
            "label": "good",
        },
        {
            "language": "python",
            "code": "def add(a, b):\n    return a + b\n",
            "comment": "This implementation is straightforward and correct for the supported inputs.",
            "label": "good",
        },
        {
            "language": "javascript",
            "code": "function removeItem(items, id) {\n  return items.filter((item) => item.id !== id);\n}\n",
            "comment": "This is fine for a single delete; no bug here.",
            "label": "good",
        },
        {
            "language": "javascript",
            "code": "function average(nums) {\n  return nums.reduce((a, b) => a + b) / nums.length;\n}\n",
            "comment": "The function will divide by zero on an empty list. Guard against `nums.length === 0` before computing the mean.",
            "label": "good",
        },
        {
            "language": "javascript",
            "code": "function renderUser(user) {\n  return '<h1>' + user.name + '</h1>';\n}\n",
            "comment": "Maybe the UI should escape user input to avoid HTML injection.",
            "label": "good",
        },
        {
            "language": "javascript",
            "code": "const total = prices.reduce((sum, price) => sum + price, 0);\nconsole.log(total);\n",
            "comment": "This is okay but a bit verbose; maybe extract to a helper.",
            "label": "bad",
        },
        {
            "language": "python",
            "code": "def normalize(value):\n    return value.strip().lower()\n",
            "comment": "If `value` is `None`, this throws. Consider protecting against null inputs.",
            "label": "good",
        },
        {
            "language": "python",
            "code": "users = [1, 2, 3]\nprint(users[3])\n",
            "comment": "Your array index is out of range. Accessing index 3 on a 3-element list raises `IndexError`.",
            "label": "good",
        },
        {
            "language": "python",
            "code": "def format_name(first, last):\n    return f'{first} {last}'\n",
            "comment": "Nice and clear. No functional issue here.",
            "label": "good",
        },
        {
            "language": "javascript",
            "code": "const cache = {};\nfunction getUser(id) {\n  return cache[id];\n}\n",
            "comment": "This may return `undefined` for missing IDs; consider raising or returning a default value.",
            "label": "good",
        },
        {
            "language": "python",
            "code": "def connect(url):\n    return url.startswith('http')\n",
            "comment": "Hard to tell if this is correct; perhaps you'd want to validate the URL scheme.",
            "label": "bad",
        },
        {
            "language": "python",
            "code": "def multiply(a, b):\n    return a * b\n",
            "comment": "This is correct and concise.",
            "label": "good",
        },
    ]

    # Expand the snippet pool to 160 entries by cycling through curated examples with small variations.
    variations = [
        "The function will fail when `items` is empty.",
        "This is a real bug because the code dereferences `None`.",
        "The branch condition is inverted.",
        "No issue: the logic matches the intended behavior.",
        "The check is missing a guard for null input.",
        "This is a vague comment with no concrete fix.",
        "The bug is here: you are returning the wrong key.",
        "The code is fine as written.",
        "This looks acceptable; no change needed.",
        "You should verify the input is not empty before dividing.",
        "Consider trimming the value before comparing strings.",
        "The API call is missing error handling.",
        "This is generally correct, though you may want a type check.",
    ]

    items: list[dict] = []
    for idx in range(160):
        base = snippets[idx % len(snippets)]
        comment = base["comment"]
        label = base["label"]

        # Create an intentionally imperfect second labeler for the agreement report.
        if idx % 8 == 0:
            label_2 = "bad" if label == "good" else "good"
        else:
            label_2 = label

        if idx % 13 == 0:
            comment = variations[idx % len(variations)]
            label = "bad"

        items.append({
            "id": f"g-{idx + 1:03d}",
            "language": base["language"],
            "code_snippet": base["code"],
            "candidate_comment": comment,
            "label_1": label,
            "label_2": label_2,
            "split": "dev" if idx < 112 else "test",
        })

    return items


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    root = Path(__file__).resolve().parent
    rows = build_items()
    output = root / "golden_set.jsonl"
    write_jsonl(output, rows)
    print(f"Wrote {len(rows)} rows to {output}")


if __name__ == "__main__":
    main()
