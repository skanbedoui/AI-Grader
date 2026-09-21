# System Prompt Changelog

Prompt versions are evaluated only on the development split while prompts are being iterated. The test split is reserved for one evaluation after the final prompt is frozen. Scores are recorded from timestamped harness output; they are never estimated or entered from memory.

## Version 1 — Baseline

Date: 2026-09-21

Reason: establish a simple system prompt that Khalil's harness can integrate before evidence-based iteration begins.

Changes: request one professional comment about a demonstrable issue, reject unsupported assumptions, handle snippets with no demonstrable issue, and emit only the shared `{"comment": "string"}` JSON schema.

Development configuration: pending. The harness, model identifier, decoding settings, and timestamped development result are not present in the repository.

Development evaluation:

- Evaluated items: pending
- Good verdict rate: pending
- Correctness rate: pending
- Usefulness rate: pending
- Mean cost per item: pending
- Mean latency: pending

Previous score: N/A (initial version)

New score: pending harness-core and judge integration

Observations: no performance claim can be made yet. Version 2 must be motivated by categorized failures from the development split; it must not be created merely to imply progress.

Remaining limitations: Khalil's system caller must load this file, pass the code snippet as the user message, and enforce the shared schema. That calling convention is not yet implemented in this repository.
