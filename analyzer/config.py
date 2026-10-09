"""Settings, read from environment variables with local defaults."""

import os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5:3b")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "120"))
MAX_ROWS = int(os.getenv("MAX_ROWS", "5000"))

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

# Used when the model is offline, so the numbers still render.
UNCATEGORIZED = "Uncategorized"

DISCLAIMER = (
    "Informational only, not financial advice. "
    "This tool does not recommend investments or predict prices."
)
