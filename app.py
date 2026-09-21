import io
import re
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="LedgerLens AI – Finance Controller",
    page_icon="📊",
    layout="wide"
)

st.title("📊 LedgerLens AI")
st.caption("AI-assisted Finance Controller • transaction analysis • cash-flow insights")

CATEGORY_RULES = {
    "Salary": ["salary", "payroll", "wages"],
    "Rent": ["rent", "lease"],
    "Utilities": ["electricity", "internet", "mobile", "water", "utility", "gas"],
    "Purchase": ["purchase", "inventory", "stock", "raw material", "materials"],
    "Travel": ["travel", "flight", "hotel", "cab", "uber", "ola", "transport"],
    "Marketing": ["marketing", "advertising", "ads", "promotion"],
    "Office": ["office", "stationery", "printer", "supplies"],
    "Bank Charges": ["bank charge", "bank fee", "transaction fee"],
    "Sales": ["sale", "sales", "revenue", "invoice"],
}


def normalize_columns(df):
    mapping = {}

    for c in df.columns:
        key = re.sub(r"[^a-z0-9]", "", str(c).lower())

        if key in {"date", "transactiondate", "txndate"}:
            mapping[c] = "Date"
        elif key in {"amount", "value", "transactionamount", "amt"}:
            mapping[c] = "Amount"
        elif key in {
            "description",
            "details",
            "narration",
            "particulars",
            "remarks",
        }:
            mapping[c] = "Description"
        elif key in {
            "type",
            "transactiontype",
            "drcr",
            "direction",
            "flow",
        }:
            mapping[c] = "Type"
        elif key in {"category", "expensecategory"}:
            mapping[c] = "Category"
        elif key in {
            "party",
            "vendor",
            "customer",
            "counterparty",
            "name",
        }:
            mapping[c] = "Party"

    return df.rename(columns=mapping)


def classify(text):
    text = str(text).lower()

    for category, words in CATEGORY_RULES.items():
        if any(word in text for word in words):
            return category

    return "Other"


def prepare_data(raw):
    df = normalize_columns(raw.copy())

    if "Amount" not in df.columns:
        numeric = df.select_dtypes(include="number").columns.tolist()

        if numeric:
            df = df.rename(columns={numeric[0]: "Amount"})
        else:
            raise ValueError("Could not find an Amount column.")

    df["Amount"] = pd.to_numeric(
        df["Amount"]
        .astype(str)
        .str.replace(r"[₹$,]", "", regex=True)
        .str.replace(r"\s+", "", regex=True),
        errors="coerce",
    )

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    else:
        df["Date"] = pd.Timestamp.today().normalize()

    if "Description" not in df.columns:
        df["Description"] = ""

    if "Party" not in df.columns:
        df["Party"] = "Unknown"

    if "Type" not in df.columns:
        df["Type"] = df["Amount"].apply(
            lambda x: "Incoming" if x >= 0 else "Outgoing"
        )
    else:
        t = df["Type"].astype(str).str.lower()

        df["Type"] = t.map(
            lambda x: (
                "Incoming"
                if any(
                    k in x
                    for k in [
                        "in",
                        "credit",
                        "cr",
                        "income",
                        "receipt",
                        "sale",
                    ]
                )
                else "Outgoing"
            )
        )

    df["Amount"] = df["Amount"].abs()

    df = df.dropna(subset=["Amount", "Date"]).copy()

    if "Category" not in df.columns:
        df["Category"] = (
            df["Description"].astype(str)
            + " "
            + df["Party"].astype(str)
        ).apply(classify)
    else:
        df["Category"] = (
            df["Category"]
            .fillna("Other")
            .astype(str)
            .replace("", "Other")
        )

    q1 = df["Amount"].quantile(0.25)
    q3 = df["Amount"].quantile(0.75)

    iqr = q3 - q1
    upper = q3 + 1.5 * iqr

    if iqr > 0:
        df["Anomaly"] = df["Amount"] > upper
    else:
        df["Anomaly"] = False

    df["Anomaly Reason"] = df["Anomaly"].apply(
        lambda x: (
            "Unusually high transaction amount"
            if x
            else ""
        )
    )

    return df.sort_values("Date")


def money(x):
    return f"₹{x:,.0f}"


uploaded = st.file_uploader(
    "Upload your transaction CSV",
    type=["csv"],
)

if uploaded is None:
    st.info("Upload a CSV to start analysing your transactions.")

    st.markdown(
        "Recommended columns: **Date, Amount, Description, "
        "Type, Category, Party**"
    )

    st.stop()


try:
    raw_data = pd.read_csv(uploaded)
    df = prepare_data(raw_data)

except Exception as e:
    st.error(f"Could not analyse this file: {e}")
    st.stop()


st.sidebar.header("🔎 Filters")

types = sorted(df["Type"].unique())

selected_types = st.sidebar.multiselect(
    "Transaction type",
    types,
    default=types,
)

cats = sorted(df["Category"].unique())

selected_cats = st.sidebar.multiselect(
    "Category",
    cats,
    default=cats,
)

dmin = df["Date"].min().date()
dmax = df["Date"].max().date()

dates = st.sidebar.date_input(
    "Date range",
    value=(dmin, dmax),
    min_value=dmin,
    max_value=dmax,
)

search = st.sidebar.text_input(
    "Search party / description"
)


filtered = df[
    df["Type"].isin(selected_types)
    & df["Category"].isin(selected_cats)
].copy()


if isinstance(dates, tuple) and len(dates) == 2:
    filtered = filtered[
        (filtered["Date"].dt.date >= dates[0])
        & (filtered["Date"].dt.date <= dates[1])
    ]


if search:
    mask = (
        filtered["Party"]
        .astype(str)
        .str.contains(search, case=False, na=False)
        |
        filtered["Description"]
        .astype(str)
        .str.contains(search, case=False, na=False)
    )

    filtered = filtered[mask]


if filtered.empty:
    st.warning("No transactions match the selected filters.")
    st.stop()


incoming = filtered.loc[
    filtered["Type"] == "Incoming",
    "Amount",
].sum()

outgoing = filtered.loc[
    filtered["Type"] == "Outgoing",
    "Amount",
].sum()

net = incoming - outgoing

anomalies = int(
    filtered["Anomaly"].sum()
)

margin = (
    net / incoming * 100
    if incoming
    else 0
)


c1, c2, c3, c4, c5 = st.columns(5)

c1.metric(
    "💰 Total Income",
    money(incoming),
)

c2.metric(
    "💸 Total Expenses",
    money(outgoing),
)

c3.metric(
    "📈 Net Cash Flow",
    money(net),
    f"{margin:.1f}% of income",
)

c4.metric(
    "🚨 Anomalies",
    anomalies,
)

c5.metric(
    "🧾 Transactions",
    len(filtered),
)


left, right = st.columns(2)


with left:
    monthly = (
        filtered.assign(
            Month=filtered["Date"]
            .dt.to_period("M")
            .astype(str)
        )
        .groupby(
            ["Month", "Type"],
            as_index=False,
        )["Amount"]
        .sum()
    )

    st.plotly_chart(
        px.bar(
            monthly,
            x="Month",
            y="Amount",
            color="Type",
            barmode="group",
            title="📅 Monthly Cash Flow",
        ),
        use_container_width=True,
    )


with right:
    expense = (
        filtered[
            filtered["Type"] == "Outgoing"
        ]
        .groupby(
            "Category",
            as_index=False,
        )["Amount"]
        .sum()
        .sort_values(
            "Amount",
            ascending=False,
        )
    )

    if not expense.empty:
        st.plotly_chart(
            px.pie(
                expense,
                names="Category",
                values="Amount",
                hole=0.45,
                title="💸 Expense Breakdown",
            ),
            use_container_width=True,
        )
    else:
        st.info(
            "No outgoing transactions in the current filter."
        )


st.subheader("🤖 Finance Insights")


if net >= 0:
    st.markdown(
        f"✅ Net cash flow is positive at **{money(net)}**."
    )
else:
    st.markdown(
        f"⚠️ Net cash flow is negative at **{money(abs(net))}**."
    )


if not expense.empty:
    top = expense.iloc[0]

    st.markdown(
        f"📌 **{top['Category']}** is the largest expense "
        f"category at **{money(top['Amount'])}**."
    )


if anomalies:
    largest = (
        filtered[filtered["Anomaly"]]
        .sort_values(
            "Amount",
            ascending=False,
        )
        .iloc[0]
    )

    st.markdown(
        f"🚨 Largest flagged transaction: "
        f"**{money(largest['Amount'])}** — "
        f"{largest['Party']}."
    )
else:
    st.markdown(
        "✅ No unusually high transactions detected."
    )


st.subheader("🚨 Anomaly Review")

anom = filtered[
    filtered["Anomaly"]
]


if anom.empty:
    st.success("No anomalies found.")
else:
    st.dataframe(
        anom[
            [
                "Date",
                "Party",
                "Description",
                "Category",
                "Type",
                "Amount",
                "Anomaly Reason",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


st.subheader("🔎 Transaction Explorer")

cols = [
    c
    for c in [
        "Date",
        "Party",
        "Description",
        "Category",
        "Type",
        "Amount",
        "Anomaly",
    ]
    if c in filtered.columns
]

st.dataframe(
    filtered[cols].sort_values(
        "Date",
        ascending=False,
    ),
    use_container_width=True,
    hide_index=True,
)


st.subheader("📥 Export Report")

report = io.BytesIO()

with pd.ExcelWriter(
    report,
    engine="openpyxl",
) as writer:

    filtered.to_excel(
        writer,
        sheet_name="Transactions",
        index=False,
    )

    pd.DataFrame(
        {
            "Metric": [
                "Total Income",
                "Total Expenses",
                "Net Cash Flow",
                "Profit Margin %",
                "Anomalies",
            ],
            "Value": [
                incoming,
                outgoing,
                net,
                round(margin, 2),
                anomalies,
            ],
        }
    ).to_excel(
        writer,
        sheet_name="Summary",
        index=False,
    )

    if not anom.empty:
        anom.to_excel(
            writer,
            sheet_name="Anomalies",
            index=False,
        )


st.download_button(
    "⬇️ Download Excel Finance Report",
    report.getvalue(),
    "LedgerLens_Finance_Report.xlsx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)


st.caption(
    "LedgerLens AI • Built with Streamlit • "
    "For analysis and decision support"
)
