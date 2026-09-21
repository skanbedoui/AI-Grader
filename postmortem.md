# Project Postmortem

This document records only issues supported by the current repository. Teammates should add their own evidence rather than having it inferred on their behalf.

## What worked

- The team selected a task where exact matching is inappropriate but human quality judgments can be defined as correctness and usefulness.
- The checked-in dataset has 160 items, two labels per row, a 112/48 development/test split, and documented agreement (86.25%, kappa 0.72).
- Keeping prompts in versioned files makes prompt changes reviewable and prevents an unrecorded prompt from becoming the reported system.
- The cost model keeps measured run totals separate from volume projections and accepts different prices for the system and judge.

## What did not work yet

The first concrete integration problem was that the prompt/cost track arrived before the harness interface. No `harness/`, dependency manifest, result JSONL, model configuration, or token-logging contract is present. As a result, v1 cannot be evaluated honestly, v2 cannot be justified by failures, and a clean-clone end-to-end check cannot run. The response was to keep metrics explicitly pending and define the minimum usage interface instead of fabricating results or implementing a teammate's track.

An early cost-model design combined system and judge token totals under one price. That was insufficient because the two calls may use different models. The implementation was revised to preserve four token categories and four configurable prices, preventing accidental double-counting and making projections auditable.

## What we learned

- Interfaces should be agreed before parallel implementation. Each result row needs separate `system_usage` and `judge_usage`, with input/output token counts, plus latency and model identifiers.
- A prompt version is an experiment only when its model settings, development items, outputs, verdicts, and timestamp are preserved. A rewritten prompt without those records is not measured improvement.
- Cost per item is driven by both prompt length and generated output. A judge can cost more than the system because it receives the code and candidate comment and may use a different model.
- Scaling cost linearly is useful as a baseline, not a guarantee. Caching and batching can reduce effective cost; retries can increase it; rate limits and concurrency determine achievable throughput.

## Remaining limitations

- There is no measured system quality, cost, or latency result.
- Judge agreement, position bias, and verbosity bias are pending Yasmine's implementation.
- The dataset report describes aggregate agreement, but final reporting should also retain counts and any dropped-item evidence required by the assignment.
- The provisional report cannot be finalized until all owned results are integrated and reviewed.

## Next improvements

1. Khalil documents the exact result-row schema and adds separate call usage and latency.
2. Yasmine integrates the judge and publishes dev reliability evidence.
3. Abdallah runs v1 on the development split, categorizes real failures, and creates v2 only if those failures justify a targeted change.
4. The team freezes the selected prompt, authorizes one test run, updates the report, and performs the clean-clone reproduction check.

