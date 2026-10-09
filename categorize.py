"""Merchant categorization with a local open-weight model served by Ollama.

The model does ONE job: turn messy merchant strings ("AMZN MKTP*2K4") into a
category from a fixed list. All math (totals, recurring charges) is done
elsewhere with pandas, so the numbers never depend on the model.
"""

import json
import os
import re

import pandas as pd
import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5:3b")
BATCH_SIZE = 15

CATEGORIES = [
    "Groceries",
    "Dining",
    "Transport",
    "Rent",
    "Utilities",
    "Subscriptions",
    "Shopping",
    "Health",
    "Entertainment",
    "Income",
    "Transfers",
    "Other",
]

SYSTEM_PROMPT = f"""You categorize bank transaction merchants.

Allowed categories: {", ".join(CATEGORIES)}.

Rules:
- Pick exactly one allowed category per merchant. Never invent a category.
- Streaming, music, cloud storage, software and gym memberships are "Subscriptions".
- Salary, payroll and deposits from an employer are "Income".
- Moves between the person's own accounts, e-transfers and credit card payments are "Transfers".
- If you are unsure, use "Other".

Reply with JSON only, in this exact shape:
{{"results": [{{"merchant": "<merchant exactly as given>", "category": "<allowed category>"}}]}}
Return one entry for every merchant you were given."""


def clean_merchant(description: str) -> str:
    """Normalize a raw bank description so identical merchants share one key.

    Drops tokens that contain digits (store numbers, reference codes) and
    punctuation noise. "AMZN MKTP*2K4" -> "AMZN MKTP".
    """
    text = str(description).upper()
    tokens = re.split(r"[\s*#]+", text)
    kept = [t for t in tokens if t and not any(c.isdigit() for c in t)]
    return " ".join(kept) or text.strip()


def ollama_chat(merchants: list[str]) -> str:
    """Send one batch of merchants to the local model and return its raw reply."""
    response = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": MODEL_NAME,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(merchants)},
            ],
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def parse_reply(reply: str) -> dict[str, str]:
    """Turn the model's JSON reply into {merchant: category}, validating categories."""
    try:
        data = json.loads(reply)
    except json.JSONDecodeError:
        return {}
    items = data.get("results", []) if isinstance(data, dict) else []
    parsed = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        merchant = str(item.get("merchant", "")).strip().upper()
        category = str(item.get("category", "")).strip()
        if merchant:
            parsed[merchant] = category if category in CATEGORIES else "Other"
    return parsed


def categorize_merchants(merchants: list[str], chat_fn=ollama_chat) -> dict[str, str]:
    """Categorize unique merchants in batches. Missing answers get one retry, then 'Other'.

    `chat_fn` is injectable so tests can run without a model.
    """
    unique = sorted(set(merchants))
    result: dict[str, str] = {}
    for start in range(0, len(unique), BATCH_SIZE):
        batch = unique[start : start + BATCH_SIZE]
        pending = batch
        for _attempt in range(2):
            parsed = parse_reply(chat_fn(pending))
            for merchant in pending:
                if merchant in parsed:
                    result[merchant] = parsed[merchant]
            pending = [m for m in pending if m not in result]
            if not pending:
                break
        for merchant in pending:
            result[merchant] = "Other"
    return result


def categorize_transactions(df: pd.DataFrame, chat_fn=ollama_chat) -> pd.DataFrame:
    """Add `merchant` and `category` columns to a transactions DataFrame.

    Expected columns: date, description, amount (negative = money out).
    """
    out = df.copy()
    out["merchant"] = out["description"].map(clean_merchant)
    mapping = categorize_merchants(out["merchant"].tolist(), chat_fn=chat_fn)
    out["category"] = out["merchant"].map(mapping).fillna("Other")
    return out
