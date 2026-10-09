import json

from analyzer import llm
from analyzer.pipeline import analyze_file

SAMPLE = "sample_data/fake_transactions.csv"


def fake_chat(system, user, json_mode=False, **kwargs):
    if json_mode:  # categorization call
        merchants = json.loads(user)
        return json.dumps({"results": [
            {"merchant": m, "category": "Rent" if "RENT" in m else "Shopping"} for m in merchants
        ]})
    return "Over 3 months you spent money on Rent and Shopping."  # summary call


def test_model_offline_still_shows_numbers(monkeypatch):
    monkeypatch.setattr(llm, "is_available", lambda: False)
    report = analyze_file(SAMPLE)
    assert not report.ai_used
    assert set(report.transactions["category"]) == {"Uncategorized"}
    assert report.stats["total_income"] == 12900.0
    assert report.summary_source == "fallback"
    assert any("unavailable" in w for w in report.warnings)


def test_full_run_with_fake_model(monkeypatch):
    monkeypatch.setattr(llm, "is_available", lambda: True)
    monkeypatch.setattr(llm, "chat", fake_chat)
    report = analyze_file(SAMPLE)
    assert report.ai_used
    assert report.summary_source == "model"
    assert report.stats["by_category"].iloc[0]["category"] == "Rent"
    assert not report.recurring.empty
