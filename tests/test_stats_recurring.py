import pandas as pd

from analyzer.categorize import clean_merchant
from analyzer.load import load_csv
from analyzer.recurring import find_recurring
from analyzer.stats import compute_stats


def sample():
    df, _ = load_csv("sample_data/fake_transactions.csv")
    df["merchant"] = df["description"].map(clean_merchant)
    df["category"] = "Other"
    df.loc[df["merchant"].str.contains("PAYROLL"), "category"] = "Income"
    return df


def test_totals():
    stats = compute_stats(sample())
    assert stats["total_income"] == 12900.0
    assert stats["months"] == 3
    assert stats["by_month"]["month"].tolist() == ["2026-07", "2026-08", "2026-09"]
    assert round(stats["by_category"]["pct"].sum()) == 100


def test_transfers_are_not_spending():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2026-01-01", "2026-01-02"]),
        "description": ["SAVINGS", "SHOP"],
        "merchant": ["SAVINGS", "SHOP"],
        "category": ["Transfers", "Shopping"],
        "amount": [-500.0, -20.0],
    })
    assert compute_stats(df)["total_spent"] == 20.0


def test_recurring_detects_monthly_and_skips_one_offs():
    recurring = find_recurring(sample())
    merchants = set(recurring["merchant"])
    assert {"APARTMENT RENT PMT", "NETFLIX.COM", "SPOTIFY"} <= merchants
    assert "CINEPLEX TICKETS" not in merchants  # only once
    assert "FRESHMART" not in merchants  # irregular amounts and dates
    rent = recurring.set_index("merchant").loc["APARTMENT RENT PMT"]
    assert rent["frequency"] == "monthly" and rent["est_monthly_cost"] == 1450.0


def test_recurring_empty_input():
    empty = pd.DataFrame(columns=["date", "description", "amount", "merchant"])
    assert find_recurring(empty).empty
