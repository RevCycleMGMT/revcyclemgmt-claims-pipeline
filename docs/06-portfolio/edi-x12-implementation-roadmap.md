# EDI/X12 Portfolio Implementation Roadmap

This roadmap turns the RevCycleMGMT portfolio into a connected set of public technical proof points. Each project should prove one part of a real claims-to-payment implementation without using PHI, payer credentials, clearinghouse credentials, or production transactions.

## Portfolio Standard

Every public project should include:

- Synthetic X12 fixtures.
- A one-command local demo.
- Tests that prove the transaction workflow works.
- Clear screenshots or sample output.
- `SECURITY.md` with no-PHI/no-secrets boundaries.
- Plain-English "What this proves" copy for executives.
- RevCycleMGMT-only naming, links, and contact language.

## Recommended Execution Order

| Order | Project | Why it matters | Public proof |
| ---: | --- | --- | --- |
| 1 | Claims Pipeline Anchor | Already connects 837, 999/277CA, 835, denials, payment variance, and dashboard output. | A complete synthetic claims journey from intake to payment visibility. |
| 2 | Acknowledgment Watcher | Buyers understand the pain of claims that were submitted but never clearly accepted, rejected, or pended. | 999 and 277CA parser, missing-ACK alert, payer-route aging table. |
| 3 | Remit 835 Reconciliation | Converts payment files into posting, adjustment, variance, and denial follow-up views. | 835 parser, paid/allowed/patient responsibility balancing, CARC/RARC grouping, variance export. |
| 4 | Eligibility 270/271 Cache | Prevents avoidable front-end denials before the 837 is built. | 270 request/271 response cache, freshness rules, payer-specific readiness flags. |
| 5 | Claim Status 276/277 Tracker | Gives teams a way to ask where a submitted claim stands after submission. | 276 request builder, 277 response normalizer, claim aging/status dashboard. |
| 6 | Payer Finder And Route Registry | Shows that payer routing and payer IDs are controlled, not tribal knowledge. | Payer search/cache, route profile, supported transaction flags, clearinghouse route selection. |
| 7 | EDI Validation Harness | Shows implementation discipline before any API or clearinghouse connection. | Golden test files, companion-guide rules, parser contract tests, rejection examples. |
| 8 | Attachment 275 Support | Useful for complex claims that need records, EOBs, charts, images, or other claim attachments. | Synthetic attachment metadata, trace ID tracking, status polling, no document PHI. |
| 9 | FHIR/HL7 Claim-Prep Bridge | Converts clinical/admin source messages into billing-ready fields. | Masked FHIR/HL7 demo records feeding claim-readiness checks. |
| 10 | RCM Dashboard | The executive-facing proof layer that reads outputs from the modules above. | Clean claim rate, ACK completion, missing remit, denial trends, payment variance, payer lag. |

## Optum API Engagement Posture

Optum's public API documentation is useful as an implementation reference because its Medical Network APIs describe the same transaction set RevCycleMGMT is positioning around:

- OAuth2 bearer-token authorization.
- X12 transactions translated to JSON for application integration.
- Eligibility API for X12 270/271.
- Professional Claims API for 837P and Institutional Claims API for 837I.
- Claim Status API for 276/277.
- Claim Responses and Reports API for payer reports and ERA-style mailbox retrieval.
- Payer Finder / payer list support.
- Sandbox access path for development.

Public website language should be careful:

- Say: "RevCycleMGMT designs workflows that can integrate with clearinghouse APIs such as Optum/Change Healthcare-style eligibility, claims, claim-status, payer-list, and remit-response endpoints."
- Say: "We build synthetic test harnesses before production onboarding."
- Do not say: "Certified Optum partner," "Optum-integrated," or "production Optum implementation" unless a signed relationship or tested production integration exists.
- Do not publish credentials, payer IDs from private contracts, client examples, or copied proprietary implementation details.

## Optum-Aligned Demo Projects

These projects map directly to the Optum-style API surface while staying vendor-neutral.

### 1. `revcyclemgmt-optum-style-sandbox-adapter`

Purpose: Show how a clearinghouse API adapter would be isolated from the core claims pipeline.

Scope:

- Local mock server for OAuth token issuance.
- Synthetic endpoints for eligibility, claim validation, claim submission, claim status, payer list, and mailbox reports.
- Adapter interface that converts between internal canonical rows and external JSON/X12 payloads.
- Contract tests that run without live Optum access.

Website card:

- Title: Clearinghouse API Adapter
- Copy: Demonstrates how RevCycleMGMT separates payer/clearinghouse API calls from the core claims workflow so integrations stay testable and replaceable.

### 2. `revcyclemgmt-payer-route-registry`

Purpose: Prove payer-route discipline.

Scope:

- Payer profile table.
- Clearinghouse route table.
- Supported transaction flags: 270/271, 837P, 837I, 276/277, 835, 275.
- Route selection rules.
- Payer ID validation examples.
- Change log for payer-route drift.

Website card:

- Title: Payer Route Registry
- Copy: Keeps payer IDs, transaction support, and clearinghouse route rules in one controlled place.

### 3. `revcyclemgmt-claim-status-tracker`

Purpose: Build a focused 276/277 proof.

Scope:

- Synthetic 276 request builder.
- Synthetic 277 response parser.
- Status normalizer: accepted, pending, denied, paid, in-process, not found.
- Aging report by payer and route.
- Link back to the original 837 claim.

Website card:

- Title: Claim Status Tracker
- Copy: Shows where submitted claims stand and which payers or routes are creating delays.

### 4. `revcyclemgmt-era-mailbox-monitor`

Purpose: Prove response and report retrieval.

Scope:

- Synthetic mailbox list.
- Report download simulation.
- 277 and 835 conversion examples.
- Idempotency rules so the same remit is not posted twice.
- Hashing and run logs for audit traceability.

Website card:

- Title: ERA Mailbox Monitor
- Copy: Retrieves payer responses, converts remit/status files, and feeds posting and follow-up queues.

### 5. `revcyclemgmt-edi-validation-harness`

Purpose: Show competence in EDI implementation without depending on live external systems.

Scope:

- Golden X12 samples for 837P, 837I, 835, 999, 277CA, 270/271, 276/277.
- Envelope/control-number checks.
- Required segment checks.
- Companion-guide override structure.
- Rejection fixtures and expected error output.

Website card:

- Title: EDI Validation Harness
- Copy: Tests X12 files before they touch a clearinghouse connection.

## Website Copy Guidance

Use concrete transaction names:

- 837 claim files.
- 999 implementation acknowledgments.
- 277CA claim acknowledgments.
- 835 remittance and ERA.
- 270/271 eligibility.
- 276/277 claim status.
- 275 attachments where needed.

Avoid vague phrases by themselves:

- "Healthcare automation."
- "Compliance intelligence."
- "Forensic analytics."
- "Quality transformation."

Better public sentence:

> RevCycleMGMT helps billing teams validate 837 claims, monitor 999/277CA responses, reconcile 835 payments, check 270/271 eligibility, track 276/277 claim status, and turn payer responses into clear follow-up workqueues.

## Near-Term Build Decision

The strongest next build is `revcyclemgmt-edi-validation-harness`, followed by `revcyclemgmt-claim-status-tracker`.

Reason:

- They prove engineering depth without needing live Optum credentials.
- They are easy to demo publicly with synthetic files.
- They make the existing claims-pipeline repo look like the first piece of a real implementation suite.
- They support future Optum/Change Healthcare, Availity, Waystar, or payer-direct integrations without implying a current vendor partnership.
