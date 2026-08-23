# 5-Minute Pitch — LedgerLens AI

## 0:00–0:35 Problem
Small businesses generate lots of transaction data, but finance teams still spend time cleaning exports, categorizing expenses and manually finding unusual transactions.

## 0:35–1:10 Solution
LedgerLens AI is a finance-controller prototype that turns a transaction CSV into a control dashboard: cash-flow metrics, expense categories, anomaly flags and prioritized controller insights.

## 1:10–2:00 Demo
1. Open the app.
2. Show demo data.
3. Upload sample_transactions.csv.
4. Show Incoming, Outgoing, Net Cash Flow and Anomalies.
5. Show category chart.
6. Show cash-flow chart.
7. Show AI Controller Insights.
8. Open transaction review and download analyzed CSV.

## 2:00–3:10 How it works
CSV is normalized into a common schema. Descriptions are categorized using explainable keyword rules. Large transactions are flagged using a dataset-relative statistical rule plus a high-quantile check. The insight layer turns these signals into controller-style recommendations.

## 3:10–4:00 Technical challenges
Different bank CSV formats were the first challenge. The parser was made tolerant of common column names and Debit/Credit exports. Another challenge was anomaly detection: a fixed threshold was too brittle, so the prototype moved to relative statistics.

## 4:00–4:40 AI judgment and future scope
The prototype deliberately uses AI-assisted decision support rather than pretending every task needs an LLM. Future versions can add an LLM with structured outputs for explanations, invoice OCR, approval agents, reconciliation and human-in-the-loop controls.

## 4:40–5:00 Close
LedgerLens AI aims to give small finance teams a simple first layer of financial control: understand cash, find what needs attention, and act faster.
