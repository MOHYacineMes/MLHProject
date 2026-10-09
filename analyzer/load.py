"""Read an uploaded CSV into a clean DataFrame, with messages a person can act on."""

import pandas as pd

from analyzer.config import MAX_ROWS

REQUIRED_COLUMNS = ["date", "description", "amount"]


class InputError(ValueError):
    """The file can't be analyzed. The message is shown to the user as-is."""


def _read(path: str) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(path, dtype=str, skipinitialspace=True, encoding=encoding)
        except UnicodeDecodeError:
            continue
        except pd.errors.EmptyDataError:
            raise InputError("The file is empty.")
        except pd.errors.ParserError:
            raise InputError("This doesn't look like a valid CSV file.")
    raise InputError("Could not read the file's text encoding. Save it as UTF-8 CSV.")


def _parse_amount(raw: pd.Series) -> pd.Series:
    """'$1,234.50' -> 1234.5 and accounting style '(12.00)' -> -12.0."""
    text = raw.fillna("").astype(str).str.strip()
    negative = text.str.startswith("(") & text.str.endswith(")")
    cleaned = text.str.replace(r"[$,()\s]", "", regex=True)
    numbers = pd.to_numeric(cleaned, errors="coerce")
    return numbers.where(~negative, -numbers.abs())


def load_csv(path: str, max_rows: int = MAX_ROWS) -> tuple[pd.DataFrame, list[str]]:
    """Return (transactions, warnings). Raises InputError when nothing usable is left.

    Output columns: date (datetime64), description (str), amount (float, negative = spending).
    """
    df = _read(path)
    df.columns = [str(c).strip().lower() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise InputError(
            f"Missing columns: {', '.join(missing)}. "
            f"Expected: {', '.join(REQUIRED_COLUMNS)}."
        )
    if len(df) > max_rows:
        raise InputError(f"Too many rows ({len(df)}). The limit is {max_rows}.")

    out = pd.DataFrame(
        {
            "date": pd.to_datetime(df["date"], errors="coerce"),
            "description": df["description"].fillna("").astype(str).str.strip(),
            "amount": _parse_amount(df["amount"]).round(2),
        }
    )
    valid = out["date"].notna() & out["amount"].notna() & (out["description"] != "")
    warnings = []
    skipped = int((~valid).sum())
    if skipped:
        warnings.append(f"{skipped} row(s) skipped because the date, description or amount was unreadable.")

    out = out[valid].sort_values("date").reset_index(drop=True)
    if out.empty:
        raise InputError("No valid transactions found.")
    return out, warnings
