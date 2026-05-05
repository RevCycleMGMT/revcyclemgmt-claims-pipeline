# Operational Safeguards And PHI Boundary

This repository is a synthetic technical scaffold for revenue cycle claims workflows. It is not a compliance product, legal opinion, clearinghouse certification, or payer certification.

The public demo is limited to claims workflow controls:

- 837 claim file intake.
- 999 and 277CA-style acknowledgment visibility.
- 835 remittance and payment reconciliation.
- CARC/RARC denial pattern capture.
- Traceable raw-to-normalized records.
- Dashboard-ready RCM metrics.

Production use in a U.S. healthcare environment requires a formal security, privacy, legal, and operational review. Typical controls include:

- BAAs with applicable processors, vendors, hosting providers, monitoring providers, and clearinghouse partners.
- Minimum necessary data handling.
- TLS for data in transit and encryption at rest.
- Role-based access control, audit trails, short-lived credentials, and periodic access reviews.
- Payer and clearinghouse companion-guide validation.
- Retention and destruction policies for raw X12 files, staging files, logs, and exports.
- Incident response runbooks for acknowledgment failure, duplicate submission, rejected files, data leakage, and vendor outage.
- PHI-safe logging. Do not log raw X12 segment values, identifiers, member demographics, or production claim details.

Never commit PHI, real patient records, real payer files, real clearinghouse files, real credentials, or raw production EDI to this repository.
