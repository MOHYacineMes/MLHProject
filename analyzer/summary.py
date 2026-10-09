"""Second LLM job: turn pre-computed numbers into a short plain-language summary.

pandas computes every number in `build_facts`. The model only writes sentences, and a
guard rejects the reply if it contains a number that isn't in the facts.
"""

import json
import re

import pandas as pd
import requests

from analyzer import llm

SYSTEM_PROMPT = """You explain a person's spending to them in plain, friendly language.

You get a JSON object of facts that were already calculated. Write 3 to 4 short sentences.
Rules:
- Use ONLY numbers that appear in the facts. Do not add, subtract, average or estimate anything.
- Write money as dollars, for example $1,450.00.
- Do not give investment advice, do not mention stocks or crypto, and do not predict the future.
- No greetings, no lists, no headings. Plain sentences only."""

# Words that mean the model drifted into advice or prediction.
BANNED = re.compile(r"\b(invest\w*|stocks?|crypto\w*|bitcoin|portfolio|predict\w*|forecast\w*)\b", re.I)
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
RELATIVE_TOLERANCE = 0.02  # "about $4,400" for 4,350 is rounding, not invention


def build_facts(stats: dict, recurring: pd.DataFrame) -> dict:
    """The only data the model sees: a small dict of already-computed numbers."""
    by_category = stats["by_category"]
    by_month = stats["by_month"]
    facts = {
        "period": f"{stats['start']} to {stats['end']}",
        "months": stats["months"],
        "total_spent": stats["total_spent"],
        "total_income": stats["total_income"],
        "net": round(stats["total_income"] - stats["total_spent"], 2),
        "average_monthly_spent": round(stats["total_spent"] / max(stats["months"], 1), 2),
        "top_categories": [
            {"category": r.category, "amount": r.total, "percent_of_spending": r.pct}
            for r in by_category.head(3).itertuples()
        ],
        "recurring_charges_count": len(recurring),
        "recurring_monthly_total": round(float(recurring["est_monthly_cost"].sum()), 2) if len(recurring) else 0.0,
        "largest_recurring": [
            {"merchant": r.merchant, "monthly_cost": r.est_monthly_cost}
            for r in recurring.head(3).itertuples()
        ],
    }
    if not by_month.empty and by_month["spent"].max() > 0:
        top = by_month.loc[by_month["spent"].idxmax()]
        facts["highest_spending_month"] = {"month": top["month"], "amount": float(top["spent"])}
    return facts


def _allowed_numbers(value) -> list[float]:
    """Every number in the facts, including digits inside strings like dates."""
    if isinstance(value, dict):
        return [n for v in value.values() for n in _allowed_numbers(v)]
    if isinstance(value, list):
        return [n for v in value for n in _allowed_numbers(v)]
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    return [float(m.replace(",", "")) for m in NUMBER.findall(str(value))]


def check_reply(text: str, facts: dict) -> bool:
    """True if the reply is non-empty, advice-free, and every number in it comes from the facts."""
    if not text.strip() or BANNED.search(text):
        return False
    allowed = _allowed_numbers(facts) + [float(n) for n in range(0, 13)]  # small counts like "3 months"
    for raw in NUMBER.findall(text):
        number = float(raw.replace(",", ""))
        if not any(abs(number - a) <= max(RELATIVE_TOLERANCE * abs(a), 0.01) for a in allowed):
            return False
    return True


def fallback_summary(facts: dict) -> str:
    """Template summary used when the model is offline or its reply fails the guard."""
    parts = [
        f"From {facts['period']} you spent ${facts['total_spent']:,.2f} "
        f"and received ${facts['total_income']:,.2f}."
    ]
    if facts["top_categories"]:
        top = facts["top_categories"][0]
        parts.append(
            f"Your biggest category was {top['category']} at ${top['amount']:,.2f} "
            f"({top['percent_of_spending']}% of spending)."
        )
    if facts["recurring_charges_count"]:
        parts.append(
            f"{facts['recurring_charges_count']} recurring charges cost about "
            f"${facts['recurring_monthly_total']:,.2f} per month."
        )
    return " ".join(parts)


def summarize(facts: dict, chat_fn=None) -> tuple[str, str]:
    """Return (summary text, source) where source is "model" or "fallback"."""
    chat_fn = chat_fn or llm.chat
    try:
        reply = chat_fn(SYSTEM_PROMPT, json.dumps(facts), temperature=0.3, max_tokens=220)
    except (requests.RequestException, KeyError, ValueError):
        return fallback_summary(facts), "fallback"
    reply = reply.strip()
    if check_reply(reply, facts):
        return reply, "model"
    return fallback_summary(facts), "fallback"
