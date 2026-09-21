# AI-Grader

AI-Grader evaluates the quality of AI-generated code review comments. Given a code snippet, the system produces one structured review comment; a separate judge grades whether that comment is correct and useful.

## Repository status

The golden dataset and the v1 system prompt are present. Harness-core and judge/reliability integration are still in progress, so the end-to-end command and measured headline result are not available on `main` yet. This README deliberately does not claim unmeasured results.

## Setup

Clone the repository and enter it:

```bash
git clone git@github.com:skanbedoui/AI-Grader.git
cd AI-Grader
```

The dataset builder and cost model use only the Python standard library. The harness dependency installation command will be added when the harness track lands its dependency manifest.

## Run

Validate or rebuild the checked-in dataset:

```bash
python data/build_dataset.py
```

Run the cost model against a harness result file containing logged input and output token counts:

```bash
python cost_model.py results/<run_id>.jsonl \
  --input-price <usd-per-million-input-tokens> \
  --output-price <usd-per-million-output-tokens>
```

The calculator reports observed cost, average cost per item, cost per 1,000 items, and the requested 100x projection. Prices are explicit CLI inputs because model pricing can change. At production scale, unit cost may not be linear because batching and prompt caching can reduce it while rate limits can constrain throughput.

The end-to-end harness command documented in the project plan is:

```bash
python harness/run.py --split test
```

It will become runnable after the harness-core and judge tracks merge. During prompt iteration, use only `--split dev`; run `--split test` once after the final prompt is frozen.

## Results

The dataset contains 160 Python and JavaScript examples: 112 development rows and 48 reserved test rows. Every example is double-labelled. Human labelers achieved 86.25% agreement and Cohen's kappa of 0.72.

System and judge scores are not reported yet because no timestamped harness result has been committed. Final results must link to a complete JSONL run in `results/` rather than being copied from an ad hoc evaluation.

## Prompt iteration

System prompts live in `prompts/system_prompt_v*.md`. Every new prompt version must have a matching entry in `prompts/CHANGELOG.md` with measured before/after development scores. Test examples must not be inspected or used to tune prompts.

## Contributions

- Skander Bedoui: golden dataset, labelling guide, agreement report, and dataset builder.
- Khalil: shared schemas and harness core (in progress).
- Yasmine: judge prompts and reliability/bias evaluation (in progress).
- Abdallah Djarraya: system-prompt iteration, prompt changelog, cost model, reproducibility documentation, and final report assembly.

All team members review the final report and contribute to the postmortem.
