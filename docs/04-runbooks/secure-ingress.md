# Secure Claim Data Ingress Runbook

This runbook documents safe intake patterns for RevCycleMGMT claim workflow demos and production planning. The public repository uses synthetic files only. Production PHI or payer data requires a separate approved environment, signed agreements, access controls, retention policy, and logging policy.

## Approved Demo Data

- Synthetic X12-style 837, 835, 999, and 277CA files.
- Synthetic FHIR or HL7 examples with fake identifiers only.
- Synthetic claim extracts built for dashboard testing.

Never place real patient records, payer files, clearinghouse files, credentials, app passwords, certificates, or private keys in this repository.

## Intake Options

| Method | Use when | Minimum controls |
| --- | --- | --- |
| SFTP | A billing team exports scheduled claim files. | Unique account per source, chroot or folder restriction, SSH key rotation, no password reuse, upload-only or read-only permissions as appropriate. |
| AWS S3 | A source system can drop files in a customer-owned bucket. | TLS, bucket encryption, read-only IAM role for RevCycleMGMT, short-lived role assumption where possible, object-level logging. |
| Azure Blob | A Microsoft-based environment owns the data lake. | TLS, storage encryption, scoped SAS or managed identity, container-level access review, diagnostic logs. |
| BigQuery external table | The customer wants query-in-place without copying files. | Dedicated service account, read-only dataset/table access, audit logs, no broad project-owner grants. |

## Claim Workflow Intake Checklist

- [ ] Data class confirmed: synthetic demo, de-identified test data, or live PHI-bearing data.
- [ ] PHI approval path documented before any production file is accepted.
- [ ] Ingress method selected: SFTP, S3, Azure Blob, BigQuery, AS2, or clearinghouse API.
- [ ] Source owner and RevCycleMGMT owner assigned.
- [ ] Expected transaction types documented: 837P, 837I, 835, 999, 277CA, 270/271, or 276/277.
- [ ] Expected payer and clearinghouse routing documented.
- [ ] Companion-guide requirements captured for each trading partner.
- [ ] Encryption in transit enabled.
- [ ] Encryption at rest enabled.
- [ ] Access logging enabled.
- [ ] Retention and deletion window approved.
- [ ] File naming convention approved.
- [ ] Duplicate-file handling defined.
- [ ] Rejected-file handling defined.
- [ ] Missing 999/277CA alert path defined.
- [ ] Missing 835/remittance alert path defined.

## Evidence Artifacts

Every onboarding should produce a small evidence bundle:

- Ingress checklist.
- Source-to-target mapping.
- Sample file manifest.
- Validation report.
- Run log.
- Known exceptions.
- Access-review record.

Templates live in `docs/04-runbooks/evidence-templates/`.

## Production Boundary

The demo pipeline proves the operating model. It is not a live clearinghouse connection, not payer certification, and not a claim submission service by itself. Production deployment requires payer and clearinghouse validation, formal security review, monitoring, and business approval.
