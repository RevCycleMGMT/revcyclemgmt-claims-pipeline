# Claims Workflow Architecture

This repository demonstrates the RevCycleMGMT claims workflow using synthetic X12-style files.

## Flow

1. Synthetic X12 files land in `tests/sample_data`.
2. `ingest_edi` saves a raw copy for traceability.
3. Parser adapters convert the file type into normalized records.
4. Normalized records are written as JSONL under `warehouse/normalized`.
5. `build_marts` creates the dashboard-ready RCM KPI mart and claim journey mart.
6. The Streamlit dashboard reads `warehouse/marts/rcm/kpi_daily.parquet` and `warehouse/marts/rcm/claim_status.parquet`.

## Normalized Domains

- `claims_header`
- `claims_line`
- `adjudication`
- `payments`
- `acknowledgments`

## Mart Outputs

- `kpi_daily`: total claims, 837/835 volume, 999/277CA counts, denial rate, clean claim rate, acknowledgment completion rate, missing acknowledgments, payment variance, and workqueue volume.
- `claim_status`: one row per claim showing whether the claim has a 999 acknowledgment, 277CA acknowledgment, 835 remit, denial follow-up, CARC/RARC root cause group, payment variance, and current workflow status.

## Optional Interoperability Context

The `interoperability` package is intentionally narrow. It can parse synthetic HL7 PID examples into masked claim-prep context so the demo can show how clinical or practice-management exports inform billing readiness. It does not move the repository into population health or general clinical analytics.

## Demo Transactions

- `demo_837p.txt`: synthetic professional claim.
- `demo_835.txt`: synthetic remittance/adjudication.
- `demo_999.txt`: synthetic implementation acknowledgment.
- `demo_277ca.txt`: synthetic claim acknowledgment.
