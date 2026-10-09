"""Gradio UI: upload a CSV, see categories, monthly totals, recurring charges and a summary.

Run: python app.py   (HOST=0.0.0.0 to expose it on a server)
"""

import os
from pathlib import Path

import gradio as gr
import pandas as pd

from analyzer.config import DISCLAIMER, MODEL_NAME
from analyzer.load import InputError
from analyzer.pipeline import analyze_file

SAMPLE_PATH = str(Path(__file__).parent / "sample_data" / "fake_transactions.csv")
EMPTY = pd.DataFrame()

BANNER = f"""# Statement Analyzer
Upload a CSV with columns **date, description, amount** (negative = spending).
Merchants are categorized by **{MODEL_NAME}** running locally through Ollama; all numbers are computed with pandas.

> ⚠️ {DISCLAIMER} Files are processed in memory and deleted right after reading.
> **On the public demo, upload only fake data.**"""


def _render(path: str):
    try:
        report = analyze_file(path)
    except InputError as error:
        return f"❌ {error}", "", EMPTY, EMPTY, EMPTY, EMPTY

    status = "✅ Analysis complete" + (" (AI categories + AI summary)" if report.ai_used else "")
    if report.warnings:
        status += "\n\n" + "\n".join(f"- ⚠️ {w}" for w in report.warnings)

    label = "Summary written by the local model" if report.summary_source == "model" else "Summary (template)"
    summary_md = f"### {label}\n{report.summary}\n\n*{DISCLAIMER}*"

    transactions = report.transactions.assign(date=report.transactions["date"].dt.date.astype(str))
    return (
        status,
        summary_md,
        report.stats["by_category"],
        report.stats["by_month"],
        report.recurring,
        transactions[["date", "description", "merchant", "category", "amount"]],
    )


def analyze_upload(file_path: str | None):
    if not file_path:
        return "Please upload a CSV file.", "", EMPTY, EMPTY, EMPTY, EMPTY
    try:
        return _render(file_path)
    finally:
        # Don't keep the user's statement on disk.
        try:
            os.remove(file_path)
        except OSError:
            pass


def analyze_sample():
    return _render(SAMPLE_PATH)


with gr.Blocks(title="Statement Analyzer", delete_cache=(300, 300)) as demo:
    gr.Markdown(BANNER)
    with gr.Row():
        upload = gr.File(label="Transactions CSV", file_types=[".csv"], type="filepath")
        with gr.Column():
            analyze_btn = gr.Button("Analyze", variant="primary")
            sample_btn = gr.Button("Try sample data")
    status = gr.Markdown()
    summary = gr.Markdown()
    with gr.Row():
        category_plot = gr.BarPlot(x="category", y="total", title="Spending by category", sort="-y")
        month_plot = gr.BarPlot(x="month", y="spent", title="Spending by month")
    gr.Markdown("### Recurring charges")
    recurring_table = gr.Dataframe(interactive=False)
    gr.Markdown("### All transactions")
    transactions_table = gr.Dataframe(interactive=False)

    outputs = [status, summary, category_plot, month_plot, recurring_table, transactions_table]
    analyze_btn.click(analyze_upload, inputs=upload, outputs=outputs)
    sample_btn.click(analyze_sample, outputs=outputs)


if __name__ == "__main__":
    # One request at a time: a CPU-only model shouldn't run two analyses in parallel.
    demo.queue(default_concurrency_limit=1)
    demo.launch(server_name=os.getenv("HOST", "127.0.0.1"), server_port=int(os.getenv("PORT", "7860")))
