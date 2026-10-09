import requests

from analyzer.summary import check_reply, summarize

FACTS = {
    "period": "2026-07-01 to 2026-09-30",
    "months": 3,
    "total_spent": 6201.5,
    "total_income": 12900.0,
    "top_categories": [{"category": "Rent", "amount": 4350.0, "percent_of_spending": 70.1}],
    "recurring_charges_count": 4,
    "recurring_monthly_total": 1508.47,
}


def chat_returning(text):
    return lambda *args, **kwargs: text


def test_model_summary_with_real_numbers_is_kept():
    text = "Over 3 months you spent $6,201.50. Rent was $4,350.00, about 70% of spending."
    assert summarize(FACTS, chat_fn=chat_returning(text)) == (text, "model")


def test_invented_number_falls_back():
    text = "You spent $9,999.00 on rent."
    summary, source = summarize(FACTS, chat_fn=chat_returning(text))
    assert source == "fallback"
    assert "$6,201.50" in summary


def test_advice_falls_back():
    assert not check_reply("You spent $6,201.50. Consider investing in stocks.", FACTS)


def test_model_offline_falls_back():
    def offline(*args, **kwargs):
        raise requests.ConnectionError("down")

    assert summarize(FACTS, chat_fn=offline)[1] == "fallback"


def test_empty_reply_falls_back():
    assert summarize(FACTS, chat_fn=chat_returning("  "))[1] == "fallback"
