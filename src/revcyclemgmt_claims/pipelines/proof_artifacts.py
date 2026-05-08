from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path
from typing import Any

import pandas as pd


def _svg_text(value: Any) -> str:
    return escape(str(value), quote=True)


def _pct(value: float) -> str:
    return f"{value:.1%}"


def _money(value: float) -> str:
    return f"${value:,.0f}"


def _metric(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = row.get(key, default)
    if pd.isna(value):
        return default
    return float(value)


def _int_metric(row: dict[str, Any], key: str, default: int = 0) -> int:
    return int(round(_metric(row, key, float(default))))


def _status_label(status: str) -> str:
    labels = {
        "paid_or_posted": "Paid / posted",
        "clearinghouse_rejected": "277CA rejection",
        "denied_follow_up": "Denial follow-up",
        "accepted_waiting_for_remit": "Waiting for 835",
        "implementation_rejected": "999 rejection",
        "implementation_accepted_waiting_for_277ca": "Waiting for 277CA",
        "waiting_for_ack": "Waiting for ACK",
    }
    return labels.get(status, status.replace("_", " ").title())


def build_proof_model(warehouse: Path) -> dict[str, Any]:
    mart_dir = warehouse / "marts" / "rcm"
    kpi_path = mart_dir / "kpi_daily.parquet"
    claim_status_path = mart_dir / "claim_status.parquet"

    if not kpi_path.exists():
        raise FileNotFoundError(f"Missing KPI mart: {kpi_path}")
    if not claim_status_path.exists():
        raise FileNotFoundError(f"Missing claim status mart: {claim_status_path}")

    kpi = pd.read_parquet(kpi_path).fillna("")
    claim_status = pd.read_parquet(claim_status_path).fillna("")
    kpi_row = kpi.iloc[0].to_dict()
    claims = claim_status.sort_values("claim_id").to_dict("records")

    total_claims = _int_metric(kpi_row, "total_claims")
    clearinghouse_rejected = _int_metric(kpi_row, "claims_clearinghouse_rejected")
    denied_follow_up = _int_metric(kpi_row, "claims_denied_follow_up")
    paid_or_posted = _int_metric(kpi_row, "claims_paid_or_posted")
    workqueue = _int_metric(kpi_row, "claims_needing_workqueue_review")
    accepted_277ca = max(total_claims - clearinghouse_rejected, 0)

    stages = [
        {
            "label": "837P claim build",
            "value": total_claims,
            "note": "Synthetic claims leave launch.",
        },
        {
            "label": "999 accepted",
            "value": _int_metric(kpi_row, "ack_999_count"),
            "note": "Implementation ACK visible.",
        },
        {
            "label": "277CA accepted",
            "value": accepted_277ca,
            "note": "Rejection separated early.",
        },
        {
            "label": "835 remit seen",
            "value": _int_metric(kpi_row, "remittance_count"),
            "note": "Remit and denial linked.",
        },
        {
            "label": "Paid / posted",
            "value": paid_or_posted,
            "note": "Clean claim paid.",
        },
        {
            "label": "Workqueue",
            "value": workqueue,
            "note": "Owner-ready follow-up.",
        },
    ]

    return {
        "headline": "Synthetic claims pipeline proof: 837P to 999, 277CA, 835, and workqueue visibility.",
        "metrics": {
            "total_claims": total_claims,
            "total_billed": _metric(kpi_row, "total_billed"),
            "total_paid": _metric(kpi_row, "total_paid"),
            "payment_variance_total": _metric(kpi_row, "payment_variance_total"),
            "clean_claim_rate": _metric(kpi_row, "clean_claim_rate"),
            "ack_completion_rate": _metric(kpi_row, "ack_completion_rate"),
            "denial_rate": _metric(kpi_row, "denial_rate"),
            "workqueue": workqueue,
        },
        "stages": stages,
        "claims": [
            {
                "claim_id": row["claim_id"],
                "payer": row.get("payer", ""),
                "status": _status_label(str(row.get("workflow_status", ""))),
                "999": row.get("ack_999_status", ""),
                "277ca": row.get("ack_277ca_status", ""),
                "835": "Yes" if bool(row.get("has_835_remit")) else "No",
                "carc": row.get("carc_codes", "") or "-",
                "variance": _metric(row, "payment_variance"),
                "review": "Yes" if bool(row.get("needs_workqueue_review")) else "No",
            }
            for row in claims
        ],
        "buyer_readout": [
            f"{total_claims} synthetic claims were traced from 837P build through acknowledgment and remit visibility.",
            f"Clean-claim rate is {_pct(_metric(kpi_row, 'clean_claim_rate'))}; ACK completion is {_pct(_metric(kpi_row, 'ack_completion_rate'))}.",
            f"{workqueue} claims need workqueue review: {clearinghouse_rejected} clearinghouse rejection and {denied_follow_up} denial follow-up.",
        ],
    }


def _metric_card(x: int, y: int, label: str, value: str, note: str) -> str:
    return f"""
      <g>
        <rect x="{x}" y="{y}" width="178" height="104" rx="10" fill="#081012" stroke="#164e53"/>
        <text x="{x + 16}" y="{y + 28}" class="kicker">{_svg_text(label)}</text>
        <text x="{x + 16}" y="{y + 62}" class="metric">{_svg_text(value)}</text>
        <text x="{x + 16}" y="{y + 86}" class="muted">{_svg_text(note)}</text>
      </g>
    """


def _stage_node(x: int, y: int, label: str, value: int, note: str, index: int) -> str:
    return f"""
      <g>
        <circle cx="{x}" cy="{y}" r="24" fill="#00B3A4" opacity=".95"/>
        <text x="{x}" y="{y + 6}" class="node-number" text-anchor="middle">{index}</text>
        <rect x="{x - 94}" y="{y + 38}" width="188" height="90" rx="10" fill="#061012" stroke="#164e53"/>
        <text x="{x - 76}" y="{y + 66}" class="small strong">{_svg_text(label)}</text>
        <text x="{x - 76}" y="{y + 92}" class="metric-small">{value}</text>
        <text x="{x - 76}" y="{y + 114}" class="tiny">{_svg_text(note)}</text>
      </g>
    """


def _claim_row(y: int, claim: dict[str, Any]) -> str:
    status_color = {
        "Paid / posted": "#83f7f4",
        "277CA rejection": "#facc15",
        "Denial follow-up": "#f97316",
    }.get(claim["status"], "#94a3b8")
    return f"""
      <g>
        <rect x="58" y="{y}" width="1164" height="50" rx="9" fill="#081012" stroke="#173f43"/>
        <circle cx="84" cy="{y + 25}" r="7" fill="{status_color}"/>
        <text x="106" y="{y + 21}" class="small strong">{_svg_text(claim['claim_id'])}</text>
        <text x="106" y="{y + 39}" class="tiny">{_svg_text(claim['status'])}</text>
        <text x="342" y="{y + 31}" class="small">{_svg_text(claim['999'])}</text>
        <text x="486" y="{y + 31}" class="small">{_svg_text(claim['277ca'])}</text>
        <text x="650" y="{y + 31}" class="small">{_svg_text(claim['835'])}</text>
        <text x="786" y="{y + 31}" class="small">{_svg_text(claim['carc'])}</text>
        <text x="920" y="{y + 31}" class="small">{_money(float(claim['variance']))}</text>
        <text x="1086" y="{y + 31}" class="small">{_svg_text(claim['review'])}</text>
      </g>
    """


def render_claims_pipeline_svg(model: dict[str, Any]) -> str:
    metrics = model["metrics"]
    cards = [
        ("Claims", f"{metrics['total_claims']:,}", "837P batch"),
        ("Billed", _money(metrics["total_billed"]), "synthetic dollars"),
        ("Paid", _money(metrics["total_paid"]), "835 visibility"),
        ("Variance", _money(metrics["payment_variance_total"]), "cash risk"),
        ("Clean Claim", _pct(metrics["clean_claim_rate"]), "launch quality"),
        ("ACK Complete", _pct(metrics["ack_completion_rate"]), "999 + 277CA"),
    ]
    card_markup = "\n".join(
        _metric_card(46 + (index * 196), 156, label, value, note)
        for index, (label, value, note) in enumerate(cards)
    )

    node_xs = [150, 346, 542, 738, 934, 1130]
    stage_markup = []
    for index, (x, stage) in enumerate(zip(node_xs, model["stages"], strict=True), start=1):
        stage_markup.append(_stage_node(x, 334, stage["label"], stage["value"], stage["note"], index))
        if index < len(node_xs):
            next_x = node_xs[index]
            stage_markup.append(
                f'<path d="M{x + 32} 334 L{next_x - 32} 334" stroke="#83f7f4" stroke-width="5" stroke-linecap="round" opacity=".72"/>'
            )

    row_header = """
      <text x="106" y="526" class="kicker">Claim Journey</text>
      <text x="342" y="526" class="tiny strong">999</text>
      <text x="486" y="526" class="tiny strong">277CA</text>
      <text x="650" y="526" class="tiny strong">835</text>
      <text x="786" y="526" class="tiny strong">CARC</text>
      <text x="920" y="526" class="tiny strong">Variance</text>
      <text x="1086" y="526" class="tiny strong">Review</text>
    """
    claim_rows = "\n".join(_claim_row(546 + index * 58, claim) for index, claim in enumerate(model["claims"]))
    readout_lines = "".join(
        f'<text x="58" y="{736 + index * 22}" class="readout">{_svg_text(line)}</text>'
        for index, line in enumerate(model["buyer_readout"])
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="820" viewBox="0 0 1280 820" role="img" aria-labelledby="title desc">
  <title id="title">RevCycleMGMT synthetic claims pipeline proof</title>
  <desc id="desc">Synthetic 837P, 999, 277CA, 835, payment, denial, and workqueue pipeline proof.</desc>
  <defs>
    <radialGradient id="tealGlow" cx="18%" cy="6%" r="68%">
      <stop offset="0%" stop-color="#83f7f4" stop-opacity=".17"/>
      <stop offset="58%" stop-color="#00B3A4" stop-opacity=".06"/>
      <stop offset="100%" stop-color="#020607" stop-opacity="1"/>
    </radialGradient>
    <linearGradient id="panel" x1="0" x2="1">
      <stop offset="0%" stop-color="#071012" stop-opacity=".98"/>
      <stop offset="100%" stop-color="#0b1416" stop-opacity=".88"/>
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="4" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    <style>
      .title {{ font: 900 42px Inter, Arial, sans-serif; fill: #f8fafc; }}
      .subtitle {{ font: 500 18px Inter, Arial, sans-serif; fill: #cbd5e1; }}
      .kicker {{ font: 900 12px Inter, Arial, sans-serif; fill: #83f7f4; letter-spacing: .12em; text-transform: uppercase; }}
      .metric {{ font: 900 30px Inter, Arial, sans-serif; fill: #ffffff; }}
      .metric-small {{ font: 900 26px Inter, Arial, sans-serif; fill: #ffffff; }}
      .node-number {{ font: 900 18px Inter, Arial, sans-serif; fill: #031719; }}
      .small {{ font: 700 15px Inter, Arial, sans-serif; fill: #d9fffd; }}
      .tiny {{ font: 600 12px Inter, Arial, sans-serif; fill: #cbd5e1; }}
      .muted {{ font: 600 12px Inter, Arial, sans-serif; fill: #94a3b8; }}
      .readout {{ font: 700 17px Inter, Arial, sans-serif; fill: #e2e8f0; }}
      .strong {{ font-weight: 900; fill: #f8fafc; }}
    </style>
  </defs>
  <rect width="1280" height="820" fill="#020607"/>
  <rect width="1280" height="820" fill="url(#tealGlow)"/>
  <path d="M0 740 C160 670 300 802 490 736 C690 666 840 786 1068 724 C1186 692 1230 700 1280 660 L1280 820 L0 820 Z" fill="#00B3A4" opacity=".06"/>
  <rect x="28" y="28" width="1224" height="764" rx="18" fill="url(#panel)" stroke="#164e53"/>
  <text x="56" y="78" class="kicker">Synthetic Claims Pipeline Proof</text>
  <text x="56" y="124" class="title">837P to payment visibility, without public PHI.</text>
  <text x="56" y="154" class="subtitle">A tiny startup-practice batch shows one paid claim, one clearinghouse rejection, and one denial follow-up path.</text>
  <g filter="url(#glow)">
    <circle cx="1178" cy="84" r="7" fill="#83f7f4"/>
    <circle cx="1204" cy="84" r="7" fill="#00B3A4"/>
    <circle cx="1230" cy="84" r="7" fill="#facc15"/>
  </g>
  {card_markup}
  <rect x="46" y="292" width="1188" height="192" rx="14" fill="#061012" stroke="#164e53"/>
  <text x="68" y="316" class="kicker">Pipeline Movement</text>
  {"".join(stage_markup)}
  <rect x="46" y="498" width="1188" height="196" rx="14" fill="#061012" stroke="#164e53"/>
  {row_header}
  {claim_rows}
  <rect x="46" y="714" width="1188" height="66" rx="14" fill="#071012" stroke="#164e53"/>
  {readout_lines}
</svg>
"""


def run(warehouse: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    model = build_proof_model(warehouse)
    svg = render_claims_pipeline_svg(model)
    (output_dir / "claims_pipeline_summary.json").write_text(
        json.dumps(model, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "claims_pipeline_map.svg").write_text(svg, encoding="utf-8")
    return {
        "total_claims": model["metrics"]["total_claims"],
        "workqueue": model["metrics"]["workqueue"],
        "artifact_count": 2,
        "svg": str(output_dir / "claims_pipeline_map.svg"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build RevCycleMGMT claims pipeline proof artifacts.")
    parser.add_argument("--warehouse", type=Path, default=Path("warehouse"))
    parser.add_argument("--out", type=Path, default=Path("output_demo"))
    args = parser.parse_args()
    print(json.dumps(run(args.warehouse, args.out), indent=2))


if __name__ == "__main__":
    main()
