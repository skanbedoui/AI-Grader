# Labelling Guide for Review Comment Quality

## Objective
A review comment is considered correct when it identifies a real issue in a code snippet, or correctly says that no issue is present. A comment is useful when it is specific, actionable, and professionally toned.

## Decision rule
- Correct = True when the comment points to a real defect or correctly says there is no defect.
- Useful = True when the comment gives a concrete problem, a precise fix, or a justified no-issue judgment.
- Borderline = Acceptable only when it is technically plausible and grounded in the code, but not strong enough to be a high-quality review comment.

## Examples
### Example 1 — Good
Code:
```python
if user is None:
    return ""
return user.name.strip()
```
Comment: "This will crash if `user.name` is `None`; guard against missing values before calling `strip()`."
Reason: This is precise, actionable, and rooted in a real failure mode.

### Example 2 — Good
Code:
```python
def total(items):
    return sum(items) / len(items)
```
Comment: "If `items` is empty, this raises a ZeroDivisionError. Add a guard before dividing."
Reason: Correct and useful because it identifies the failing input condition and a fix.

### Example 3 — Bad
Comment: "Looks fine."
Reason: No concrete issue is identified, so it is not useful and may be incorrect if a bug exists.

### Example 4 — Bad
Comment: "Maybe this is wrong somehow."
Reason: Vague and non-actionable; it does not identify a real code issue.

### Example 5 — Borderline
Comment: "This could be a null-handling bug."
Reason: It hints at a possible issue but lacks enough specificity or action.

### Example 6 — Good (no issue found)
Code:
```python
def add(a, b):
    return a + b
```
Comment: "This implementation is correct and straightforward for the supported inputs."
Reason: It correctly says there is no bug and does so clearly.

## Summary
Score comments as:
- Good: correct + useful
- Acceptable: correct but weak / somewhat useful
- Bad: wrong, vague, or irrelevant
