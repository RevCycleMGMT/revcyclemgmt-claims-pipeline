from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .hl7_pid import mask_patient_context


def _patients_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and payload.get("resourceType") == "Patient":
        return [payload]

    if isinstance(payload, dict) and payload.get("resourceType") == "Bundle":
        patients: list[dict[str, Any]] = []
        for entry in payload.get("entry", []):
            resource = entry.get("resource", {}) if isinstance(entry, dict) else {}
            if resource.get("resourceType") == "Patient":
                patients.append(resource)
        return patients

    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict) and item.get("resourceType") == "Patient"]

    return []


def _first_identifier(patient: dict[str, Any]) -> tuple[str, str, str]:
    for identifier in patient.get("identifier", []) or []:
        if not isinstance(identifier, dict):
            continue
        value = str(identifier.get("value", "")).strip()
        if value:
            return value, str(identifier.get("system", "")).strip(), str(identifier.get("type", {}).get("text", "")).strip()
    return "", "", ""


def _first_name(patient: dict[str, Any]) -> tuple[str, str, str]:
    for name in patient.get("name", []) or []:
        if not isinstance(name, dict):
            continue
        family = str(name.get("family", "")).strip()
        given = [str(part).strip() for part in name.get("given", []) if str(part).strip()]
        return family, given[0] if given else "", given[1] if len(given) > 1 else ""
    return "", "", ""


def _first_address(patient: dict[str, Any]) -> tuple[str, str, str, str, str]:
    for address in patient.get("address", []) or []:
        if not isinstance(address, dict):
            continue
        lines = [str(line).strip() for line in address.get("line", []) if str(line).strip()]
        return (
            lines[0] if lines else "",
            str(address.get("city", "")).strip(),
            str(address.get("state", "")).strip(),
            str(address.get("postalCode", "")).strip(),
            str(address.get("country", "")).strip(),
        )
    return "", "", "", "", ""


def _first_phone(patient: dict[str, Any]) -> str:
    for telecom in patient.get("telecom", []) or []:
        if isinstance(telecom, dict) and telecom.get("system") == "phone" and telecom.get("value"):
            return str(telecom["value"]).strip()
    return ""


def parse_fhir_patient(patient: dict[str, Any]) -> dict[str, Any]:
    """Flatten a synthetic FHIR Patient into the same claim-prep shape as HL7 PID."""
    identifier, authority, identifier_type = _first_identifier(patient)
    last_name, first_name, middle_name = _first_name(patient)
    address_line_1, city, state, postal_code, country = _first_address(patient)
    return {
        "patient_identifier": identifier,
        "identifier_authority": authority,
        "identifier_type": identifier_type,
        "last_name": last_name,
        "first_name": first_name,
        "middle_name": middle_name,
        "date_of_birth": str(patient.get("birthDate", "")).strip(),
        "administrative_sex": str(patient.get("gender", "")).strip(),
        "address_line_1": address_line_1,
        "city": city,
        "state": state,
        "postal_code": postal_code,
        "country": country,
        "phone": _first_phone(patient),
        "patient_account_number": str(patient.get("id", "")).strip(),
    }


def parse_fhir_patient_records(payload: str | dict[str, Any] | list[Any], *, mask: bool = True, salt: str = "revcyclemgmt-demo") -> list[dict[str, Any]]:
    """Parse synthetic FHIR Patient resources, masked by default."""
    parsed_payload: Any = json.loads(payload) if isinstance(payload, str) else payload
    records = [parse_fhir_patient(patient) for patient in _patients_from_payload(parsed_payload)]
    records = [record for record in records if record]
    if not mask:
        return records
    return [mask_patient_context(record, salt=salt) for record in records]


def parse_fhir_patient_file(path: str | Path, *, mask: bool = True, salt: str = "revcyclemgmt-demo") -> list[dict[str, Any]]:
    """Parse synthetic FHIR Patient resources from a JSON file."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_fhir_patient_records(payload, mask=mask, salt=salt)
