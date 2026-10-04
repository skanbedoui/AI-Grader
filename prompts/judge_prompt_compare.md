# Compare-Mode Judge Prompt (Bias Testing)

Given the code below and two candidate review comments, determine which comment is better.

Code:
{code}

Comment A:
{comment_a}

Comment B:
{comment_b}

Return ONLY a JSON object matching this schema:

{
  "winner": "A" | "B" | "tie",
  "reason": "short explanation, <= 30 words"
}

Do not include Markdown fences or extra text outside the JSON object.
