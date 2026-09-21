# System Prompt Changelog

Prompt versions are evaluated only on the development split while prompts are being iterated. The test split is reserved for one evaluation after the final prompt is frozen. Scores are recorded from timestamped harness output; they are never estimated or entered from memory.

## v1 — 2026-09-21

Changed: added the baseline structured-output prompt. It asks for one grounded, actionable comment, permits an explicit no-issue judgment for clean code, and returns the shared `{"comment": "string"}` schema.

Dev score: pending the harness-core integration (before: N/A; after: pending).

The score must be replaced with the measured overall, correct, and useful rates from the first development run before a v2 prompt is created.

