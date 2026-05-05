# Clinical-To-Claim Interoperability Bridge

RevCycleMGMT does not turn the public portfolio into a broad clinical analytics product. The interoperability layer exists only to help a billing team prepare cleaner claim workflows.

## Purpose

Clinical and practice-management systems may export claim-prep context through FHIR, HL7 v2, CSV, or flat files. RevCycleMGMT uses that context to support:

- Claim readiness checks before 837 generation.
- Missing demographic or account context flags.
- Routing context for professional, institutional, or dental claims.
- Better handoff from EHR/PM systems into clearinghouse submission.
- Safer traceability between source events and downstream claim status.

## Current Public Demo

The repository includes dependency-free synthetic helpers:

- `src/revcyclemgmt_claims/interoperability/hl7_pid.py`
- `src/revcyclemgmt_claims/interoperability/fhir_patient.py`

By default, it returns masked claim-prep context instead of raw patient identifiers. That keeps demos and logs focused on operational completeness rather than patient details.

## Production Boundary

Real HL7, FHIR, EHR exports, or practice-management exports can contain PHI. Production intake requires:

- Approved environment.
- Signed agreements where applicable.
- Role-based access controls.
- PHI-safe logging.
- Retention and deletion rules.
- Source-system mapping review.
- Payer and clearinghouse companion-guide review.

The public repository remains synthetic and does not store production patient data.
