# AI-Grader

AI-Grader is an evaluation harness project for code-review comment quality. A system LLM receives a code snippet and returns exactly one review comment. A separate LLM judge grades whether that comment is correct and useful. Exact string matching is inappropriate because multiple differently worded comments can identify the same defect.

## Current status

The repository currently contains the golden dataset, labelling documentation, baseline system prompt, and standalone cost model. The harness and judge tracks have not landed, so end-to-end system scores, judge reliability results, bias results, and final API costs are pending. No unmeasured result is claimed here.

## Architecture

```text
code snippet -> system LLM -> {"comment": "..."}
             -> LLM judge  -> structured correctness/usefulness verdict
             -> harness    -> one JSONL result per dataset item
             -> analysis   -> quality, latency, and cost summaries
```

The development split is used for prompt iteration. The reserved test split must be evaluated once only after the final prompt is frozen.

## Repository structure

```text
data/                    Golden set, labelling guide, agreement report, builder
prompts/                 Versioned system prompt and prompt changelog
tests/test_cost_model.py Abdallah's cost-model tests
cost_model.py            Measured cost aggregation and scale projections
README.md                Setup, methodology, status, and contributions
report.html              Editable provisional report source
report.pdf               Generated provisional report (when present)
postmortem.md             Evidence-based project retrospective
```

The planned `harness/` and `results/` directories are pending their owners' integration.

## Installation

Python 3.10 or newer is sufficient for the files currently present; they use only the standard library.

```bash
python --version
python -m unittest discover -s tests -v
```

An API SDK installation command cannot be documented until the harness dependency manifest is added. Store future credentials in an ignored `.env` file or the shell environment; never commit API keys. The expected variable name must be documented by the harness owner.

## Running the project

Rebuild the checked-in dataset from Skander's deterministic generator:

```bash
python data/build_dataset.py
```

This overwrites `data/golden_set.jsonl`; do not use it merely to validate manual dataset edits.

The planned end-to-end command is `python harness/run.py --split dev`, but it is not runnable because `harness/run.py` does not yet exist. Do not run the test split during prompt development.

## Evaluation methodology

A comment is correct when it identifies a real issue or correctly reports that no issue is present. It is useful when it is specific, actionable where appropriate, and professionally worded. Each dataset row has two human labels and a locked `dev` or `test` split. The future harness must store input, structured system output, structured judge verdict and reason, separate token usage for both calls, and latency for every item.

The dataset contains 160 items (112 development, 48 test; 110 Python, 50 JavaScript). The checked-in agreement report records 86.25% human agreement and Cohen's kappa of 0.72. No system or judge score is currently available.

## Prompt engineering

`prompts/system_prompt_v1.md` is the baseline. Khalil's caller should load it as the system instruction, pass the code snippet separately as the user message, and enforce `{"comment": "string"}` as structured output. Development results must be logged before adding v2. Each later version must address observed failures and receive a before/after entry in `prompts/CHANGELOG.md`; previous versions must remain unchanged.

## Cost model

The calculator requires per-item usage for both calls, either as `system_usage`/`judge_usage` or as `system_output.usage`/`judge_verdict.usage`. Each usage object contains integer `input_tokens` and `output_tokens` (legacy `prompt_tokens` and `completion_tokens` are also accepted).

```bash
python cost_model.py results/<run_id>.jsonl \
  --system-input-price <usd-per-million> \
  --system-output-price <usd-per-million> \
  --judge-input-price <usd-per-million> \
  --judge-output-price <usd-per-million> \
  --daily-volume <items>
```

Prices are explicit because providers and models can differ and pricing changes. The output separates measured token totals and run costs from projected cost per 1,000 items, daily cost, and cost at 100x daily volume. Projections assume constant usage and list price; batching and prompt caching may lower cost, while retries add cost and rate limits constrain throughput. Concurrency changes throughput, not unit token cost by itself.

## Results

| Measure | Available result |
|---|---:|
| Dataset size | 160 |
| Development/test split | 112 / 48 |
| Human agreement | 86.25% |
| Cohen's kappa | 0.72 |
| System quality | Pending harness and judge |
| Judge reliability/bias | Pending judge track |
| Measured API cost/latency | Pending result JSONL |

## Reproducibility

For the currently implemented scope:

```bash
python -m unittest discover -s tests -v
python -m py_compile cost_model.py
```

Full clean-clone reproduction remains blocked until the harness, dependency manifest, judge prompts, and timestamped result files are integrated.

## Contributions

- **Skander Bedoui:** checked-in golden dataset, labelling guide, agreement report, and dataset builder.
- **Khalil:** shared schemas and harness core (not yet present in this repository state).
- **Yasmine:** judge prompts and reliability/bias evaluation (not yet present in this repository state).
- **Abdallah Djarraya:** baseline system prompt and changelog, separate system/judge cost model and tests, cost/scalability analysis, README, provisional report assembly, and postmortem contribution.

All team members must review the final report and add their own evidence to the postmortem before submission.
