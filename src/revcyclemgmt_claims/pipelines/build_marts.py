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
    kpi = pd.DataFrame([{
        "total_claims": int(claims["claim_id"].nunique()) if not claims.empty else 0,
        "total_claim_lines": total_claim_lines,
        "total_billed": float(lines["billed"].sum()),
        "total_allowed": float(lines["allowed"].sum()),
        "total_paid": float(lines["paid"].sum()),
        "remittance_count": int(len(pays)),
        "ack_999_count": int((acks["ack_type"] == "999").sum()) if not acks.empty else 0,
        "ack_277ca_count": int((acks["ack_type"] == "277CA").sum()) if not acks.empty else 0,
        "denial_count": denial_count,
        "denial_rate": denial_count / total_claim_lines if total_claim_lines else 0.0,
    }])
    out_dir = warehouse / "marts" / "rcm"
    out_dir.mkdir(parents=True, exist_ok=True)
    kpi_path = out_dir / "kpi_daily.parquet"
    kpi.to_parquet(kpi_path, index=False)
    print(f"Wrote {kpi_path}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--warehouse", type=Path, default=Path("warehouse"))
    args = ap.parse_args()
    main(args.warehouse)
