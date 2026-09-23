 import io
import re
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st


# -----------------------------
# Page configuration
# -----------------------------
st.set_page_config(
    page_title="LedgerLens AI | Finance Controller",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Professional styling
# -----------------------------
st.markdown(
    """
    <style>
        .main { background-color: #f7f9fc; }
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
        .hero {
            padding: 1.35rem 1.5rem;
            border-radius: 16px;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: white;
            margin-bottom: 1.2rem;
        }
        .hero h1 { margin: 0; font-size: 2rem; }
        .hero p { margin: 0.35rem 0 0; color: #cbd5e1; }
        .section-title {
            font-size: 1.25rem;
            font-weight: 700;
            margin: 1rem 0 0.6rem;
            color: #0f172a;
        }
        .insight-card {
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1rem;
            background: white;
            min-height: 105px;
        }
        .small-label {
            font-size: 0.78rem;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .small-value {
            font-size: 1.35rem;
            font-weight: 700;
            color: #0f172a;
            margin-top: 0.2rem;
        }
        div[data-testid="stMetric"] {
            background: white;
            border: 1px solid #e2e8f0;
            padding: 0.85rem;
            border-radius: 12px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Header
# -----------------------------
st.markdown(
    """
    <div class="hero">
        <h1>📊 LedgerLens AI</h1>
        <p>AI-assisted Finance Controller • Cash Flow • Expense Intelligence • Anomaly Detection</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Helpers
# -----------------------------
def clean_col_name(name):
    return re.sub(r"[^a-z0-9]", "", str(name).strip().lower())


def normalize_columns(df):
    aliases = {
        "date": ["date", "transactiondate", "txn_date", "txndate", "postingdate"],
        "amount": ["amount", "value", "transactionamount", "netamount"],
        "description": [
            "description", "details", "narration", "particulars",
            "remarks", "memo", "transactiondetails"
        ],
        "type": [
            "type", "transactiontype", "drcr", "direction",
            "flow", "inout", "transactiondirection"
        ],
        "category": [
            "category", "expensecategory", "expense_category",
            "accountcategory", "head"
        ],
        "party": [
            "party", "vendor", "customer", "counterparty",
            "name", "client", "supplier"
        ],
        "debit": ["debit", "dr", "debitamount"],
        "credit": ["credit", "cr", "creditamount"],
    }

    lookup = {clean_col_name(c): c for c in df.columns}
    rename_map = {}

    for standard, candidates in aliases.items():
        for candidate in candidates:
            key = clean_col_name(candidate)
            if key in lookup:
                rename_map[lookup[key]] = standard
                break

    return df.rename(columns=rename_map)


def parse_number(series):
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("₹", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.replace("INR", "", regex=False)
        .str.strip(),
        errors="coerce",
    )


def classify_category(description):
    text = str(description).lower()

    rules = {
        "Sales": ["sale", "sales", "revenue", "service revenue", "invoice collection", "receipt"],
        "Purchase": ["purchase", "inventory", "stock", "raw material"],
        "Salary": ["salary", "payroll", "wages", "employee"],
        "Rent": ["rent", "lease"],
        "Utilities": ["electricity", "water bill", "internet", "utility", "phone"],
        "Marketing": ["google ads", "facebook ads", "advertising", "marketing", "promotion"],
        "Bank Charges": ["bank charge", "bank fee", "transaction fee"],
        "Travel": ["travel", "flight", "hotel", "cab", "transport"],
        "Office Expenses": ["stationery", "office", "printer", "supplies"],
        "Tax": ["gst", "tds", "tax", "income tax"],
    }

    for category, keywords in rules.items():
        if any(k in text for k in keywords):
            return category

    return "Other"


def prepare_data(raw):
    df = normalize_columns(raw.copy())

    # Support either Debit/Credit or a signed Amount model.
    has_debit_credit = "debit" in df.columns or "credit" in df.columns

    if "date" not in df.columns:
        df["date"] = pd.NaT
    df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)

    if "description" not in df.columns:
        df["description"] = "Transaction"

    if "party" not in df.columns:
        df["party"] = "Unspecified"

    if "category" not in df.columns:
        df["category"] = ""

    if "debit" in df.columns:
        df["debit"] = parse_number(df["debit"]).fillna(0)
    else:
        df["debit"] = 0.0

    if "credit" in df.columns:
        df["credit"] = parse_number(df["credit"]).fillna(0)
    else:
        df["credit"] = 0.0

    if has_debit_credit:
        # Debit = money going out; Credit = money coming in.
        df["debit"] = df["debit"].abs()
        df["credit"] = df["credit"].abs()
        df["amount"] = df["credit"] - df["debit"]
        df["type"] = df.apply(
            lambda r: "Incoming" if r["credit"] > 0 and r["debit"] == 0
            else ("Outgoing" if r["debit"] > 0 and r["credit"] == 0
                  else ("Incoming" if r["amount"] > 0 else "Outgoing")),
            axis=1,
        )
    else:
        if "amount" not in df.columns:
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            if numeric_cols:
                df["amount"] = df[numeric_cols[0]]
            else:
                raise ValueError(
                    "No Amount, Debit/Credit, or numeric transaction column found."
                )

        df["amount"] = parse_number(df["amount"])

        if "type" not in df.columns:
            df["type"] = df["amount"].apply(
                lambda x: "Incoming" if x >= 0 else "Outgoing"
            )
        else:
            def map_type(value, amount):
                t = clean_col_name(value)
                if t in {"credit", "cr", "incoming", "inflow", "income", "receipt", "received", "sale", "sales"}:
                    return "Incoming"
                if t in {"debit", "dr", "outgoing", "outflow", "expense", "payment", "paid", "purchase"}:
                    return "Outgoing"
                return "Incoming" if amount >= 0 else "Outgoing"

            df["type"] = [
                map_type(t, a) for t, a in zip(df["type"], df["amount"])
            ]

        df["debit"] = df["amount"].where(df["amount"] < 0, 0).abs()
        df["credit"] = df["amount"].where(df["amount"] >= 0, 0)
        df["amount"] = df["credit"] - df["debit"]

    df["description"] = df["description"].fillna("Transaction").astype(str)
    df["party"] = df["party"].fillna("Unspecified").astype(str)

    category_blank = (
        df["category"].isna()
        | df["category"].astype(str).str.strip().eq("")
        | df["category"].astype(str).str.lower().eq("nan")
    )
    df.loc[category_blank, "category"] = df.loc[category_blank, "description"].apply(
        classify_category
    )

    # IQR-based anomaly detection: dataset-relative and explainable.
    positive_values = df.loc[df["amount"].abs() > 0, "amount"].abs()
    if len(positive_values) >= 4:
        q1 = positive_values.quantile(0.25)
        q3 = positive_values.quantile(0.75)
        iqr = q3 - q1
        upper_limit = q3 + 1.5 * iqr
    else:
        upper_limit = float("inf")

    df["anomaly"] = df["amount"].abs() > upper_limit
    df["anomaly_reason"] = df.apply(
        lambda r: f"Unusually large transaction (>{upper_limit:,.0f})"
        if r["anomaly"] else "",
        axis=1,
    )

    df["month"] = df["date"].dt.to_period("M").astype(str)
    df["date_display"] = df["date"].dt.strftime("%d %b %Y").fillna("—")

    return df


def money(value):
    return f"₹{value:,.0f}"


def build_excel(df):
    summary = pd.DataFrame(
        {
            "Metric": [
                "Incoming / Cash Inflow",
                "Outgoing / Cash Outflow",
                "Total Bank Credits",
                "Total Bank Debits",
                "Net Cash Flow",
                "Cash Flow Margin %",
                "Anomalies",
                "Transactions",
            ],
            "Value": [
                df.loc[df["type"] == "Incoming", "amount"].sum(),
                df.loc[df["type"] == "Outgoing", "amount"].sum(),
                df["credit"].sum(),
                df["debit"].sum(),
                df["amount"].sum(),
                (
                    df["amount"].sum()
                    / df.loc[df["type"] == "Incoming", "amount"].sum()
                    * 100
                    if df.loc[df["type"] == "Incoming", "amount"].sum() else 0
                ),
                int(df["anomaly"].sum()),
                len(df),
            ],
        }
    )

    export_df = df[
        [
            "date_display", "party", "description", "category",
            "debit", "credit", "amount", "type", "anomaly", "anomaly_reason"
        ]
    ].copy()

    export_df.columns = [
        "Date", "Party", "Description", "Category",
        "Debit", "Credit", "Net Amount", "Cash Flow Type",
        "Anomaly", "Anomaly Reason"
    ]

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary.to_excel(writer, index=False, sheet_name="Summary")
        export_df.to_excel(writer, index=False, sheet_name="Transactions")
        (
            df.groupby("category", dropna=False)["amount"]
            .agg(["sum", "count"])
            .reset_index()
            .rename(columns={"sum": "Net Amount", "count": "Transactions"})
            .to_excel(writer, index=False, sheet_name="Category Analysis")
        )

    output.seek(0)
    return output


# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.markdown("### 📂 Data Input")
    uploaded = st.file_uploader(
        "Upload transaction CSV",
        type=["csv"],
        help="Recommended: Date, Party, Description, Debit, Credit, Category",
    )

    st.markdown("---")
    st.markdown("### 🧭 Recommended Format")
    st.caption(
        "Debit = cash/payment going out\n\n"
        "Credit = cash/receipt coming in\n\n"
        "You can also upload a signed Amount column."
    )

    st.markdown("---")
    st.markdown("### ⚙️ Prototype Scope")
    st.caption(
        "Decision-support dashboard for finance analysis. "
        "Not an accounting, audit, tax-filing, or payment-authorization system."
    )


# -----------------------------
# Load data
# -----------------------------
if uploaded is not None:
    try:
        raw_df = pd.read_csv(uploaded)
        source_label = uploaded.name
    except Exception as exc:
        st.error(f"Could not read the CSV: {exc}")
        st.stop()
else:
    raw_df = pd.DataFrame(
        [
            ["2026-09-01", "ABC Ltd", "Sales Receipt", 0, 50000, "Sales"],
            ["2026-09-02", "XYZ Suppliers", "Inventory Purchase", 18000, 0, "Purchase"],
            ["2026-09-03", "Electricity Board", "Electricity Bill", 4500, 0, "Utilities"],
            ["2026-09-04", "Client A", "Service Revenue", 0, 35000, "Sales"],
            ["2026-09-05", "Staff Payroll", "Monthly Salary", 22000, 0, "Salary"],
            ["2026-09-06", "ABC Ltd", "Sales Receipt", 0, 42000, "Sales"],
            ["2026-09-07", "Google Ads", "Digital Marketing", 7500, 0, "Marketing"],
            ["2026-09-08", "Landlord", "Office Rent", 15000, 0, "Rent"],
            ["2026-09-09", "Client B", "Invoice Collection", 0, 28000, "Sales"],
            ["2026-09-10", "Bank", "Bank Charges", 1200, 0, "Bank Charges"],
            ["2026-09-11", "Raw Materials Co.", "Raw Material Purchase", 27000, 0, "Purchase"],
            ["2026-09-12", "Client C", "Project Payment", 0, 64000, "Sales"],
            ["2026-09-13", "Travel Desk", "Business Travel", 9800, 0, "Travel"],
            ["2026-09-14", "GST Department", "GST Payment", 6200, 0, "Tax"],
            ["2026-09-15", "Client A", "Invoice Collection", 0, 31000, "Sales"],
        ],
        columns=["Date", "Party", "Description", "Debit", "Credit", "Category"],
    )
    source_label = "Built-in professional demo dataset"

try:
    df = prepare_data(raw_df)
except Exception as exc:
    st.error(str(exc))
    st.info(
        "Use either: Date + Debit/Credit, or Date + Amount. "
        "Optional columns: Party, Description, Type, Category."
    )
    st.stop()

# -----------------------------
# KPI calculations
# -----------------------------
incoming = df.loc[df["type"] == "Incoming", "amount"].sum()
outgoing = df.loc[df["type"] == "Outgoing", "amount"].sum()
net_cash = df["amount"].sum()
bank_credits = df["credit"].sum()
bank_debits = df["debit"].sum()
anomalies = int(df["anomaly"].sum())
transaction_count = len(df)
cash_margin = (net_cash / incoming * 100) if incoming else 0

# -----------------------------
# Source + KPI cards
# -----------------------------
st.caption(f"Data source: **{source_label}** • {transaction_count:,} transactions")

st.markdown('<div class="section-title">Cash Flow Overview</div>', unsafe_allow_html=True)

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Incoming", money(incoming))
c2.metric("Outgoing", money(outgoing))
c3.metric("Net Cash Flow", money(net_cash), delta=f"{cash_margin:.1f}% margin")
c4.metric("Bank Credits", money(bank_credits))
c5.metric("Bank Debits", money(bank_debits))
c6.metric("Anomalies", f"{anomalies:,}")

# -----------------------------
# Main charts
# -----------------------------
st.markdown('<div class="section-title">Financial Intelligence</div>', unsafe_allow_html=True)

left, right = st.columns(2)

with left:
    monthly = (
        df.groupby(["month", "type"], dropna=False)["amount"]
        .sum()
        .reset_index()
    )
    monthly = monthly[monthly["month"] != "NaT"]

    if not monthly.empty:
        fig = px.bar(
            monthly,
            x="month",
            y="amount",
            color="type",
            barmode="group",
            labels={"month": "Month", "amount": "Amount (₹)", "type": "Cash Flow"},
            title="Monthly Incoming vs Outgoing",
        )
        fig.update_layout(height=370, legend_title_text="")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No valid dates available for monthly analysis.")

with right:
    expense_df = (
        df[df["type"] == "Outgoing"]
        .groupby("category", dropna=False)["amount"]
        .sum()
        .reset_index()
        .sort_values("amount", ascending=False)
    )

    if not expense_df.empty:
        fig2 = px.pie(
            expense_df,
            names="category",
            values="amount",
            hole=0.48,
            title="Outgoing / Expense Mix",
        )
        fig2.update_layout(height=370, legend_title_text="")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No outgoing transactions available.")

# -----------------------------
# Controller insights
# -----------------------------
st.markdown('<div class="section-title">Controller Insights</div>', unsafe_allow_html=True)

top_expense = (
    expense_df.iloc[0]["category"] if not expense_df.empty else "—"
)
top_expense_value = (
    expense_df.iloc[0]["amount"] if not expense_df.empty else 0
)

largest_txn = df.loc[df["amount"].abs().idxmax()] if not df.empty else None

i1, i2, i3 = st.columns(3)

with i1:
    status = "Positive" if net_cash >= 0 else "Negative"
    st.markdown(
        f"""
        <div class="insight-card">
            <div class="small-label">Cash Position</div>
            <div class="small-value">{status}</div>
            <div>Net cash movement: {money(net_cash)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with i2:
    st.markdown(
        f"""
        <div class="insight-card">
            <div class="small-label">Top Outgoing Category</div>
            <div class="small-value">{top_expense}</div>
            <div>{money(top_expense_value)} total outgoing</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with i3:
    if largest_txn is not None:
        largest_text = f"{largest_txn['party']} • {money(abs(largest_txn['amount']))}"
    else:
        largest_text = "—"
    st.markdown(
        f"""
        <div class="insight-card">
            <div class="small-label">Largest Transaction</div>
            <div class="small-value">{largest_text}</div>
            <div>{largest_txn['description'] if largest_txn is not None else ''}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------
# Anomaly review
# -----------------------------
st.markdown('<div class="section-title">⚠️ Anomaly Review</div>', unsafe_allow_html=True)

anomaly_df = df[df["anomaly"]].copy()

if anomaly_df.empty:
    st.success("No unusually large transactions were detected in this dataset.")
else:
    st.warning(
        f"{len(anomaly_df)} transaction(s) were flagged for review using a "
        "dataset-relative IQR threshold."
    )
    st.dataframe(
        anomaly_df[
            [
                "date_display", "party", "description", "category",
                "debit", "credit", "amount", "type", "anomaly_reason"
            ]
        ].rename(
            columns={
                "date_display": "Date",
                "party": "Party",
                "description": "Description",
                "category": "Category",
                "debit": "Debit",
                "credit": "Credit",
                "amount": "Net Amount",
                "type": "Cash Flow",
                "anomaly_reason": "Reason",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

# -----------------------------
# Transaction explorer
# -----------------------------
st.markdown('<div class="section-title">🔎 Transaction Explorer</div>', unsafe_allow_html=True)

f1, f2, f3 = st.columns(3)

with f1:
    flow_filter = st.multiselect(
        "Cash Flow Type",
        ["Incoming", "Outgoing"],
        default=["Incoming", "Outgoing"],
    )

with f2:
    category_options = sorted(df["category"].dropna().astype(str).unique())
    category_filter = st.multiselect(
        "Category",
        category_options,
        default=category_options,
    )

with f3:
    search_text = st.text_input("Search party / description", placeholder="e.g. ABC Ltd")

filtered = df[
    df["type"].isin(flow_filter)
    & df["category"].isin(category_filter)
].copy()

if search_text.strip():
    needle = search_text.strip().lower()
    filtered = filtered[
        filtered["party"].str.lower().str.contains(needle, na=False)
        | filtered["description"].str.lower().str.contains(needle, na=False)
    ]

st.dataframe(
    filtered[
        [
            "date_display", "party", "description", "category",
            "debit", "credit", "amount", "type", "anomaly"
        ]
    ].rename(
        columns={
            "date_display": "Date",
            "party": "Party",
            "description": "Description",
            "category": "Category",
            "debit": "Debit",
            "credit": "Credit",
            "amount": "Net Amount",
            "type": "Cash Flow",
            "anomaly": "Anomaly",
        }
    ),
    use_container_width=True,
    hide_index=True,
)

# -----------------------------
# Export
# -----------------------------
st.markdown('<div class="section-title">📥 Finance Report</div>', unsafe_allow_html=True)

excel_file = build_excel(df)

st.download_button(
    "Download Excel Finance Report",
    data=excel_file,
    file_name="LedgerLens_Finance_Controller_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

st.caption(
    "LedgerLens AI is a finance analytics prototype designed for management "
    "decision support. Always validate outputs against source accounting records."
)

