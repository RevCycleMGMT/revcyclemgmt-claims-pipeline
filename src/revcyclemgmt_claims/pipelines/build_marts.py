import argparse
import json
from pathlib import Path
import pandas as pd


def load_jsonl_dir(path: Path) -> pd.DataFrame:
    rows = []
    if not path.exists():
        return pd.DataFrame()
    for f in path.glob("*.jsonl"):
        with open(f) as fh:
            for line in fh:
                rows.append(json.loads(line))
    return pd.DataFrame(rows)


def _unique_codes(series: pd.Series) -> str:
    codes = sorted({str(code).strip() for code in series.dropna() if str(code).strip()})
    return ",".join(codes)


def _load_carc_groups(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    mapping = pd.read_csv(path, dtype=str).fillna("")
    return dict(zip(mapping["CARC"].str.strip(), mapping["Group"].str.strip()))


def build_claim_status_mart(
    claims: pd.DataFrame,
    lines: pd.DataFrame,
    adjud: pd.DataFrame,
    pays: pd.DataFrame,
    acks: pd.DataFrame,
    carc_groups: dict[str, str] | None = None,
) -> pd.DataFrame:
    if claims.empty:
        return pd.DataFrame()

    claim_status = claims[["claim_id", "payer", "claim_type", "billed_amt"]].drop_duplicates("claim_id").copy()

    if not lines.empty:
        line_aggs = {
            "line_count": ("line_no", "count"),
            "line_billed": ("billed", "sum"),
            "line_allowed": ("allowed", "sum"),
            "line_paid": ("paid", "sum"),
        }
        if "patient_resp" in lines.columns:
            line_aggs["patient_resp_total"] = ("patient_resp", "sum")
        line_rollup = (
            lines.groupby("claim_id", as_index=False)
            .agg(**line_aggs)
        )
        claim_status = claim_status.merge(line_rollup, on="claim_id", how="left")

    if not pays.empty:
        payment_rollup = (
            pays.groupby("claim_id", as_index=False)
            .agg(remittance_count=("claim_id", "count"), paid_amount=("amount", "sum"))
        )
        claim_status = claim_status.merge(payment_rollup, on="claim_id", how="left")

    if not adjud.empty:
        adjud_work = adjud.copy()
        for column, default in {
            "allowed": 0.0,
            "paid": 0.0,
            "patient_resp": 0.0,
            "CARC": "",
            "RARC": "",
            "status": "",
        }.items():
            if column not in adjud_work:
                adjud_work[column] = default
            adjud_work[column] = adjud_work[column].fillna(default)
        adjud_work["is_denial"] = adjud_work["status"].str.lower() != "paid"
        group_map = carc_groups or {}
        adjud_work["root_cause_group"] = (
            adjud_work["CARC"].astype(str).str.strip().map(group_map).fillna("Unmapped")
        )
        adjud_rollup = (
            adjud_work.groupby("claim_id", as_index=False)
            .agg(
                adjud_allowed=("allowed", "sum"),
                adjud_paid=("paid", "sum"),
                adjud_patient_resp=("patient_resp", "sum"),
            )
        )
        claim_status = claim_status.merge(adjud_rollup, on="claim_id", how="left")

        denied_work = adjud_work[adjud_work["is_denial"]].copy()
        if denied_work.empty:
            denial_rollup = pd.DataFrame(columns=["claim_id", "denial_count", "carc_codes", "rarc_codes", "root_cause_groups"])
        else:
            denied_work["root_cause_group"] = denied_work["root_cause_group"].where(
                denied_work["root_cause_group"].astype(bool),
                "Unmapped",
            )
            denial_rollup = (
                denied_work.groupby("claim_id", as_index=False)
                .agg(
                    denial_count=("is_denial", "sum"),
                    carc_codes=("CARC", _unique_codes),
                    rarc_codes=("RARC", _unique_codes),
                    root_cause_groups=("root_cause_group", _unique_codes),
                )
            )
        claim_status = claim_status.merge(denial_rollup, on="claim_id", how="left")

    if not acks.empty:
        ack_pivot = (
            acks.pivot_table(index="claim_id", columns="ack_type", values="status", aggfunc="last")
            .reset_index()
            .rename(columns={"999": "ack_999_status", "277CA": "ack_277ca_status"})
        )
        claim_status = claim_status.merge(ack_pivot, on="claim_id", how="left")

    defaults = {
        "line_count": 0,
        "line_billed": 0.0,
        "line_allowed": 0.0,
        "line_paid": 0.0,
        "patient_resp_total": 0.0,
        "adjud_allowed": 0.0,
        "adjud_paid": 0.0,
        "adjud_patient_resp": 0.0,
        "remittance_count": 0,
        "paid_amount": 0.0,
        "denial_count": 0,
        "carc_codes": "",
        "rarc_codes": "",
        "root_cause_groups": "",
        "ack_999_status": "",
        "ack_277ca_status": "",
    }
    for column, default in defaults.items():
        if column not in claim_status:
            claim_status[column] = default
        claim_status[column] = claim_status[column].fillna(default)

    claim_status["line_allowed"] = claim_status["adjud_allowed"].where(
        claim_status["adjud_allowed"].astype(float) > 0,
        claim_status["line_allowed"].astype(float),
    )
    claim_status["line_paid"] = claim_status["adjud_paid"].where(
        claim_status["adjud_paid"].astype(float) > 0,
        claim_status["line_paid"].astype(float),
    )
    claim_status["patient_resp_total"] = claim_status["adjud_patient_resp"].where(
        claim_status["adjud_patient_resp"].astype(float) > 0,
        claim_status["patient_resp_total"].astype(float),
    )

    claim_status["has_999_ack"] = claim_status["ack_999_status"].astype(bool)
    claim_status["has_277ca_ack"] = claim_status["ack_277ca_status"].astype(bool)
    claim_status["is_999_rejected"] = claim_status["ack_999_status"].astype(str).str.lower().str.contains("reject")
    claim_status["is_277ca_rejected"] = claim_status["ack_277ca_status"].astype(str).str.lower().str.contains("reject")
    claim_status["has_835_remit"] = claim_status["remittance_count"].astype(int) > 0
    claim_status["payment_variance"] = (
        claim_status["line_allowed"].astype(float)
        - claim_status["paid_amount"].astype(float)
        - claim_status["patient_resp_total"].astype(float)
    ).round(2)

    def workflow_status(row: pd.Series) -> str:
        if bool(row["is_999_rejected"]):
            return "implementation_rejected"
        if bool(row["is_277ca_rejected"]):
            return "clearinghouse_rejected"
        if int(row["denial_count"]) > 0:
            return "denied_follow_up"
        if bool(row["has_835_remit"]):
            return "paid_or_posted"
        if bool(row["has_999_ack"]) and bool(row["has_277ca_ack"]):
            return "accepted_waiting_for_remit"
        if bool(row["has_999_ack"]):
            return "implementation_accepted_waiting_for_277ca"
        return "waiting_for_ack"

    claim_status["workflow_status"] = claim_status.apply(workflow_status, axis=1)
    claim_status["needs_workqueue_review"] = (
        (claim_status["workflow_status"] != "paid_or_posted")
        | (claim_status["denial_count"].astype(int) > 0)
        | (claim_status["payment_variance"].astype(float) > 0)
    )
    return claim_status


def main(warehouse: Path):
    norm = warehouse / "normalized"
    claims = load_jsonl_dir(norm / "claims_header")
    lines  = load_jsonl_dir(norm / "claims_line")
    adjud  = load_jsonl_dir(norm / "adjudication")
    pays   = load_jsonl_dir(norm / "payments")
    acks   = load_jsonl_dir(norm / "acknowledgments")
    repo_root = Path(__file__).resolve().parents[3]
    carc_groups = _load_carc_groups(repo_root / "config" / "mappings" / "carc_groups.csv")

    # Simple KPIs for demo
    if lines.empty:
        print("No normalized lines found; did you run ingest_edi.py?")
        return

    denial_count = 0
    if not adjud.empty and "status" in adjud:
        denial_count = int((adjud["status"].str.lower() != "paid").sum())

    total_claim_lines = int(lines["line_no"].count())
    claim_status = build_claim_status_mart(claims, lines, adjud, pays, acks, carc_groups)
    total_claims = int(claims["claim_id"].nunique()) if not claims.empty else 0
    ack_complete = int((claim_status["has_999_ack"] & claim_status["has_277ca_ack"]).sum()) if not claim_status.empty else 0
    clean_claims = int(
        (
            (claim_status["denial_count"].astype(int) == 0)
            & (claim_status["has_999_ack"])
            & (claim_status["has_277ca_ack"])
            & (~claim_status["is_999_rejected"])
            & (~claim_status["is_277ca_rejected"])
        ).sum()
    ) if not claim_status.empty else 0
    kpi = pd.DataFrame([{
        "total_claims": total_claims,
        "total_claim_lines": total_claim_lines,
        "total_billed": float(claims["billed_amt"].sum()) if not claims.empty else float(lines["billed"].sum()),
        "total_allowed": float(claim_status["line_allowed"].sum()) if not claim_status.empty else float(lines["allowed"].sum()),
        "total_paid": float(claim_status["paid_amount"].sum()) if not claim_status.empty else float(lines["paid"].sum()),
        "remittance_count": int(len(pays)),
        "ack_999_count": int((acks["ack_type"] == "999").sum()) if not acks.empty else 0,
        "ack_277ca_count": int((acks["ack_type"] == "277CA").sum()) if not acks.empty else 0,
        "denial_count": denial_count,
        "denial_rate": denial_count / total_claim_lines if total_claim_lines else 0.0,
        "ack_completion_rate": ack_complete / total_claims if total_claims else 0.0,
        "clean_claim_rate": clean_claims / total_claims if total_claims else 0.0,
        "claims_paid_or_posted": int((claim_status["workflow_status"] == "paid_or_posted").sum()) if not claim_status.empty else 0,
        "claims_waiting_for_remit": int((claim_status["workflow_status"] == "accepted_waiting_for_remit").sum()) if not claim_status.empty else 0,
        "claims_denied_follow_up": int((claim_status["workflow_status"] == "denied_follow_up").sum()) if not claim_status.empty else 0,
        "claims_clearinghouse_rejected": int((claim_status["workflow_status"] == "clearinghouse_rejected").sum()) if not claim_status.empty else 0,
        "claims_implementation_rejected": int((claim_status["workflow_status"] == "implementation_rejected").sum()) if not claim_status.empty else 0,
        "claims_missing_ack": int((~claim_status["has_999_ack"] | ~claim_status["has_277ca_ack"]).sum()) if not claim_status.empty else 0,
        "claims_needing_workqueue_review": int(claim_status["needs_workqueue_review"].sum()) if not claim_status.empty else 0,
        "payment_variance_total": float(claim_status["payment_variance"].sum()) if not claim_status.empty else 0.0,
    }])
    out_dir = warehouse / "marts" / "rcm"
    out_dir.mkdir(parents=True, exist_ok=True)
    kpi_path = out_dir / "kpi_daily.parquet"
    claim_status_path = out_dir / "claim_status.parquet"
    kpi.to_parquet(kpi_path, index=False)
    if not claim_status.empty:
        claim_status.to_parquet(claim_status_path, index=False)
    print(f"Wrote {kpi_path}")
    if not claim_status.empty:
        print(f"Wrote {claim_status_path}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--warehouse", type=Path, default=Path("warehouse"))
    args = ap.parse_args()
    main(args.warehouse)
