from pathlib import Path

import pandas as pd

from revcyclemgmt_claims.interoperability.fhir_patient import parse_fhir_patient_records
from revcyclemgmt_claims.interoperability.hl7_pid import parse_hl7_pid_records
from revcyclemgmt_claims.parsers.x12_pyx12_adapter import parse_x12_to_dicts
from revcyclemgmt_claims.pipelines.build_marts import build_claim_status_mart
from revcyclemgmt_claims.pipelines.build_marts import main as build_marts_main
from revcyclemgmt_claims.pipelines.ingest_edi import main as ingest_main
from revcyclemgmt_claims.pipelines.proof_artifacts import run as proof_artifacts_run


def test_parser_recognizes_claim_remit_and_ack_files():
    sample_dir = Path(__file__).resolve().parent / "sample_data"
    claim = parse_x12_to_dicts((sample_dir / "demo_837p.txt").read_text())
    remit = parse_x12_to_dicts((sample_dir / "demo_835.txt").read_text())
    ack_999 = parse_x12_to_dicts((sample_dir / "demo_999.txt").read_text())
    ack_277ca = parse_x12_to_dicts((sample_dir / "demo_277ca.txt").read_text())

    assert [row["claim_id"] for row in claim["claims_header"]] == [
        "CLM-LAUNCH-001",
        "CLM-LAUNCH-002",
        "CLM-LAUNCH-003",
    ]
    assert len(claim["claims_line"]) == 4
    assert remit["payments"][0]["amount"] == 148.00
    assert remit["payments"][1]["amount"] == 0.00
    assert ack_999["acknowledgments"][0]["ack_type"] == "999"
    assert ack_277ca["acknowledgments"][0]["ack_type"] == "277CA"
    assert ack_277ca["acknowledgments"][1]["status"] == "Rejected"


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
    assert row["total_claims"] == 3
    assert row["total_claim_lines"] == 4
    assert row["remittance_count"] == 2
    assert row["ack_999_count"] == 3
    assert row["ack_277ca_count"] == 3
    assert row["ack_completion_rate"] == 1.0
    assert round(row["clean_claim_rate"], 2) == 0.33
    assert row["claims_paid_or_posted"] == 1
    assert row["claims_clearinghouse_rejected"] == 1
    assert row["claims_denied_follow_up"] == 1
    assert row["claims_missing_ack"] == 0
    assert row["claims_needing_workqueue_review"] == 2
    assert row["payment_variance_total"] == 300.0

    claim_status_path = warehouse / "marts" / "rcm" / "claim_status.parquet"
    assert claim_status_path.exists()

    claim_status = pd.read_parquet(claim_status_path)
    by_claim = {row["claim_id"]: row for row in claim_status.to_dict("records")}

    clean = by_claim["CLM-LAUNCH-001"]
    assert bool(clean["has_999_ack"]) is True
    assert bool(clean["has_277ca_ack"]) is True
    assert bool(clean["has_835_remit"]) is True
    assert clean["payment_variance"] == 0.0
    assert clean["workflow_status"] == "paid_or_posted"
    assert bool(clean["needs_workqueue_review"]) is False

    rejected = by_claim["CLM-LAUNCH-002"]
    assert rejected["ack_277ca_status"] == "Rejected"
    assert rejected["workflow_status"] == "clearinghouse_rejected"
    assert bool(rejected["needs_workqueue_review"]) is True

    denied = by_claim["CLM-LAUNCH-003"]
    assert denied["root_cause_groups"] == "Info Missing"
    assert denied["carc_codes"] == "16"
    assert denied["payment_variance"] == 300.0
    assert denied["workflow_status"] == "denied_follow_up"
    assert bool(denied["needs_workqueue_review"]) is True


def test_demo_pipeline_builds_public_proof_artifacts(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    inbox = repo_root / "tests" / "sample_data"
    warehouse = tmp_path / "warehouse"
    output_dir = tmp_path / "output_demo"

    ingest_main(inbox, warehouse)
    build_marts_main(warehouse)
    result = proof_artifacts_run(warehouse, output_dir)

    assert result["total_claims"] == 3
    assert result["workqueue"] == 2
    assert result["artifact_count"] == 2

    summary_path = output_dir / "claims_pipeline_summary.json"
    svg_path = output_dir / "claims_pipeline_map.svg"
    assert summary_path.exists()
    assert svg_path.exists()

    svg = svg_path.read_text(encoding="utf-8")
    assert "837P to payment visibility" in svg
    assert "CLM-LAUNCH-002" in svg
    assert "277CA rejection" in svg
    assert "without public PHI" in svg


def test_claim_status_mart_flags_denials_and_missing_acks():
    claims = pd.DataFrame(
        [
            {
                "claim_id": "CLM-DENIED-001",
                "payer": "ACME_PAYER",
                "claim_type": "837P",
                "billed_amt": 300.0,
            }
        ]
    )
    lines = pd.DataFrame(
        [
            {
                "claim_id": "CLM-DENIED-001",
                "line_no": 1,
                "billed": 300.0,
                "allowed": 180.0,
                "paid": 0.0,
            }
        ]
    )
    adjud = pd.DataFrame(
        [
            {
                "claim_id": "CLM-DENIED-001",
                "line_no": 1,
                "CARC": "16",
                "RARC": "M51",
                "status": "Denied",
            }
        ]
    )
    pays = pd.DataFrame()
    acks = pd.DataFrame(
        [
            {
                "claim_id": "CLM-DENIED-001",
                "ack_type": "999",
                "status": "Accepted",
            }
        ]
    )

    mart = build_claim_status_mart(
        claims,
        lines,
        adjud,
        pays,
        acks,
        {"16": "Info Missing"},
    )
    row = mart.iloc[0].to_dict()
    assert row["workflow_status"] == "denied_follow_up"
    assert row["root_cause_groups"] == "Info Missing"
    assert row["carc_codes"] == "16"
    assert row["rarc_codes"] == "M51"
    assert row["payment_variance"] == 180.0
    assert bool(row["has_999_ack"]) is True
    assert bool(row["has_277ca_ack"]) is False
    assert bool(row["needs_workqueue_review"]) is True


def test_hl7_pid_records_are_masked_by_default():
    raw = (
        "MSH|^~\\&|EHR|DEMO|RCM|DEST|20260505000000||ADT^A04|MSG1|P|2.5.1\r"
        "PID|1||MRN123^^^DEMO^MR||DOE^JANE^Q||19800101|F|||1 MAIN ST^^LOMA LINDA^CA^92354^US||5551112222|||||ACCT123\r"
    )

    records = parse_hl7_pid_records(raw, salt="test")

    assert len(records) == 1
    record = records[0]
    assert "patient_context_hash" in record
    assert "MRN123" not in str(record)
    assert "DOE" not in str(record)
    assert record["patient_account_present"] is True
    assert record["date_of_birth_present"] is True


def test_fhir_patient_records_are_masked_by_default():
    payload = {
        "resourceType": "Bundle",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "acct-001",
                    "identifier": [{"system": "demo-mrn", "value": "MRN999", "type": {"text": "MR"}}],
                    "name": [{"family": "Doe", "given": ["John"]}],
                    "birthDate": "1980-02-03",
                    "gender": "male",
                    "telecom": [{"system": "phone", "value": "555-111-2222"}],
                    "address": [{"line": ["1 Main"], "city": "Loma Linda", "state": "CA", "postalCode": "92354"}],
                }
            }
        ],
    }

    records = parse_fhir_patient_records(payload, salt="test")

    assert len(records) == 1
    record = records[0]
    assert "patient_context_hash" in record
    assert "MRN999" not in str(record)
    assert "Doe" not in str(record)
    assert record["patient_account_present"] is True
    assert record["address_present"] is True
