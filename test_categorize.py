import json
import pandas as pd
from analyzer.categorize import clean_merchant, categorize_transactions, parse_reply, CATEGORIES


def fake_chat(merchants):
    """Stand-in for the model: tags everything 'Groceries' except Netflix, skipping one merchant."""
    results = []
    for m in merchants:
        if m == "CAFE LUNA":
            continue  # simulate the model forgetting one
        results.append({"merchant": m, "category": "Subscriptions" if "NETFLIX" in m else "Groceries"})
    return json.dumps({"results": results})


def test_clean_merchant():
    assert clean_merchant("AMZN MKTP*2K4") == "AMZN MKTP"
    assert clean_merchant("FRESHMART #214") == "FRESHMART"


def test_invalid_category_becomes_other():
    reply = json.dumps({"results": [{"merchant": "X", "category": "Spaceships"}]})
    assert parse_reply(reply) == {"X": "Other"}


def test_bad_json_is_safe():
    assert parse_reply("not json") == {}


def test_categorize_transactions():
    df = pd.read_csv("sample_data/fake_transactions.csv")
    out = categorize_transactions(df, chat_fn=fake_chat)
    assert set(out["category"]).issubset(set(CATEGORIES))
    assert out.loc[out.merchant == "NETFLIX.COM", "category"].eq("Subscriptions").all()
    assert out.loc[out.merchant == "CAFE LUNA", "category"].eq("Other").all()
