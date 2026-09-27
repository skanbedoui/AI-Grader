# Judge Prompt v1

You are grading one code-review comment. Read the code and the candidate comment.

A comment is correct if it identifies a real technical issue in the shown code, or correctly says that no issue was found. A comment is useful if it is specific, technically grounded, professional, and actionable where appropriate. Do not assume requirements that are not shown.

Return only valid JSON matching this schema:

{"verdict":"good|bad","correctness":"good|bad","usefulness":"good|bad","reason":"short explanation"}

Do not include Markdown fences or text outside the JSON object.
