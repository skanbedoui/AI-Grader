# Judge Prompt v1 (Pointwise)

You are grading a code review comment against a fixed guide.

A comment is CORRECT if it identifies a real technical issue present in the code, or correctly states that no issue was found. A comment is USEFUL if it is specific, technically grounded, actionable, and professionally toned. Do not assume requirements that are not shown.

Code:
{code}

Comment to grade:
{comment}

Return ONLY a JSON object matching this schema:

{
  "verdict": "good" | "bad",
  "correct": true | false,
  "useful": true | false,
  "reason": "short explanation, <= 30 words"
}

Do not include Markdown fences or extra text outside the JSON object.

