# Lightweight synthetic X12-style adapter.
#
# This is intentionally not a production X12 translator. It extracts a small,
# deterministic demo shape from synthetic fixtures so the public portfolio can
# prove the claims-to-payment workflow without PHI, payer files, or clearinghouse
# credentials. Production implementations should replace this with a validated
# X12 translator and payer/clearinghouse companion-guide rules.

from typing import Dict, List


def _empty_payload() -> Dict[str, List[dict]]:
    return {
        "claims_header": [],
        "claims_line": [],
        "adjudication": [],
        "payments": [],
        "acknowledgments": [],
    }


def _segments(x12_text: str) -> list[list[str]]:
    return [
        [part.strip() for part in segment.strip().split("*")]
        for segment in x12_text.replace("\n", "").replace("\r", "").split("~")
        if segment.strip()
    ]


def _money(value: str) -> float:
    try:
        return round(float(value or 0), 2)
    except ValueError:
        return 0.0


def _int(value: str, default: int = 0) -> int:
    try:
        return int(float(value or default))
    except ValueError:
        return default


def _hcpcs(composite: str) -> str:
    parts = composite.split(":")
    return parts[1].strip() if len(parts) > 1 else composite.strip()


def _fallback_demo_payload(x12_text: str) -> Dict[str, List[dict]]:
    """Return the original one-claim demo payload for tiny legacy fixtures."""
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
            {"claim_id":"CLM-DEMO-001","line_no":1,"CARC":"45","RARC":"","group_code":"CO","remark_text":"Charge exceeds fee schedule","status":"Paid","allowed":120.00,"paid":96.00,"patient_resp":24.00},
            {"claim_id":"CLM-DEMO-001","line_no":2,"CARC":"45","RARC":"","group_code":"CO","remark_text":"Charge exceeds fee schedule","status":"Paid","allowed":80.00,"paid":64.00,"patient_resp":16.00}
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


def parse_x12_to_dicts(x12_text: str) -> Dict[str, List[dict]]:
    """Return canonical synthetic dicts without PHI or production claim data."""
    payload = _empty_payload()
    segments = _segments(x12_text)

    current_transaction = ""
    current_payer = "SYNTHETIC_PAYER"
    current_claim = ""
    line_no = 0
    current_clp: dict | None = None
    last_adjudication: dict | None = None

    for segment in segments:
        tag = segment[0] if segment else ""

        if tag == "ST" and len(segment) > 1:
            current_transaction = segment[1]
            current_claim = ""
            line_no = 0
            continue

        if tag == "NM1" and len(segment) > 3 and segment[1] == "PR":
            current_payer = segment[3] or current_payer
            continue

        if current_transaction.startswith("837") and tag == "CLM" and len(segment) > 2:
            current_claim = segment[1]
            line_no = 0
            payload["claims_header"].append({
                "claim_id": current_claim,
                "member_id": f"MEM-{current_claim.rsplit('-', 1)[-1]}",
                "payer": current_payer,
                "claim_type": "837P" if current_transaction == "837" else current_transaction,
                "dos_from": "2026-05-01",
                "dos_to": "2026-05-01",
                "place_of_service": "11",
                "billed_amt": _money(segment[2]),
                "rendering_provider_npi": "1999999999",
            })
            continue

        if current_transaction.startswith("837") and tag == "SV1" and current_claim and len(segment) > 2:
            line_no += 1
            payload["claims_line"].append({
                "claim_id": current_claim,
                "line_no": line_no,
                "hcpcs_cpt": _hcpcs(segment[1]),
                "units": _int(segment[4], 1) if len(segment) > 4 else 1,
                "billed": _money(segment[2]),
                "allowed": 0.0,
                "paid": 0.0,
                "patient_resp": 0.0,
            })
            continue

        if current_transaction == "835" and tag == "CLP" and len(segment) > 4:
            current_claim = segment[1]
            line_no = 0
            current_clp = {
                "claim_id": current_claim,
                "status_code": segment[2],
                "billed": _money(segment[3]),
                "paid": _money(segment[4]),
                "patient_resp": _money(segment[5]) if len(segment) > 5 else 0.0,
            }
            payload["payments"].append({
                "claim_id": current_claim,
                "check_eft_no": "EFT-LAUNCH-001",
                "payer": current_payer,
                "amount": current_clp["paid"],
                "post_date": "2026-05-15",
                "trace_no": f"TRACE-{current_claim}",
            })
            continue

        if current_transaction == "835" and tag == "SVC" and current_claim and current_clp and len(segment) > 3:
            line_no += 1
            paid = _money(segment[3])
            billed = _money(segment[2])
            status = "Paid" if paid > 0 and current_clp["status_code"] != "4" else "Denied"
            last_adjudication = {
                "claim_id": current_claim,
                "line_no": line_no,
                "CARC": "",
                "RARC": "",
                "group_code": "",
                "remark_text": "",
                "status": status,
                "allowed": paid + current_clp["patient_resp"] if status == "Paid" else billed,
                "paid": paid,
                "patient_resp": current_clp["patient_resp"] if line_no == 1 else 0.0,
            }
            payload["adjudication"].append(last_adjudication)
            continue

        if current_transaction == "835" and tag == "CAS" and last_adjudication and len(segment) > 3:
            last_adjudication["group_code"] = segment[1]
            last_adjudication["CARC"] = segment[2]
            last_adjudication["remark_text"] = f"CAS {segment[1]} {segment[2]} amount {_money(segment[3]):.2f}"
            continue

        # Demo-only claim-level ACK segment used by synthetic fixtures:
        # ACK*999*CLM-LAUNCH-001*Accepted*000000907~
        # ACK*277CA*CLM-LAUNCH-002*Rejected*000000908~
        if tag == "ACK" and len(segment) >= 4:
            payload["acknowledgments"].append({
                "claim_id": segment[2],
                "ack_type": segment[1],
                "status": segment[3],
                "received_at": "2026-05-10T12:00:00Z",
                "control_number": segment[4] if len(segment) > 4 else "",
            })

    if not any(payload.values()):
        return _fallback_demo_payload(x12_text)

    return payload
