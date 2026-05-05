from pathlib import Path

import pandas as pd

from revcyclemgmt_claims.interoperability.fhir_patient import parse_fhir_patient_records
from revcyclemgmt_claims.interoperability.hl7_pid import parse_hl7_pid_records
from revcyclemgmt_claims.parsers.x12_pyx12_adapter import parse_x12_to_dicts
from revcyclemgmt_claims.pipelines.build_marts import build_claim_status_mart
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
    assert row["claims_missing_ack"] == 0
    assert row["claims_needing_workqueue_review"] == 0
    assert row["payment_variance_total"] == 0.0

    claim_status_path = warehouse / "marts" / "rcm" / "claim_status.parquet"
    assert claim_status_path.exists()

    claim_status = pd.read_parquet(claim_status_path)
    claim_row = claim_status.iloc[0].to_dict()
    assert claim_row["claim_id"] == "CLM-DEMO-001"
    assert bool(claim_row["has_999_ack"]) is True
    assert bool(claim_row["has_277ca_ack"]) is True
    assert bool(claim_row["has_835_remit"]) is True
    assert claim_row["root_cause_groups"] == "Contractual Adjustment"
    assert claim_row["payment_variance"] == 0.0
    assert claim_row["workflow_status"] == "paid_or_posted"
    assert bool(claim_row["needs_workqueue_review"]) is False


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
