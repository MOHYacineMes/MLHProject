"""Find recurring charges (subscriptions, rent, bills) with plain pandas rules."""

import pandas as pd

from analyzer.config import UNCATEGORIZED

COLUMNS = [
    "merchant", "category", "typical_amount", "frequency",
    "occurrences", "last_date", "est_monthly_cost",
]

# frequency name -> (min gap days, max gap days, charges per month)
FREQUENCIES = {
    "weekly": (6, 8, 52 / 12),
    "every 2 weeks": (13, 16, 26 / 12),
    "monthly": (25, 35, 1.0),
}


def _frequency(dates: pd.Series) -> str | None:
    gaps = dates.sort_values().diff().dt.days.dropna()
    if gaps.empty:
        return None
    for name, (low, high, _) in FREQUENCIES.items():
        if gaps.between(low, high).all():
            return name
    return None


def find_recurring(
    df: pd.DataFrame, amount_tolerance: float = 0.10, min_occurrences: int = 2
) -> pd.DataFrame:
    """A merchant is recurring when its charges are similar in size and evenly spaced.

    Needs `merchant` and `date`; uses `category` if present. Price changes beyond
    `amount_tolerance` (e.g. a subscription getting more expensive) are not detected.
    """
    if df.empty or "merchant" not in df:
        return pd.DataFrame(columns=COLUMNS)

    spending = df[df["amount"] < 0]
    rows = []
    for merchant, group in spending.groupby("merchant"):
        group = group.drop_duplicates(subset="date")
        if len(group) < min_occurrences:
            continue
        amounts = -group["amount"]
        median = amounts.median()
        if not ((amounts - median).abs() <= amount_tolerance * median).all():
            continue
        frequency = _frequency(group["date"])
        if frequency is None:
            continue
        per_month = FREQUENCIES[frequency][2]
        rows.append(
            {
                "merchant": merchant,
                "category": group["category"].iloc[-1] if "category" in group else UNCATEGORIZED,
                "typical_amount": round(float(median), 2),
                "frequency": frequency,
                "occurrences": len(group),
                "last_date": group["date"].max().date().isoformat(),
                "est_monthly_cost": round(float(median) * per_month, 2),
            }
        )

    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    return pd.DataFrame(rows, columns=COLUMNS).sort_values("est_monthly_cost", ascending=False).reset_index(drop=True)
