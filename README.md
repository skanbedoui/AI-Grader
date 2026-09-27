# AI-Grader

AI-Grader evaluates the quality of code-review comments. A system LLM receives a Python or JavaScript snippet and returns one structured comment. A second LLM judge evaluates whether the comment is correct and useful. Exact string matching is not suitable because multiple phrasings can identify the same defect.

## Status at a glance

The repository currently contains the labelled dataset, prompts, provider client, runnable system-to-judge harness, timestamped development output, cost model, tests, report, and postmortem. The latest local development run is `results/dev_20260927T111715Z.jsonl` and contains 112 rows, one for each development item.

The assignment's final measurements are not complete yet: system quality summaries, judge-versus-human reliability, position-bias and verbosity-bias percentages, measured cost/latency analysis, and the single final test-set run still need to be produced and added to the report.

## Requirements

- Windows PowerShell
- Python 3.10 or newer
- Ollama, or an OpenAI API key
- The required Ollama model pulled locally when using Ollama

## Setup on Windows

Run these commands from the repository root (`AI-Grader`):

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, either select `.venv\Scripts\python.exe` as the VS Code interpreter or run this once for the current user:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Create `.env` from `.env.example`, then set the provider. `.env` is ignored by Git and must never be committed:

```powershell
Copy-Item .env.example .env
```

For Ollama, use settings like these in `.env`:

```dotenv
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
```

Ollama must be running before the harness starts. On Windows, Ollama may already be running in the background. Check it before starting another server:

```powershell
ollama list
Get-NetTCPConnection -LocalPort 11434 -ErrorAction SilentlyContinue
```

If the model is not installed, pull it once:

```powershell
ollama pull llama3.1
```

If port `11434` is listening, do not run `ollama serve` again. If it is not listening, start Ollama in a separate terminal:

```powershell
ollama serve
```

For OpenAI instead, set `LLM_PROVIDER=openai`, provide `OPENAI_API_KEY`, and set `OPENAI_MODEL` in `.env`.

## Test the project

Run the unit tests from the activated environment:

```powershell
python -m unittest discover -s tests -v
```

Run syntax checks:

```powershell
python -m py_compile config.py cost_model.py model_client.py harness\run.py data\build_dataset.py
```

The cost-model tests do not call an LLM. The harness run does call the configured provider and may take several minutes for the full development split.

## Run the evaluation

First verify the dataset without overwriting it. The dataset builder is deterministic but writes `data/golden_set.jsonl`, so run it only when intentionally rebuilding the dataset:

```powershell
python data\build_dataset.py
```

Run the development split while prompts are being developed:

```powershell
python harness\run.py --split dev
```

The runner loads `prompts\system_prompt_v1.md` and `prompts\judge_prompt_v1.md`, calls the system and judge once per item, and writes a new timestamped JSONL file under `results\`. It preserves the input, model/provider, structured outputs, token usage, latency, human labels, and status for each item.

Inspect the newest run in PowerShell:

```powershell
$latest = Get-ChildItem results\dev_*.jsonl |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
$rows = Get-Content $latest.FullName |
    Where-Object { $_.Trim() } |
    ForEach-Object { $_ | ConvertFrom-Json }
Write-Host "File:" $latest.FullName
Write-Host "Rows:" $rows.Count
Write-Host "Statuses:" (($rows.status | Sort-Object -Unique) -join ", ")
```

Do not run the test split during prompt iteration. After the final prompt is frozen and the team has reviewed the development evidence, run it exactly once:

```powershell
python harness\run.py --split test
```

Do not edit result JSONL files by hand. Keep every timestamped run so the reported result is reproducible and auditable.

## Cost calculation

The cost model requires separate system and judge token prices. Use a result file whose rows have successful usage data:

```powershell
python cost_model.py results\<run_id>.jsonl `
  --system-input-price <usd-per-million> `
  --system-output-price <usd-per-million> `
  --judge-input-price <usd-per-million> `
  --judge-output-price <usd-per-million> `
  --daily-volume <items>
```

It reports measured token totals, system cost, judge cost, total cost, mean cost per item, cost per 1,000 items, daily cost, and a 100x volume projection. Prices are inputs, not claims about provider pricing. Batching and prompt caching can reduce effective cost, retries add cost, and rate limits can restrict throughput.

## Architecture

```text
code snippet -> system LLM -> {"comment": "..."}
             -> LLM judge  -> verdict/correct/useful/reason JSON
             -> harness    -> one JSONL row per dataset item
             -> analysis   -> quality, reliability, latency, and cost summaries
```

The dataset has 160 items: 110 Python and 50 JavaScript, with 112 development items and 48 reserved test items. Each row has two human labels. The checked-in agreement report records 86.25% agreement and Cohen's kappa of 0.72.

## Assignment checklist

### Done in this repository

- [x] 160-item golden dataset with Python and JavaScript snippets.
- [x] Double labels, locked 112/48 development/test split, labelling guide, and human agreement report.
- [x] Baseline system prompt and judge prompt with structured JSON expectations.
- [x] Ollama and OpenAI provider client with token usage capture.
- [x] End-to-end `harness\run.py` that writes one result row per item, including latency and status.
- [x] Cost model with separate system/judge prices and unit/scale projections.
- [x] Cost-model unit tests.
- [x] Provisional report and evidence-based postmortem scaffolding.
- [x] Timestamped development result file with 112 rows.

### Still required by the assignment

- [ ] Run a clean-clone setup and confirm the harness runs with no manual fixes.
- [ ] Produce development quality metrics: good rate, correctness, usefulness, per-language results, and failure categories.
- [ ] Report judge-versus-human agreement separately for dev and test using both percentage agreement and Cohen's kappa.
- [ ] Implement and report the position-bias swap test and verbosity-bias padding test, including at least two concrete failure examples.
- [ ] Add every prompt version's before/after development score to `prompts\CHANGELOG.md`; the current v1 entry still contains pending fields and no v2 is justified until failures are analysed.
- [ ] Calculate measured cost and latency from successful result rows and add the evidence to the report.
- [ ] Freeze the final prompt, run `harness\run.py --split test` exactly once, and preserve the timestamped output.
- [ ] Replace all pending fields in `report.pdf`/`report.html`, have all teammates review the report, and add their evidence to `postmortem.md`.
- [ ] Verify Git history contains no API keys and document reviewed pull requests, protected main, and the final clean-clone check.

## Repository structure

```text
data/                    Golden set, labelling guide, agreement report, builder
prompts/                 Versioned system and judge prompts, plus changelog
harness/                 End-to-end runner
results/                 Timestamped generated JSONL runs
tests/test_cost_model.py Cost-model tests
cost_model.py            Measured cost aggregation and scale projections
model_client.py          Ollama/OpenAI provider client
report.html              Editable provisional report source
report.pdf               Provisional report
postmortem.md            Project retrospective
```

## Contributions

- **Skander Bedoui:** golden dataset, labelling guide, agreement report, and dataset builder.
- **Khalil:** provider integration and end-to-end harness runner.
- **Yasmine:** judge prompt and the remaining judge-reliability and bias-analysis track.
- **Abdallah Djarraya:** baseline system prompt and changelog, cost model and tests, cost/scalability analysis, README, provisional report assembly, and postmortem contribution.

The contributions list and final metrics must be checked against the merged Git history before submission.
