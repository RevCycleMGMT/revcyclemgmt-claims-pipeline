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


def build_claim_status_mart(
    claims: pd.DataFrame,
    lines: pd.DataFrame,
    adjud: pd.DataFrame,
    pays: pd.DataFrame,
    acks: pd.DataFrame,
) -> pd.DataFrame:
    if claims.empty:
        return pd.DataFrame()

    claim_status = claims[["claim_id", "payer", "claim_type", "billed_amt"]].drop_duplicates("claim_id").copy()

    if not lines.empty:
        line_rollup = (
            lines.groupby("claim_id", as_index=False)
            .agg(
                line_count=("line_no", "count"),
                line_billed=("billed", "sum"),
                line_allowed=("allowed", "sum"),
                line_paid=("paid", "sum"),
            )
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
        adjud_work["is_denial"] = adjud_work["status"].str.lower() != "paid"
        denial_rollup = (
            adjud_work.groupby("claim_id", as_index=False)
            .agg(
                denial_count=("is_denial", "sum"),
                carc_codes=("CARC", _unique_codes),
                rarc_codes=("RARC", _unique_codes),
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
        "remittance_count": 0,
        "paid_amount": 0.0,
        "denial_count": 0,
        "carc_codes": "",
        "rarc_codes": "",
        "ack_999_status": "",
        "ack_277ca_status": "",
    }
    for column, default in defaults.items():
        if column not in claim_status:
            claim_status[column] = default
        claim_status[column] = claim_status[column].fillna(default)

    claim_status["has_999_ack"] = claim_status["ack_999_status"].astype(bool)
    claim_status["has_277ca_ack"] = claim_status["ack_277ca_status"].astype(bool)
    claim_status["has_835_remit"] = claim_status["remittance_count"].astype(int) > 0

    def workflow_status(row: pd.Series) -> str:
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
    return claim_status


def main(warehouse: Path):
    norm = warehouse / "normalized"
    claims = load_jsonl_dir(norm / "claims_header")
    lines  = load_jsonl_dir(norm / "claims_line")
    adjud  = load_jsonl_dir(norm / "adjudication")
    pays   = load_jsonl_dir(norm / "payments")
    acks   = load_jsonl_dir(norm / "acknowledgments")

    # Simple KPIs for demo
    if lines.empty:
        print("No normalized lines found; did you run ingest_edi.py?")
        return

    denial_count = 0
    if not adjud.empty and "status" in adjud:
        denial_count = int((adjud["status"].str.lower() != "paid").sum())

    total_claim_lines = int(lines["line_no"].count())
    claim_status = build_claim_status_mart(claims, lines, adjud, pays, acks)
    total_claims = int(claims["claim_id"].nunique()) if not claims.empty else 0
    ack_complete = int((claim_status["has_999_ack"] & claim_status["has_277ca_ack"]).sum()) if not claim_status.empty else 0
    clean_claims = int(
        (
            (claim_status["denial_count"].astype(int) == 0)
            & (claim_status["has_999_ack"])
            & (claim_status["has_277ca_ack"])
        ).sum()
    ) if not claim_status.empty else 0
    kpi = pd.DataFrame([{
        "total_claims": total_claims,
        "total_claim_lines": total_claim_lines,
        "total_billed": float(lines["billed"].sum()),
        "total_allowed": float(lines["allowed"].sum()),
        "total_paid": float(lines["paid"].sum()),
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
