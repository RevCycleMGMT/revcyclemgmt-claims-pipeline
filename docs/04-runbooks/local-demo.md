# Local Demo Runbook

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e . pytest
```

## Run Tests

```bash
pytest -q
```

## Build Demo Warehouse

```bash
python -m revcyclemgmt_claims.pipelines.ingest_edi --inbox tests/sample_data --warehouse warehouse
python -m revcyclemgmt_claims.pipelines.build_marts --warehouse warehouse
```

## Launch Dashboard

```bash
streamlit run apps/dashboard/rcm_app.py
```

## Expected KPI Row

The synthetic demo currently produces:

- `total_claims`: 1
- `total_claim_lines`: 2
- `remittance_count`: 1
- `ack_999_count`: 1
- `ack_277ca_count`: 1
- `denial_rate`: 0.0
- `payment_variance_total`: 0.0
- `claims_needing_workqueue_review`: 0

The demo workqueue is expected to stay clear because the sample remit balances after patient responsibility is considered. In a real implementation, non-zero variance rows would route to posting, contractual-adjustment review, or payer follow-up depending on the source policy.
