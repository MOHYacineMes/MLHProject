"""CLI for the Agent Skill: analyze a transactions CSV and print a JSON report.

Usage: python skills/bank-statement-analyzer/scripts/analyze_statement.py FILE.csv [--no-llm]
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from analyzer.config import DISCLAIMER  # noqa: E402
from analyzer.load import InputError  # noqa: E402
from analyzer.pipeline import analyze_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", help="CSV with columns date, description, amount")
    parser.add_argument("--no-llm", action="store_true", help="skip the local model")
    args = parser.parse_args()

    try:
        report = analyze_file(args.csv, use_llm=not args.no_llm)
    except (InputError, FileNotFoundError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 1

    stats = report.stats
    output = {
        "ai_used": report.ai_used,
        "summary": report.summary,
        "summary_source": report.summary_source,
        "period": {"start": stats["start"], "end": stats["end"], "months": stats["months"]},
        "total_spent": stats["total_spent"],
        "total_income": stats["total_income"],
        "by_category": stats["by_category"].to_dict(orient="records"),
        "by_month": stats["by_month"].to_dict(orient="records"),
        "top_merchants": stats["top_merchants"].to_dict(orient="records"),
        "recurring": report.recurring.to_dict(orient="records"),
        "warnings": report.warnings,
        "disclaimer": DISCLAIMER,
    }
    print(json.dumps(output, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
