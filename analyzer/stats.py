"""All the spending math, done with pandas. The model never computes numbers."""

import pandas as pd

from analyzer.config import UNCATEGORIZED

# Moving money between your own accounts is neither spending nor income.
EXCLUDED = {"Transfers"}


def compute_stats(df: pd.DataFrame) -> dict:
    """Totals per category, per month and per merchant. Spending is reported as positive numbers."""
    data = df.copy()
    if "category" not in data:
        data["category"] = UNCATEGORIZED
    if "merchant" not in data:
        data["merchant"] = data["description"]
    data["month"] = data["date"].dt.to_period("M").astype(str)

    counted = data[~data["category"].isin(EXCLUDED)]
    spending = counted[counted["amount"] < 0].assign(spent=lambda d: -d["amount"])
    income = counted[counted["amount"] > 0]
    total_spent = round(float(spending["spent"].sum()), 2)
    total_income = round(float(income["amount"].sum()), 2)

    by_category = (
        spending.groupby("category", as_index=False)["spent"].sum()
        .rename(columns={"spent": "total"})
        .sort_values("total", ascending=False)
        .reset_index(drop=True)
    )
    by_category["total"] = by_category["total"].round(2)
    by_category["pct"] = (100 * by_category["total"] / total_spent).round(1) if total_spent else 0.0

    months = sorted(data["month"].unique())
    by_month = pd.DataFrame({"month": months})
    by_month["spent"] = by_month["month"].map(spending.groupby("month")["spent"].sum()).fillna(0).round(2)
    by_month["income"] = by_month["month"].map(income.groupby("month")["amount"].sum()).fillna(0).round(2)
    by_month["net"] = (by_month["income"] - by_month["spent"]).round(2)

    top_merchants = (
        spending.groupby("merchant", as_index=False)["spent"].sum()
        .rename(columns={"spent": "total"})
        .sort_values("total", ascending=False)
        .head(5)
        .reset_index(drop=True)
    )
    top_merchants["total"] = top_merchants["total"].round(2)

    return {
        "by_category": by_category,
        "by_month": by_month,
        "top_merchants": top_merchants,
        "total_spent": total_spent,
        "total_income": total_income,
        "months": len(months),
        "start": data["date"].min().date().isoformat(),
        "end": data["date"].max().date().isoformat(),
    }
