---
name: bank-statement-analyzer
description: Analyze a bank transaction CSV (columns date, description, amount) privately on the user's machine. Categorizes merchants with a local open-weight model through Ollama, computes spending per category and per month with pandas, and finds recurring charges. Use when the user wants to understand their spending, find subscriptions, or summarize a CSV bank statement. Informational only; never gives investment advice.
---

# Bank Statement Analyzer

## When to use
The user has a CSV export of bank transactions and wants a spending breakdown, a list of
recurring charges or subscriptions, or a plain-language summary.

## Prerequisites
- This skill lives inside the project repository and imports its `analyzer` package.
  Run commands from the repository root after `pip install -r requirements.txt`.
- Ollama running locally (`OLLAMA_URL`, default `http://localhost:11434`) with the model
  pulled (`MODEL_NAME`, default `qwen2.5:3b`). Without it the script still returns all
  numbers, with every category set to `Uncategorized`.

## Steps
1. Check the CSV has the columns `date`, `description`, `amount` (negative = spending).
   If it does not, tell the user which columns are missing and stop.
2. Run:
   ```
   python skills/bank-statement-analyzer/scripts/analyze_statement.py <path/to/file.csv>
   ```
   Add `--no-llm` to skip the model entirely.
3. Read the JSON printed to stdout. On failure the script prints `{"error": ...}` to
   stderr and exits with code 1: relay the message and explain how to fix the file.
4. Present the results (format below).

## Rules
- Every number you show must come from the script's JSON. Never add, average or estimate numbers yourself.
- Do not recommend investments, financial products, or predict prices or future spending.
- Always end with: "Informational only, not financial advice."
- Remind the user their data was processed locally and nothing was stored.
- If `ai_used` is false, say categories were unavailable because the local model was offline.

## Output format
1. The `summary` field, as-is.
2. Top categories: a short table of `by_category` (category, total, pct).
3. Recurring charges: a table of `recurring` (merchant, frequency, est_monthly_cost).
4. Any `warnings`.
5. The disclaimer.
