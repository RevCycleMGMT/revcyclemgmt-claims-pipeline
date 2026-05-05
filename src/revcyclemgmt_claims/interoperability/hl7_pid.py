from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def split_hl7_messages(raw_text: str) -> list[str]:
    """Split HL7 text into messages that start with MSH and contain PID."""
    normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    messages: list[str] = []
    buffer: list[str] = []

    for line in normalized.splitlines():
        if line.startswith("MSH|") and buffer:
            candidate = "\r".join(buffer)
            if "\rPID|" in candidate or candidate.startswith("PID|") or "\nPID|" in candidate:
                messages.append(candidate)
            buffer = [line]
        elif line.strip():
            buffer.append(line)

    if buffer:
        candidate = "\r".join(buffer)
        if "\rPID|" in candidate or candidate.startswith("PID|") or "\nPID|" in candidate:
            messages.append(candidate)

    return messages


def _component(value: str, index: int) -> str:
    parts = value.split("^")
    return parts[index].strip() if len(parts) > index else ""


def _first_repeat(value: str) -> str:
    return value.split("~", 1)[0].strip()


def parse_hl7_pid(message_text: str) -> dict[str, Any]:
    """
    Parse the PID segment from a synthetic HL7 v2 message.

    The returned values can be direct identifiers if the input is real. Keep this
    helper inside approved environments and use `mask_patient_context` before
    logs, demos, or public artifacts.
    """
    normalized = message_text.replace("\r\n", "\n").replace("\r", "\n")
    pid_line = next((line for line in normalized.splitlines() if line.startswith("PID|")), "")
    if not pid_line:
        return {}

    fields = pid_line.split("|")

    def field(position: int) -> str:
        return fields[position] if len(fields) > position else ""

    identifier = _first_repeat(field(3))
    name = _first_repeat(field(5))
    address = _first_repeat(field(11))
    phone = _first_repeat(field(13))
    account_number = _first_repeat(field(18))

    return {
        "patient_identifier": _component(identifier, 0),
        "identifier_authority": _component(identifier, 3),
        "identifier_type": _component(identifier, 4),
        "last_name": _component(name, 0),
        "first_name": _component(name, 1),
        "middle_name": _component(name, 2),
        "date_of_birth": field(7).strip(),
        "administrative_sex": field(8).strip(),
        "address_line_1": _component(address, 0),
        "city": _component(address, 2),
        "state": _component(address, 3),
        "postal_code": _component(address, 4),
        "country": _component(address, 5),
        "phone": _component(phone, 0),
        "patient_account_number": _component(account_number, 0),
    }


def mask_patient_context(record: dict[str, Any], salt: str = "revcyclemgmt-demo") -> dict[str, Any]:
    """
    Return a log-safe claim-prep context record.

    Direct identifiers are removed. The hash is deterministic for a given salt so
    synthetic events can still be linked across demo files.
    """
    identifier = "|".join(
        str(record.get(key, ""))
        for key in ("patient_identifier", "patient_account_number", "date_of_birth")
    )
    digest = hashlib.sha256(f"{salt}|{identifier}".encode("utf-8")).hexdigest()[:16]
    return {
        "patient_context_hash": digest,
        "identifier_type": record.get("identifier_type", ""),
        "identifier_authority": record.get("identifier_authority", ""),
        "administrative_sex_present": bool(record.get("administrative_sex")),
        "date_of_birth_present": bool(record.get("date_of_birth")),
        "address_present": bool(record.get("postal_code") or record.get("state")),
        "phone_present": bool(record.get("phone")),
        "patient_account_present": bool(record.get("patient_account_number")),
    }


def parse_hl7_pid_records(raw_text: str, *, mask: bool = True, salt: str = "revcyclemgmt-demo") -> list[dict[str, Any]]:
    """Parse all PID records in a text block, masked by default."""
    records = [parse_hl7_pid(message) for message in split_hl7_messages(raw_text)]
    records = [record for record in records if record]
    if not mask:
        return records
    return [mask_patient_context(record, salt=salt) for record in records]


def parse_hl7_pid_file(path: str | Path, *, mask: bool = True, salt: str = "revcyclemgmt-demo") -> list[dict[str, Any]]:
    """Parse PID records from a local synthetic HL7 file."""
    raw_text = Path(path).read_text(encoding="utf-8", errors="ignore")
    return parse_hl7_pid_records(raw_text, mask=mask, salt=salt)
