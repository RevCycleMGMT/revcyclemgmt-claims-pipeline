# Stub adapter for pyx12-based translation.
# Replace `parse_x12_to_dicts` with real logic once pyx12 is installed.

from typing import Dict, List


def _empty_payload() -> Dict[str, List[dict]]:
    return {
        "claims_header": [],
        "claims_line": [],
        "adjudication": [],
        "payments": [],
        "acknowledgments": [],
    }

def parse_x12_to_dicts(x12_text: str) -> Dict[str, List[dict]]:
    """Return canonical demo dicts without PHI or production claim data."""
    payload = _empty_payload()

    if "ST*837" in x12_text:
        payload["claims_header"].append({
            "claim_id": "CLM-DEMO-001",
            "member_id": "MEM-DEMO-001",
            "payer": "ACME_PAYER",
            "claim_type": "837P",
            "dos_from": "2024-06-01",
            "dos_to": "2024-06-01",
            "place_of_service": "11",
            "billed_amt": 250.00,
            "rendering_provider_npi": "1234567890"
        })
        payload["claims_line"].extend([
            {"claim_id":"CLM-DEMO-001","line_no":1,"hcpcs_cpt":"99213","units":1,"billed":150.00,"allowed":120.00,"paid":96.00,"patient_resp":24.00},
            {"claim_id":"CLM-DEMO-001","line_no":2,"hcpcs_cpt":"99050","units":1,"billed":100.00,"allowed":80.00,"paid":64.00,"patient_resp":16.00}
        ])

    if "ST*835" in x12_text:
        payload["adjudication"].extend([
            {"claim_id":"CLM-DEMO-001","line_no":1,"CARC":"45","RARC":"","group_code":"CO","remark_text":"Charge exceeds fee schedule","status":"Paid"},
            {"claim_id":"CLM-DEMO-001","line_no":2,"CARC":"45","RARC":"","group_code":"CO","remark_text":"Charge exceeds fee schedule","status":"Paid"}
        ])
        payload["payments"].append(
            {"claim_id":"CLM-DEMO-001","check_eft_no":"EFT123","payer":"ACME_PAYER","amount":160.00,"post_date":"2024-06-15","trace_no":"TRACE123"}
        )

    if "ST*999" in x12_text:
        payload["acknowledgments"].append({
            "claim_id": "CLM-DEMO-001",
            "ack_type": "999",
            "status": "Accepted",
            "received_at": "2024-07-01T12:01:00Z",
            "control_number": "000000907",
        })

    if "ST*277" in x12_text:
        payload["acknowledgments"].append({
            "claim_id": "CLM-DEMO-001",
            "ack_type": "277CA",
            "status": "Accepted",
            "received_at": "2024-07-01T12:03:00Z",
            "control_number": "000000908",
        })

    return payload
