"""One function that runs the whole analysis. Used by the Gradio app and the Agent Skill script."""

from dataclasses import dataclass, field

import pandas as pd
import requests

from analyzer import llm
from analyzer.categorize import categorize_transactions, clean_merchant
from analyzer.config import UNCATEGORIZED
from analyzer.load import load_csv
from analyzer.recurring import find_recurring
from analyzer.stats import compute_stats
from analyzer.summary import build_facts, fallback_summary, summarize

OTHER_WARNING_SHARE = 0.3


@dataclass
class Report:
    transactions: pd.DataFrame
    stats: dict
    recurring: pd.DataFrame
    facts: dict
    summary: str
    summary_source: str  # "model" or "fallback"
    ai_used: bool
    warnings: list[str] = field(default_factory=list)


def _without_model(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["merchant"] = out["description"].map(clean_merchant)
    out["category"] = UNCATEGORIZED
    return out


def analyze_file(path: str, use_llm: bool = True) -> Report:
    """CSV path -> Report. Raises load.InputError for unusable files; never fails because of the model."""
    df, warnings = load_csv(path)

    ai_used = use_llm and llm.is_available()
    if use_llm and not ai_used:
        warnings.append("AI model unavailable: showing numbers only, without categories.")

    if ai_used:
        try:
            df = categorize_transactions(df)
        except requests.RequestException:
            ai_used = False
            warnings.append("AI model stopped responding: showing numbers only, without categories.")
            df = _without_model(df)
    else:
        df = _without_model(df)

    if ai_used:
        merchants = df.drop_duplicates("merchant")
        other_share = (merchants["category"] == "Other").mean()
        if other_share > OTHER_WARNING_SHARE:
            warnings.append(f"{other_share:.0%} of merchants could not be categorized and are shown as Other.")

    stats = compute_stats(df)
    recurring = find_recurring(df)
    facts = build_facts(stats, recurring)
    if ai_used:
        summary, source = summarize(facts)
    else:
        summary, source = fallback_summary(facts), "fallback"

    return Report(df, stats, recurring, facts, summary, source, ai_used, warnings)
