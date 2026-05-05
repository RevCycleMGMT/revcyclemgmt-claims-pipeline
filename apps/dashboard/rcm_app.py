import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="RevCycleMGMT Claims Pipeline", layout="wide")

st.title("RevCycleMGMT Claims Pipeline - RCM KPIs (Demo)")
warehouse = Path(st.secrets.get("WAREHOUSE_DIR", "warehouse"))
kpi_path = warehouse / "marts" / "rcm" / "kpi_daily.parquet"

if kpi_path.exists():
    df = pd.read_parquet(kpi_path)
else:
    st.warning("No KPI mart found — run build_marts.py first. Showing demo data.")
    df = pd.DataFrame([
        {
            "total_claims": 1,
            "total_claim_lines": 2,
            "total_billed": 250.0,
            "total_allowed": 200.0,
            "total_paid": 160.0,
            "remittance_count": 1,
            "ack_999_count": 1,
            "ack_277ca_count": 1,
            "denial_rate": 0.0,
        }
    ])

st.metric("Total Claims", int(df['total_claims'].sum()))
st.metric("Total Claim Lines", int(df['total_claim_lines'].sum()))
st.metric("Total Billed ($)", round(df['total_billed'].sum(), 2))
st.metric("Total Allowed ($)", round(df['total_allowed'].sum(), 2))
st.metric("Total Paid ($)", round(df['total_paid'].sum(), 2))
st.metric("835 Remits", int(df['remittance_count'].sum()))
st.metric("999 ACKs", int(df['ack_999_count'].sum()))
st.metric("277CA ACKs", int(df['ack_277ca_count'].sum()))
st.metric("Denial Rate", f"{round(float(df['denial_rate'].mean()) * 100, 2)}%")

st.subheader("Detail")
st.dataframe(df)
