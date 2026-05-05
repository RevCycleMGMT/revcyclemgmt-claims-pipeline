import argparse
from pathlib import Path
import json
from datetime import UTC, datetime

# Choose one adapter implementation; both stubs produce demo rows.
from revcyclemgmt_claims.parsers.x12_pyx12_adapter import parse_x12_to_dicts
from revcyclemgmt_claims.pipelines.utils import ensure_dir, lineage_hash, write_json_lines

def process_file(p: Path):
    data = parse_x12_to_dicts(p.read_text())
    # Decorate with lineage hashes
    for row in data["claims_header"]:
        row["_hash"] = lineage_hash(row, ["claim_id","member_id","payer"])
    for row in data["claims_line"]:
        row["_hash"] = lineage_hash(row, ["claim_id","line_no","hcpcs_cpt","billed"])
    for row in data["adjudication"]:
        row["_hash"] = lineage_hash(row, ["claim_id","line_no","CARC","status"])
    for row in data["payments"]:
        row["_hash"] = lineage_hash(row, ["claim_id","check_eft_no","amount"])
    for row in data["acknowledgments"]:
        row["_hash"] = lineage_hash(row, ["claim_id","ack_type","status","control_number"])
    return data

def main(inbox: Path, warehouse: Path):
    raw_dir = warehouse / "raw"
    norm_dir = warehouse / "normalized"
    ensure_dir(raw_dir); ensure_dir(norm_dir)
    files = list(inbox.glob("*.txt"))
    if not files:
        print(f"No .txt EDI files found in {inbox}. Using demo placeholders.")
        files = [inbox / "demo_837p.txt", inbox / "demo_835.txt"]
        for f in files:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("ISA*00*          *00*          *ZZ*DEMO        *ZZ*DEMO        *240701*1200*^*00501*000000905*0*T*:~\nST*837*0001~SE*2*0001~IEA*1*000000905~")

    for f in files:
        text = f.read_text()
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        (raw_dir / f"{f.stem}_{ts}.x12").write_text(text)

        parsed = process_file(f)
        for k, rows in parsed.items():
            out = norm_dir / k / f"{f.stem}_{ts}.jsonl"
            if rows:
                write_json_lines(out, rows)
                print(f"Wrote {len(rows)} rows -> {out}")
            else:
                print(f"Skipped {k} for {f.name}: 0 rows")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--inbox", type=Path, default=Path("tests/sample_data"))
    ap.add_argument("--warehouse", type=Path, default=Path("warehouse"))
    args = ap.parse_args()
    main(args.inbox, args.warehouse)
