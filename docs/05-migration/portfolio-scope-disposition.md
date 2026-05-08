# Portfolio Scope Disposition

This repository consolidates the public RevCycleMGMT claims-pipeline portfolio around one clear business line: revenue cycle management claims automation.

## Included

The repository includes assets that support:

- EDI/X12 claim workflow automation.
- 837 claim intake and validation.
- 999 and 277CA acknowledgment monitoring.
- 835 remittance and payment reconciliation.
- CARC/RARC denial grouping.
- Claim status and workqueue visibility.
- Secure file ingress planning.
- Synthetic HL7/FHIR claim-prep context where it supports cleaner billing handoff.
- Evidence templates for implementation readiness.

## Deferred

These areas are useful, but they should be handled in separate workstreams or separate repositories:

- RSS/NLP website content automation.
- Cloud infrastructure operations beyond this claims demo.
- Broader compliance monitoring not tied to claim submission, remittance, denial, or clearinghouse workflow.

## Excluded

These areas are not part of the RevCycleMGMT claims-pipeline portfolio:

- General quality-measure products.
- Population health analytics.
- Member engagement analytics.
- Government contracting and PMO positioning.
- Any live PHI-bearing data, payer credentials, clearinghouse credentials, app passwords, private keys, or certificates.

## Public Link Rule

RevCycleMGMT website cards should link to RevCycleMGMT-branded repositories and pages. Legacy source repositories should not be used as public portfolio destinations after the relevant work has been rewritten into this repository.
