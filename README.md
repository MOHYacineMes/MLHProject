# Statement Analyzer

**A private, local-first bank statement analyzer: the first module of a future personal finance app.**

Upload a CSV of transactions and get spending by category, monthly totals, recurring charges
and a short plain-language summary. An open-weight LLM running on your own machine does the
language work; pandas does all the math.

> ⚠️ Informational only, not financial advice. This tool does not recommend investments or predict prices.

<!-- TODO: screenshot or GIF of the app -->

## What it does
- **Categorizes merchants** like `AMZN MKTP*2K4` or `SQ *BLUE BOTTLE` into 12 fixed categories.
- **Computes totals** per category and per month (income, spending, net).
- **Finds recurring charges** (rent, subscriptions, bills) and their monthly cost.
- **Writes a 3–4 sentence summary** of your spending in plain language.

## How AI is used
The model ([Qwen2.5-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct), served by [Ollama](https://ollama.com)) has two jobs. It never computes numbers.

| Job | Model sees | Model returns | Safety net |
|---|---|---|---|
| Categorize | Unique cleaned merchant names (no amounts, no dates) | JSON `{merchant: category}` | Categories validated against a fixed list; missing ones retried once, then `Other` |
| Summarize | A small JSON of numbers pandas already computed | 3–4 sentences | Every number in the reply must exist in the facts, and advice words are rejected; otherwise a template summary is used |

**Why the model matters:** `python scripts/eval_categories.py` compares the LLM against a hand-written
keyword baseline on 32 hand-labeled fake merchants:

| Method | Accuracy |
|---|---|
| Keyword rules | 50% |
| Qwen2.5-3B (local) | TODO: run the script and paste the result |

Without the model, every chart collapses into a single `Uncategorized` bar. Try it by stopping Ollama.

## Model and license
- **Model:** `qwen2.5:3b` (Qwen2.5-3B-Instruct, 4-bit, about 1.9 GB) via Ollama.
- **License:** Qwen2.5-3B is released under the **Qwen Research License** (open weights, non-commercial use).
  Fully Apache-2.0 alternatives work by changing one variable: `MODEL_NAME=qwen2.5:1.5b` or `qwen2.5:7b`.
- **This project's code:** MIT (see `LICENSE`).

## Quickstart
```bash
# 1. Install Ollama from https://ollama.com, then:
ollama pull qwen2.5:3b

# 2. Install and run the app
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py                      # open http://127.0.0.1:7860, then click "Try sample data"

# 3. Tests (no model needed)
pytest
```

| Variable | Default | Meaning |
|---|---|---|
| `OLLAMA_URL` | `http://localhost:11434` | Where Ollama runs |
| `MODEL_NAME` | `qwen2.5:3b` | Which model to use |
| `HOST` / `PORT` | `127.0.0.1` / `7860` | Where the app listens |
| `LLM_TIMEOUT` | `120` | Seconds to wait for the model |
| `MAX_ROWS` | `5000` | Largest CSV accepted |

CSV format: columns `date, description, amount`, with negative amounts for spending. See `sample_data/fake_transactions.csv`.

## Privacy
- **Runs on your machine.** The model runs locally through Ollama. No cloud AI API, no bank connection, no account.
- **Nothing is stored.** No database. The uploaded file is deleted right after it is read, and analysis happens in memory.
- **Minimal model input.** The model sees only merchant names and aggregate totals, never your full statement.
- **Fake data only in this repo.**
- **The public demo is a demo.** It runs the same stack on a DigitalOcean Droplet, so data you upload there
  leaves your computer. Use it only with fake data. For real statements, run it locally.

## Deployment (DigitalOcean)
One Droplet runs both Ollama and the app: Ubuntu 24.04, **8 GB RAM / 4 vCPU**. The 3B model needs
about 3 GB of RAM, plus room for the OS and Python. CPU-only inference makes a full analysis take
about 20–45 seconds.

```bash
ssh root@<droplet-ip>
curl -fsSLO https://raw.githubusercontent.com/MOHYacineMes/MLHProject/main/deploy/setup_droplet.sh
bash setup_droplet.sh
```
The script installs Ollama, pulls the model, keeps it loaded (`OLLAMA_KEEP_ALIVE=24h`), installs the
app as a `systemd` service that restarts on failure, and opens only ports 22 and 7860.
Port 11434 (Ollama) is never exposed.

## Agent Skill
`skills/bank-statement-analyzer/` follows the [Agent Skills](https://agentskills.io) format:
a `SKILL.md` with `name` and `description` frontmatter plus a helper script that prints a JSON report:
```bash
python skills/bank-statement-analyzer/scripts/analyze_statement.py sample_data/fake_transactions.csv
```

## Project structure
```
analyzer/      config, llm client, load, categorize, stats, recurring, summary, pipeline
app.py         Gradio UI
scripts/       eval_categories.py (LLM vs keyword baseline)
skills/        Agent Skill
deploy/        Droplet setup script and systemd unit
tests/         pytest suite (runs without a model)
sample_data/   fake transactions and hand-labeled merchants
```

## Limitations
- A 3B model makes mistakes, especially with unusual or very short merchant names.
- Only simple CSVs with `date, description, amount` columns; no PDF or bank-specific formats yet.
- Recurring detection misses charges whose price changed by more than 10%, and irregular schedules.
- CPU inference is slow on large statements.
- Not financial advice.

## Future modules
- Budgets and overspending alerts
- Merging several accounts and bank-specific CSV formats
- Letting users correct categories, and remembering corrections
- Savings goals tracking

## License
MIT
