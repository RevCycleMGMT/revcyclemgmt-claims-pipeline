from pathlib import Path

import pandas as pd

from revcyclemgmt_claims.parsers.x12_pyx12_adapter import parse_x12_to_dicts
from revcyclemgmt_claims.pipelines.build_marts import main as build_marts_main
from revcyclemgmt_claims.pipelines.ingest_edi import main as ingest_main


def test_parser_recognizes_claim_remit_and_ack_files():
    claim = parse_x12_to_dicts("ST*837*0001~")
    remit = parse_x12_to_dicts("ST*835*0001~")
    ack_999 = parse_x12_to_dicts("ST*999*0001~")
    ack_277ca = parse_x12_to_dicts("ST*277*0001~")

    assert claim["claims_header"][0]["claim_id"] == "CLM-DEMO-001"
    assert remit["payments"][0]["amount"] == 160.00
    assert ack_999["acknowledgments"][0]["ack_type"] == "999"
    assert ack_277ca["acknowledgments"][0]["ack_type"] == "277CA"


def test_demo_pipeline_builds_rcm_kpi_mart(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    inbox = repo_root / "tests" / "sample_data"
    warehouse = tmp_path / "warehouse"

    ingest_main(inbox, warehouse)
    build_marts_main(warehouse)

    kpi_path = warehouse / "marts" / "rcm" / "kpi_daily.parquet"
    assert kpi_path.exists()

    kpi = pd.read_parquet(kpi_path)
    row = kpi.iloc[0].to_dict()
    assert row["total_claims"] == 1
    assert row["total_claim_lines"] == 2
    assert row["remittance_count"] == 1
    assert row["ack_999_count"] == 1
    assert row["ack_277ca_count"] == 1
    assert row["ack_completion_rate"] == 1.0
    assert row["clean_claim_rate"] == 1.0
    assert row["claims_paid_or_posted"] == 1

    claim_status_path = warehouse / "marts" / "rcm" / "claim_status.parquet"
    assert claim_status_path.exists()

    claim_status = pd.read_parquet(claim_status_path)
    claim_row = claim_status.iloc[0].to_dict()
    assert claim_row["claim_id"] == "CLM-DEMO-001"
    assert bool(claim_row["has_999_ack"]) is True
    assert bool(claim_row["has_277ca_ack"]) is True
    assert bool(claim_row["has_835_remit"]) is True
    assert claim_row["workflow_status"] == "paid_or_posted"
