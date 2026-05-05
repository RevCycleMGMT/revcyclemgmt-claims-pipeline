# Claims Workflow Architecture

This repository demonstrates the RevCycleMGMT claims workflow using synthetic X12-style files.

## Flow

1. Synthetic X12 files land in `tests/sample_data`.
2. `ingest_edi` saves a raw copy for traceability.
3. Parser adapters convert the file type into normalized records.
4. Normalized records are written as JSONL under `warehouse/normalized`.
5. `build_marts` creates the dashboard-ready RCM KPI mart.
6. The Streamlit dashboard reads `warehouse/marts/rcm/kpi_daily.parquet`.

## Normalized Domains

- `claims_header`
- `claims_line`
- `adjudication`
- `payments`
- `acknowledgments`

## Demo Transactions

- `demo_837p.txt`: synthetic professional claim.
- `demo_835.txt`: synthetic remittance/adjudication.
- `demo_999.txt`: synthetic implementation acknowledgment.
- `demo_277ca.txt`: synthetic claim acknowledgment.
