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

- `total_claims`: 3
- `total_claim_lines`: 4
- `remittance_count`: 2
- `ack_999_count`: 3
- `ack_277ca_count`: 3
- `clean_claim_rate`: about 0.33
- `claims_paid_or_posted`: 1
- `claims_clearinghouse_rejected`: 1
- `claims_denied_follow_up`: 1
- `payment_variance_total`: 300.0
- `claims_needing_workqueue_review`: 2

The demo intentionally does not stay clean. A startup practice needs to see both success and failure paths:

- one claim that reaches payment visibility,
- one claim rejected in the clearinghouse response flow,
- and one claim denied at remit/adjudication with CARC 16.

In a real implementation, rejected and denied rows would route to billing, coding, documentation, eligibility, payer follow-up, or posting review depending on source policy.
