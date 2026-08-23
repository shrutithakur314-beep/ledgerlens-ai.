
import os, io, json, re
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="LedgerLens AI", page_icon="💳", layout="wide")

CATEGORIES = {
    "salary": "Payroll", "wages": "Payroll", "payroll": "Payroll",
    "rent": "Rent & Utilities", "electric": "Rent & Utilities", "internet": "Rent & Utilities",
    "aws": "Technology", "software": "Technology", "hosting": "Technology",
    "ads": "Marketing", "facebook": "Marketing", "google ads": "Marketing",
    "travel": "Travel", "flight": "Travel", "uber": "Travel", "ola": "Travel",
    "food": "Meals", "restaurant": "Meals", "swiggy": "Meals", "zomato": "Meals",
    "office": "Office Supplies", "stationery": "Office Supplies",
    "tax": "Taxes", "gst": "Taxes", "tds": "Taxes",
    "customer": "Revenue", "sales": "Revenue", "invoice": "Revenue", "payment received": "Revenue",
    "vendor": "Vendor Payments", "supplier": "Vendor Payments"
}

def categorize(text):
    s = str(text).lower()
    for key, cat in CATEGORIES.items():
        if key in s:
            return cat
    return "Other"

def detect_anomaly(df):
    if df.empty:
        return df
    out = df.copy()
    vals = out["amount"].abs()
    threshold = vals.mean() + 2 * vals.std() if len(vals) > 1 else vals.mean() * 2
    out["anomaly"] = (vals > threshold) | (vals >= vals.quantile(0.95))
    return out

def parse_csv(upload):
    raw = pd.read_csv(upload)
    cols = {c.lower().strip(): c for c in raw.columns}
    date_col = next((cols[c] for c in ["date","transaction date","txn date"] if c in cols), None)
    desc_col = next((cols[c] for c in ["description","narration","details","merchant"] if c in cols), None)
    amount_col = next((cols[c] for c in ["amount","value","transaction amount"] if c in cols), None)
    debit_col = next((cols[c] for c in ["debit","withdrawal"] if c in cols), None)
    credit_col = next((cols[c] for c in ["credit","deposit"] if c in cols), None)
    if not desc_col:
        raise ValueError("CSV needs a Description/Narration/Merchant column.")
    if amount_col:
        raw["amount"] = pd.to_numeric(raw[amount_col], errors="coerce").fillna(0)
        raw["type"] = raw["amount"].apply(lambda x: "Credit" if x >= 0 else "Debit")
    elif debit_col or credit_col:
        d = pd.to_numeric(raw[debit_col], errors="coerce").fillna(0) if debit_col else 0
        c = pd.to_numeric(raw[credit_col], errors="coerce").fillna(0) if credit_col else 0
        raw["amount"] = c - d
        raw["type"] = raw["amount"].apply(lambda x: "Credit" if x >= 0 else "Debit")
    else:
        raise ValueError("CSV needs Amount, or Debit/Credit columns.")
    raw["description"] = raw[desc_col].astype(str)
    raw["category"] = raw["description"].apply(categorize)
    if date_col:
        raw["date"] = pd.to_datetime(raw[date_col], errors="coerce")
    else:
        raw["date"] = pd.Timestamp.today()
    return raw[["date","description","amount","type","category"]]

st.title("💳 LedgerLens AI")
st.caption("AI-assisted Finance Controller • transaction intelligence for small businesses")

with st.sidebar:
    st.header("Data Input")
    uploaded = st.file_uploader("Upload transaction CSV", type=["csv"])
    st.markdown("**Expected columns:** Date, Description, Amount")
    st.markdown("Also supports Debit/Credit columns.")
    st.divider()
    st.info("Demo mode works without an API key. Optional Gemini integration can be added through GEMINI_API_KEY.")

if uploaded:
    try:
        df = parse_csv(uploaded)
    except Exception as e:
        st.error(str(e))
        st.stop()
else:
    demo = pd.DataFrame({
        "date": pd.to_datetime(["2026-08-01","2026-08-02","2026-08-03","2026-08-04","2026-08-05","2026-08-06","2026-08-07","2026-08-08","2026-08-09","2026-08-10"]),
        "description": ["Customer invoice received","AWS hosting","Office rent","Google Ads","Uber business travel","Vendor payment","Salary payroll","GST payment","Customer invoice received","Restaurant meeting"],
        "amount": [85000,-12500,-30000,-8000,-1800,-22000,-45000,-6500,62000,-2400]
    })
    demo["type"] = demo["amount"].apply(lambda x: "Credit" if x >= 0 else "Debit")
    demo["category"] = demo["description"].apply(categorize)
    df = demo
    st.warning("Showing demo data. Upload your own CSV from the sidebar to analyze real transactions.")

df = detect_anomaly(df)
income = df.loc[df.amount > 0, "amount"].sum()
expense = -df.loc[df.amount < 0, "amount"].sum()
net = income - expense

c1,c2,c3,c4 = st.columns(4)
c1.metric("Incoming", f"₹{income:,.0f}")
c2.metric("Outgoing", f"₹{expense:,.0f}")
c3.metric("Net Cash Flow", f"₹{net:,.0f}")
c4.metric("Anomalies", int(df.anomaly.sum()))

st.divider()
left,right = st.columns(2)

with left:
    st.subheader("📊 Category Breakdown")
    exp = df[df.amount < 0].copy()
    exp["expense"] = -exp.amount
    if not exp.empty:
        cat = exp.groupby("category", as_index=False)["expense"].sum().sort_values("expense", ascending=False)
        fig = px.bar(cat, x="category", y="expense", title="Expenses by category")
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("💰 Cash Flow")
    flow = df.groupby("date", as_index=False)["amount"].sum()
    fig2 = px.line(flow, x="date", y="amount", markers=True, title="Daily net movement")
    st.plotly_chart(fig2, use_container_width=True)

st.subheader("🤖 AI Controller Insights")
insights = []
if expense > income:
    insights.append("⚠️ Outgoing cash is higher than incoming cash in this dataset. Review discretionary spending.")
else:
    insights.append("✅ Incoming cash exceeds outgoing cash. Continue monitoring the largest expense categories.")
if not exp.empty:
    top = cat.iloc[0]
    insights.append(f"📌 Highest expense category: {top['category']} (₹{top['expense']:,.0f}).")
if df.anomaly.sum():
    insights.append(f"🔎 {int(df.anomaly.sum())} transaction(s) were flagged as unusually large and should be reviewed.")
else:
    insights.append("✅ No unusually large transactions were detected using the demo anomaly rule.")
insights.append("💡 Recommended control: review high-value transactions before approval and reconcile them with invoices/bank records.")

for x in insights:
    st.write(x)

st.subheader("🔍 Transaction Review")
show = df.copy()
show["amount"] = show["amount"].map(lambda x: f"₹{x:,.2f}")
st.dataframe(show, use_container_width=True, hide_index=True)

csv = df.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Download analyzed CSV", csv, "ledgerlens_analyzed.csv", "text/csv")

st.divider()
st.caption("LedgerLens AI is a prototype for decision support. It does not provide accounting, tax, investment or regulatory advice.")
