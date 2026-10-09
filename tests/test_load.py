import pytest

from analyzer.load import InputError, load_csv


def write(tmp_path, text):
    path = tmp_path / "t.csv"
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_loads_sample():
    df, warnings = load_csv("sample_data/fake_transactions.csv")
    assert len(df) == 41
    assert warnings == []
    assert str(df["date"].dtype).startswith("datetime64")


def test_empty_file(tmp_path):
    with pytest.raises(InputError, match="empty"):
        load_csv(write(tmp_path, ""))


def test_header_only(tmp_path):
    with pytest.raises(InputError, match="No valid"):
        load_csv(write(tmp_path, "date,description,amount\n"))


def test_wrong_columns(tmp_path):
    with pytest.raises(InputError, match="Missing columns: amount"):
        load_csv(write(tmp_path, "Date,Description,Value\n2026-01-01,X,-1\n"))


def test_messy_amounts_and_bad_rows(tmp_path):
    text = (
        " Date , DESCRIPTION ,Amount\n"
        '2026-01-01,SHOP,"$1,234.50"\n'
        "2026-01-02,SHOP,(12.00)\n"
        "not a date,SHOP,-5\n"
        "2026-01-03,SHOP,abc\n"
    )
    df, warnings = load_csv(write(tmp_path, text))
    assert df["amount"].tolist() == [1234.5, -12.0]
    assert "2 row(s) skipped" in warnings[0]


def test_row_limit(tmp_path):
    with pytest.raises(InputError, match="Too many rows"):
        load_csv(write(tmp_path, "date,description,amount\n" + "2026-01-01,X,-1\n" * 3), max_rows=2)
