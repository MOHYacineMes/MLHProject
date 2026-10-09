"""Show why the model matters: LLM categorization vs. a simple keyword baseline.

Run (Ollama must be running): python scripts/eval_categories.py
Labels in sample_data/fake_labels.csv were written by hand for fake merchant names.
"""

import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analyzer import llm  # noqa: E402
from analyzer.categorize import categorize_merchants, clean_merchant  # noqa: E402

# The kind of rules you'd write by hand from the sample statement.
KEYWORDS = {
    r"RENT": "Rent",
    r"NETFLIX|SPOTIFY|MEMBERSHIP": "Subscriptions",
    r"UBER|TRANSIT": "Transport",
    r"PAYROLL": "Income",
    r"PHARMACY": "Health",
    r"MART|GROCER": "Groceries",
    r"CAFE|RESTAURANT": "Dining",
    r"UTILITY|ELECTRIC": "Utilities",
    r"AMZN|AMAZON": "Shopping",
    r"TICKETS|CINEMA|CINEPLEX": "Entertainment",
    r"TRANSFER": "Transfers",
}


def keyword_category(merchant: str) -> str:
    for pattern, category in KEYWORDS.items():
        if re.search(pattern, merchant):
            return category
    return "Other"


def main() -> int:
    labels = pd.read_csv(Path(__file__).resolve().parents[1] / "sample_data" / "fake_labels.csv")
    labels["merchant"] = labels["description"].map(clean_merchant)
    labels["keyword"] = labels["merchant"].map(keyword_category)

    if not llm.is_available():
        print(f"Ollama or the model is not available. Keyword baseline only: "
              f"{(labels['keyword'] == labels['category']).mean():.0%}")
        return 1

    mapping = categorize_merchants(labels["merchant"].tolist())
    labels["llm"] = labels["merchant"].map(mapping)

    print(f"Merchants: {len(labels)}")
    print(f"Keyword baseline accuracy: {(labels['keyword'] == labels['category']).mean():.0%}")
    print(f"LLM ({llm.MODEL_NAME}) accuracy: {(labels['llm'] == labels['category']).mean():.0%}")
    wrong = labels[labels["llm"] != labels["category"]]
    if not wrong.empty:
        print("\nLLM mistakes:")
        print(wrong[["merchant", "category", "llm"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
