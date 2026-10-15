"""pages/1_Executive_Summary.py - Page 1: headline KPIs, 3 findings, 3 recommendations.

Every number shown is read from outputs/ at render time (analysis_summary.json or CSV).
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
import plotly.express as px

APP_DIR = Path(__file__).resolve().parents[1]
ROOT = APP_DIR.parent
for p in [str(APP_DIR), str(ROOT / "src")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from data import (load_summary, load_orders, load_kpi_monthly, apply_order_filters,  # noqa: E402
                  load_stage_bad_vs_normal, load_funnel_origin_stat, load_funnel_waterfall,
                  load_robust_lateness, load_robust_first_sale)
from ui import (kpi_row, caveat_badge, method_expander, download_brief,  # noqa: E402
                empty_state_guard, ORANGE, RED)

st.title("🏠 Executive Summary")
st.caption("Olist Seller Acquisition & Delivery Diagnostics · window 2017-01 to 2018-08 · all relationships are associations in observational data")

# ─── Load everything from outputs/ ────────────────────────────────────────────
summary = load_summary()
kpi, rev, dlv, fn = summary["kpi"], summary["reviews"], summary["delivery"], summary["funnel"]
stage = load_stage_bad_vs_normal().set_index("period")
origin = load_funnel_origin_stat().set_index("origin")
wf = load_funnel_waterfall()
wf_d = dict(zip(wf["stage"], wf["value"]))
rob_late = load_robust_lateness().set_index("definition")
rob_fs = load_robust_first_sale().set_index("definition")

matured = float(wf_d["deals_matured_90d"])
first_sale = float(wf_d["matured_deals_first_sale_within_90d"])
first_rate = first_sale / matured
not_observed = 1 - first_rate

ts_gap = float(rob_late.loc["timestamp_level", "post_delivery_gap_pp"])
p_ts = float(rob_fs.loc["timestamp_level (baseline)", "chi2_p_value"])
p_date = float(rob_fs.loc["date_level", "chi2_p_value"])


def orate(name: str) -> str:
    return f"{origin.loc[name, 'conv_rate'] * 100:.1f}%" if name in origin.index else "n/a"


# ─── Filters ──────────────────────────────────────────────────────────────────
orders = load_orders()
sel_m = st.session_state.get("sel_months", [])
sel_s = st.session_state.get("sel_states", [])
sel_c = st.session_state.get("sel_categories", [])
filtered = apply_order_filters(orders, sel_m or None, sel_s or None, sel_c or None)
active_filter = bool(sel_m or sel_s or sel_c)

if not empty_state_guard(filtered, min_rows=1):
    st.stop()

if active_filter:
    st.info(f"🔽 Filters active: {len(filtered):,} of {len(orders):,} orders. Cards in the first row use the filtered orders; "
            "all other cards, the findings and the recommendations always show the full window.")
    n_show = len(filtered)
    n_late_f = int(filtered["is_late"].sum())
    late_rate_f = n_late_f / n_show
    avg_review_f = float(filtered["review_score"].mean()) if filtered["review_score"].notna().any() else float("nan")
    dispatch_f = float(filtered["dispatch_days"].mean()) if filtered["dispatch_days"].notna().any() else float("nan")
    late_note = f"{n_late_f:,} late"
else:
    n_show = kpi["delivered_valid_orders"]
    n_late_f = kpi["late_orders"]
    late_rate_f = kpi["late_rate"]
    avg_review_f = kpi["avg_review"]
    dispatch_f = kpi["avg_dispatch_days"]
    late_note = f"{n_late_f:,} late · 95% CI {kpi['late_rate_ci_lo']*100:.2f}–{kpi['late_rate_ci_hi']*100:.2f}%"

# ─── KPI cards ────────────────────────────────────────────────────────────────
st.markdown("### 📊 Key Performance Indicators")
kpi_row([
    {"label": "Delivered orders", "value": f"{n_show:,}", "help": "In-window delivered-valid orders"},
    {"label": "On-time rate", "value": f"{(1 - late_rate_f) * 100:.1f}%", "n": f"{n_show:,}",
     "help": "Delivered on or before the estimated date (date-level lateness, D-012)"},
    {"label": "Late rate", "value": f"{late_rate_f * 100:.2f}%", "n": late_note, "help": "Late = delivery date after estimated date"},
    {"label": "Avg review score", "value": f"{avg_review_f:.2f} / 5", "help": "One review per order (latest)"},
    {"label": "Avg dispatch days", "value": f"{dispatch_f:.1f} d", "help": "Purchase approval to carrier hand-off"},
])
kpi_row([
    {"label": "Item GMV (full window)", "value": f"BRL {kpi['gmv_items'] / 1e6:.2f} M", "help": "Item value only, delivered-valid orders"},
    {"label": "AOV (full window)", "value": f"BRL {kpi['aov']:.0f}", "help": "Item value per delivered order"},
    {"label": "Dispatch compliance", "value": f"{kpi['dispatch_compliance'] * 100:.1f}%",
     "help": "Share of orders handed to the carrier by the shipping limit date"},
    {"label": "Lead → deal rate", "value": f"{fn['lead_to_deal_rate'] * 100:.1f}%",
     "n": f"{fn['deals']} of {fn['leads']:,} leads · CI {fn['lead_to_deal_ci_lo']*100:.1f}–{fn['lead_to_deal_ci_hi']*100:.1f}%"},
    {"label": "First observed sale ≤ 90 d", "value": f"{first_rate * 100:.1f}%",
     "n": f"{int(first_sale)} of {int(matured)} matured deals",
     "help": "'Not observed' does not mean 'did not sell' (L-001): the data is a sample"},
])

# ─── Monthly trend ────────────────────────────────────────────────────────────
st.markdown("### 📈 Monthly Late Rate")
if active_filter:
    monthly = (filtered.groupby("purchase_month")["is_late"].agg(["sum", "count"]).reset_index()
               .rename(columns={"purchase_month": "month"}))
    monthly["late_rate"] = monthly["sum"] / monthly["count"]
    st.caption("Recomputed from the filtered orders.")
else:
    monthly = load_kpi_monthly()
fig = px.line(monthly, x="month", y="late_rate", markers=True, color_discrete_sequence=[ORANGE],
              labels={"month": "Month", "late_rate": "Late rate"})
fig.update_layout(title="Late order rate by purchase month", yaxis_tickformat=".1%",
                  plot_bgcolor="#F4F6FA", paper_bgcolor="white", margin=dict(l=20, r=20, t=40, b=20))
fig.add_hline(y=0.10, line_dash="dash", line_color=RED, annotation_text="10% bad-month threshold (D-017)")
st.plotly_chart(fig, width="stretch")
method_expander("Monthly late rate", "Late = date of delivery after the estimated delivery date (D-012). "
                "Source table: `out_kpi_monthly.csv` produced by `sql/03_kpis.sql`.")

# ─── Findings ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🔍 Key Findings (full window)")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("#### 🚛 1 · Most of the extra delay time is carrier transit")
    st.markdown(
        f"In the three months with a late rate above 10% ({', '.join(dlv['bad_months'])}), average carrier transit was "
        f"**{stage.loc['bad', 'avg_transit_days']:.1f} days** vs **{stage.loc['normal', 'avg_transit_days']:.1f}** in other months, while "
        f"dispatch moved from {stage.loc['normal', 'avg_dispatch_days']:.1f} to {stage.loc['bad', 'avg_dispatch_days']:.1f} days. "
        f"Of the {dlv['shift_share_change'] * 100:+.2f} pp rise in the late rate, the within-state rate effect is "
        f"**{dlv['shift_share_rate_effect'] * 100:+.2f} pp** and the state-mix effect {dlv['shift_share_mix_effect'] * 100:+.2f} pp."
    )
    st.metric("Transit share of late orders' extra time", f"{dlv['pct_extra_transit'] * 100:.1f}%")
    caveat_badge("Descriptive decomposition; no carrier-level data to say why")

with c2:
    st.markdown("#### 📬 2 · Missed dispatch deadline is associated with lateness")
    tot = dlv["dispatch_missed_n"] + dlv["dispatch_met_n"]
    st.markdown(
        f"**{dlv['dispatch_missed_n']:,}** orders ({dlv['dispatch_missed_n'] / tot * 100:.1f}%) missed the seller shipping limit; "
        f"their late rate is **{dlv['dispatch_missed_late_rate'] * 100:.1f}%** vs {dlv['dispatch_met_late_rate'] * 100:.1f}% for the rest. "
        f"They make up {dlv['dispatch_missed_pct_of_late'] * 100:.1f}% of all late orders, so dispatch is real but secondary to transit."
    )
    st.metric("Risk ratio (missed vs met)", f"{dlv['dispatch_missed_risk_ratio']:.2f}×")
    caveat_badge("Association only")

with c3:
    st.markdown("#### ⭐ 3 · Late delivery is associated with worse reviews")
    st.markdown(
        f"Crude 1-star gap, late vs on-time: **{rev['one_star_gap'] * 100:.1f} pp** "
        f"({rev['one_star_late'] * 100:.1f}% vs {rev['one_star_ontime'] * 100:.1f}%). Many reviews predate delivery, so using only reviews "
        f"written after delivery the gap is **{rev['post_delivery_gap'] * 100:.1f} pp** "
        f"({rev['post_delivery_1star_late'] * 100:.1f}% vs {rev['post_delivery_1star_ontime'] * 100:.1f}%), and "
        f"{ts_gap:.1f} pp with timestamp-level lateness. Adjusted odds ratio (review timing × state): "
        f"**{rev['mh_or']:.2f}** (95% CI {rev['mh_or_ci'][0]:.2f}–{rev['mh_or_ci'][1]:.2f}) vs crude {rev['crude_or']:.2f}."
    )
    st.metric("Post-delivery 1-star gap", f"{rev['post_delivery_gap'] * 100:.1f} pp")
    caveat_badge("Reviews are voluntary; survey timing explains most of the crude gap (L-009)")

# ─── Recommendations ──────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 💡 Recommendations")
sim_10 = next((r for r in summary["simulator"] if abs(r["pct_worst"] - 0.10) < 1e-9), None)
lane = dlv["sp_rj_lane"]
r1, r2, r3 = st.columns(3)
with r1:
    st.success(
        f"**1 · Prioritise the carrier leg on slow lanes and peak months.**\n\n"
        f"{lane['lane']}: {lane['late_rate'] * 100:.1f}% late on {lane['orders']:,} orders. "
        f"Top-3 states hold {dlv['top3_states_share_of_late'] * 100:.1f}% of late orders.\n\n"
        f"**KPI:** late rate by destination state and lane; carrier transit days; late rate in peak months."
    )
with r2:
    if sim_10:
        st.success(
            f"**2 · Put sellers who miss the shipping limit on a dispatch scorecard.**\n\n"
            f"Scenario (not a forecast): bringing the worst {sim_10['n_fixed_sellers']} sellers to the median dispatch time avoids "
            f"~{sim_10['late_orders_avoided']:,} late orders ({sim_10['share_of_all_late'] * 100:.1f}% of all late); "
            f"one-star avoided between {sim_10['est_1star_low']} and {sim_10['est_1star_high']} (a range, D-024).\n\n"
            f"**KPI:** dispatch compliance (now {kpi['dispatch_compliance'] * 100:.1f}%); late rate of flagged sellers."
        )
with r3:
    st.success(
        f"**3 · Keep the funnel; test weak channels before adding spend.**\n\n"
        f"Lead→deal: social {orate('social')} and email {orate('email')} vs organic search {orate('organic_search')} and "
        f"paid search {orate('paid_search')}. {not_observed * 100:.1f}% of matured deals have no first sale observed within 90 days. "
        f"No cost data, so no ROI claim.\n\n"
        f"**KPI:** lead→deal rate by origin with n; first observed sale ≤ 90 d; month-2 seller retention."
    )
caveat_badge("Recommendations rest on observational associations. No causal claim is made.")

# ─── Limitations ──────────────────────────────────────────────────────────────
with st.expander("⚠️ Key Limitations"):
    st.markdown(f"""
- **Observational data only.** Acquired-seller comparisons have selection effects (L-010); only {wf_d['deal_sellers_in_order_items']:.0f} of {fn['deals']} deal sellers appear in the order data.
- **Survey timing.** Most late orders' reviews were written before delivery (L-009), so the crude gap overstates the review penalty. The post-delivery gap is {ts_gap:.1f}–{rev['post_delivery_gap'] * 100:.1f} pp depending on the lateness definition.
- **Exploratory channel comparison.** The omnibus test of first sale by origin moves from p = {p_ts:.3f} to p = {p_date:.3f} when first sale is measured at date level (V-012). The paid-vs-organic difference stays positive under both ({fn['paid_vs_organic']['diff_pp']:.1f} pp, CI {fn['paid_vs_organic']['diff_ci_lo_pp']:.1f} to {fn['paid_vs_organic']['diff_ci_hi_pp']:.1f}), but it was chosen after looking at the data and has no multiple-comparison correction (L-011).
- **Simulator is a scenario,** a range between the post-delivery and the crude review gap (D-024), not a forecast.
- **No cost, margin or CAC data,** so nothing here is costed (L-004).
- **Sample and period.** Public Olist sample, 2017–2018; later months are censored.
""")

# ─── Executive brief download ─────────────────────────────────────────────────
brief = f"""# Olist Executive Brief
Scope: {len(filtered):,} orders {'(filtered)' if active_filter else '(full window)'}. Findings and recommendations below are always full window.

## Headline KPIs
- Delivered orders: {n_show:,}
- Late rate: {late_rate_f * 100:.2f}%
- Avg review: {avg_review_f:.2f}/5
- Item GMV (full window): BRL {kpi['gmv_items']:,.0f}

## Findings (associations, not causal)
1. Carrier transit {stage.loc['bad', 'avg_transit_days']:.1f} vs {stage.loc['normal', 'avg_transit_days']:.1f} days in bad vs normal months; {dlv['pct_extra_transit'] * 100:.1f}% of late orders' extra time is transit.
2. Missed dispatch deadline: late rate {dlv['dispatch_missed_late_rate'] * 100:.1f}% vs {dlv['dispatch_met_late_rate'] * 100:.1f}% (RR {dlv['dispatch_missed_risk_ratio']:.2f}).
3. Post-delivery 1-star gap {ts_gap:.1f}-{rev['post_delivery_gap'] * 100:.1f} pp; adjusted OR {rev['mh_or']:.2f} (CI {rev['mh_or_ci'][0]:.2f}-{rev['mh_or_ci'][1]:.2f}).

## Recommendations
1. Prioritise the carrier leg on slow lanes ({lane['lane']} {lane['late_rate'] * 100:.1f}% late) and peak months.
2. Dispatch scorecard for sellers who miss the shipping limit (scenario: ~{sim_10['late_orders_avoided'] if sim_10 else 'n/a'} late orders avoided at 10%).
3. Keep the funnel; test social/email follow-up before adding spend.

Data: Olist Brazilian E-Commerce (CC BY-NC-SA 4.0).
"""
download_brief(brief, filename="olist_executive_brief.md")
