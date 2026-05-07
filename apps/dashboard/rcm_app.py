import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="RevCycleMGMT Claims Pipeline", layout="wide")

st.title("RevCycleMGMT Claims Pipeline")
st.caption("Synthetic revenue launch demo: 837 intake, 999/277CA acknowledgments, 835 remits, clearinghouse rejection, denial follow-up, and payment visibility.")
warehouse = Path(st.secrets.get("WAREHOUSE_DIR", "warehouse"))
kpi_path = warehouse / "marts" / "rcm" / "kpi_daily.parquet"
claim_status_path = warehouse / "marts" / "rcm" / "claim_status.parquet"

if kpi_path.exists():
    df = pd.read_parquet(kpi_path)
else:
    st.warning("No KPI mart found — run build_marts.py first. Showing demo data.")
    df = pd.DataFrame([
        {
            "total_claims": 3,
            "total_claim_lines": 4,
            "total_billed": 705.0,
            "total_allowed": 485.0,
            "total_paid": 148.0,
            "remittance_count": 2,
            "ack_999_count": 3,
            "ack_277ca_count": 3,
            "denial_rate": 0.5,
            "ack_completion_rate": 1.0,
            "clean_claim_rate": 0.3333,
            "claims_paid_or_posted": 1,
            "claims_waiting_for_remit": 0,
            "claims_denied_follow_up": 1,
            "claims_clearinghouse_rejected": 1,
            "claims_implementation_rejected": 0,
            "claims_missing_ack": 0,
            "claims_needing_workqueue_review": 2,
            "payment_variance_total": 300.0,
        }
    ])

top = st.columns(4)
top[0].metric("Total Claims", int(df["total_claims"].sum()))
top[1].metric("Total Billed", f"${df['total_billed'].sum():,.2f}")
top[2].metric("Total Paid", f"${df['total_paid'].sum():,.2f}")
top[3].metric("Payment Variance", f"${df['payment_variance_total'].sum():,.2f}")

ops = st.columns(5)
ops[0].metric("999 ACKs", int(df["ack_999_count"].sum()))
ops[1].metric("277CA ACKs", int(df["ack_277ca_count"].sum()))
ops[2].metric("835 Remits", int(df["remittance_count"].sum()))
ops[3].metric("Missing ACK", int(df["claims_missing_ack"].sum()))
ops[4].metric("Workqueue", int(df["claims_needing_workqueue_review"].sum()))

queues = st.columns(3)
queues[0].metric("Paid / Posted", int(df["claims_paid_or_posted"].sum()))
queues[1].metric("277CA Rejected", int(df.get("claims_clearinghouse_rejected", pd.Series([0])).sum()))
queues[2].metric("Denied Follow-up", int(df["claims_denied_follow_up"].sum()))

rates = st.columns(3)
rates[0].metric("Denial Rate", f"{round(float(df['denial_rate'].mean()) * 100, 2)}%")
rates[1].metric("ACK Completion", f"{round(float(df['ack_completion_rate'].mean()) * 100, 2)}%")
rates[2].metric("Clean Claim Rate", f"{round(float(df['clean_claim_rate'].mean()) * 100, 2)}%")

st.subheader("KPI Detail")
st.dataframe(df)

st.subheader("Claim Journey")
if claim_status_path.exists():
    claim_status = pd.read_parquet(claim_status_path)
    st.dataframe(claim_status)

    if "workflow_status" in claim_status:
        status_counts = claim_status["workflow_status"].value_counts().rename_axis("status").reset_index(name="claims")
        st.subheader("Workflow Status")
        st.bar_chart(status_counts, x="status", y="claims")

    if "needs_workqueue_review" in claim_status:
        workqueue = claim_status[claim_status["needs_workqueue_review"]].copy()
    elif "workflow_status" in claim_status:
        workqueue = claim_status[claim_status["workflow_status"] != "paid_or_posted"].copy()
    else:
        workqueue = claim_status.iloc[0:0].copy()

    st.subheader("Claim Workqueue Export")
    if workqueue.empty:
        st.success("No claim rows need workqueue review in this demo run.")
    else:
        export_columns = [
            column
            for column in [
                "claim_id",
                "payer",
                "workflow_status",
                "denial_count",
                "carc_codes",
                "rarc_codes",
                "root_cause_groups",
                "payment_variance",
                "ack_999_status",
                "ack_277ca_status",
            ]
            if column in workqueue.columns
        ]
        st.dataframe(workqueue[export_columns])
        st.download_button(
            "Download Claim Workqueue CSV",
            workqueue[export_columns].to_csv(index=False).encode("utf-8"),
            "revcyclemgmt_claim_workqueue.csv",
            "text/csv",
        )
else:
    st.info("Run the mart build to create claim_status.parquet.")
