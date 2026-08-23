# LedgerLens AI — Finance Controller

LedgerLens AI is a lightweight AI-assisted finance controller prototype for small businesses. It converts raw transaction data into cash-flow metrics, expense categories, anomaly flags and actionable controller insights.

## Why this project?

Small businesses often have transaction data but lack a simple control layer that answers:
- Where is cash going?
- Which expense categories are growing?
- Which transactions deserve review?
- What should the finance team reconcile first?

## Core features

- CSV transaction ingestion
- Automatic transaction categorization
- Incoming/outgoing/net cash-flow metrics
- Expense category analysis
- Unusually-large transaction detection
- Controller-style AI insights
- Downloadable analyzed CSV
- Demo mode with sample data

## Tech stack

Python, Streamlit, Pandas, Plotly.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## CSV format

Minimum:
`Date, Description, Amount`

Positive amount = incoming money.
Negative amount = outgoing money.

Debit/Credit columns are also supported.

## Architecture

CSV → Parser/Normalizer → Categorization Engine → Anomaly Detector → Controller Insight Layer → Dashboard

## Important limitation

This is a prototype and decision-support tool. It does not replace an accountant, auditor, tax professional, or payment authorization system.

## Build challenge / failure recovery

The first design assumed every bank export would have the same columns. That failed because bank exports differ. The parser was therefore changed to detect common aliases such as Amount, Value, Debit, Credit, Narration and Description, with clear validation errors when required fields are absent.

For anomaly detection, a fixed rupee threshold would not generalize across businesses. The prototype uses a dataset-relative statistical rule and quantile flagging, making the control more adaptable while keeping the result explainable.
