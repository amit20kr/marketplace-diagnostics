"""pages/2_Acquisition_Funnel.py - Page 2: funnel, conversion by origin/landing page, first observed sale, days to close, SDRs."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

APP_DIR = Path(__file__).resolve().parents[1]
ROOT = APP_DIR.parent
for p in [str(APP_DIR), str(ROOT / "src")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from data import (load_summary, load_funnel_waterfall, load_funnel_origin_stat,  # noqa: E402
                  load_funnel_landing_stat, load_days_to_close, load_sdr,
                  load_downstream_origin, load_robust_first_sale)
from ui import (caveat_badge, precomputed_label, sql_expander, section, download_csv,  # noqa: E402
                empty_state_guard, wilson, ORANGE, BLUE, GREEN)

st.title("🔭 Acquisition Funnel")
st.caption("Lead → closed deal → seller → first observed sale. Lead and seller data: the sidebar order filters do not apply on this page.")

summary = load_summary()
fn = summary["funnel"]
wf = load_funnel_waterfall()
wf_d = dict(zip(wf["stage"], wf["value"]))

# ─── Section 1: funnel (two separate populations) ─────────────────────────────
section("Funnel and join coverage",
        f"Lead-to-deal rate {fn['lead_to_deal_rate'] * 100:.2f}% "
        f"(95% CI {fn['lead_to_deal_ci_lo'] * 100:.2f}–{fn['lead_to_deal_ci_hi'] * 100:.2f}%)")

labels = ["All leads (MQLs)", "Closed deals", "Deal sellers in order items", "…with a delivered order"]
values = [wf_d["all_leads"], wf_d["closed_deals"], wf_d["deal_sellers_in_order_items"], wf_d["deal_sellers_with_delivered_order"]]
fig_a = go.Figure(go.Funnel(y=labels, x=values, textinfo="value+percent previous",
                            marker=dict(color=[ORANGE, BLUE, GREEN, GREEN])))
fig_a.update_layout(title="A · Who can be followed into the order data (each stage is a subset of the previous)",
                    plot_bgcolor="#F4F6FA", paper_bgcolor="white", margin=dict(l=20, r=20, t=50, b=20))
st.plotly_chart(fig_a, width="stretch")
st.caption(f"Only {int(values[2])} of {int(values[1])} closed-deal sellers appear in the order data (L-002). "
           f"Everything downstream rests on those sellers: {wf_d['delivered_orders_from_deal_sellers']:,.0f} delivered orders, "
           f"BRL {wf_d['item_gmv_deal_sellers']:,.0f} item GMV. A naive leads × deals × items join would give "
           f"{wf_d['NAIVE_join_rows_leads_x_deals_x_items']:,.0f} rows (fan-out), so we count distinct keys at the right grain.")

matured = int(wf_d["deals_matured_90d"])
first = int(wf_d["matured_deals_first_sale_within_90d"])
lo, hi = wilson(first, matured)
c1, c2, c3 = st.columns(3)
c1.metric("B · Matured deals (≥ 90 days of data after the deal)", f"{matured:,}", help="Share of ALL closed deals, so shown apart from panel A")
c2.metric("…with a first observed sale within 90 days", f"{first:,}", f"{first / matured * 100:.1f}% (95% CI {lo * 100:.1f}–{hi * 100:.1f}%)", delta_color="off")
c3.metric("Not observed selling within 90 days", f"{matured - first:,}", f"{(matured - first) / matured * 100:.1f}%", delta_color="off",
          help="'Not observed' does not mean 'did not sell' (L-001)")
sql_expander("Funnel and coverage", "04_funnel.sql")

# ─── Section 2: Conversion by origin ──────────────────────────────────────────
section("Lead → deal conversion by origin", "Origins with at least 100 leads shown; others are flagged small-n")
precomputed_label()
orig = load_funnel_origin_stat()
big = orig[orig["small_n"] == 0].sort_values("conv_rate", ascending=False)
if empty_state_guard(big, min_rows=2):
    fig_o = go.Figure(go.Bar(
        x=big["origin"], y=big["conv_rate"],
        error_y=dict(type="data", symmetric=False,
                     array=(big["conv_hi"] - big["conv_rate"]).tolist(),
                     arrayminus=(big["conv_rate"] - big["conv_lo"]).tolist()),
        text=[f"{r * 100:.1f}%<br>n={n:,}" for r, n in zip(big["conv_rate"], big["leads"])],
        textposition="outside", marker_color=ORANGE))
    fig_o.update_layout(title="Lead → deal rate by origin (95% Wilson CI; n = leads)", yaxis_tickformat=".0%",
                        plot_bgcolor="#F4F6FA", paper_bgcolor="white", margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig_o, width="stretch")
    chi = fn["chi2_origin"]
    st.caption(f"Differences across origins: chi-square = {chi['chi2']:.1f} (dof {chi['dof']}), Cramér's V = {chi['cramers_v']:.2f} (a modest effect).")
    small = orig[orig["small_n"] == 1]
    if len(small):
        st.caption(f"⚠️ Small-n origins not shown (< 100 leads): {', '.join(small['origin'].astype(str))}")
download_csv(orig, label="Download origin stats", filename="funnel_origin.csv")

# ─── Section 3: Conversion by landing page ────────────────────────────────────
section("Lead → deal conversion by landing page", "Landing pages with at least 100 leads")
precomputed_label()
land = load_funnel_landing_stat()
lbig = land[land["small_n"] == 0].sort_values("conv_rate", ascending=False).head(12).copy()
if empty_state_guard(lbig):
    lbig["page"] = lbig["landing_page_id"].astype(str).str[:6]
    fig_l = go.Figure(go.Bar(
        x=lbig["page"], y=lbig["conv_rate"],
        error_y=dict(type="data", symmetric=False,
                     array=(lbig["conv_hi"] - lbig["conv_rate"]).tolist(),
                     arrayminus=(lbig["conv_rate"] - lbig["conv_lo"]).tolist()),
        text=[f"{r * 100:.1f}%<br>n={n:,}" for r, n in zip(lbig["conv_rate"], lbig["leads"])],
        textposition="outside", marker_color=BLUE))
    fig_l.update_layout(title="Top landing pages by lead → deal rate (page id shortened; 95% Wilson CI)", yaxis_tickformat=".0%",
                        plot_bgcolor="#F4F6FA", paper_bgcolor="white", margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig_l, width="stretch")
    cl = fn["chi2_landing"]
    st.caption(f"Across landing pages: chi-square = {cl['chi2']:.1f} (dof {cl['dof']}), Cramér's V = {cl['cramers_v']:.2f}. "
               "Landing page is known for all leads; segment and lead type exist only for closed deals, so they cannot explain conversion (L-008).")
download_csv(land, label="Download landing-page stats", filename="funnel_landing.csv")

# ─── Section 4: first observed sale by origin ─────────────────────────────────
section("First observed sale within 90 days, by origin", "Origins with at least 30 matured deals")
precomputed_label()
ds = load_downstream_origin()
if empty_state_guard(ds):
    ds = ds.sort_values("downstream_rate", ascending=False)
    fig_d = go.Figure(go.Bar(
        x=ds["origin"], y=ds["downstream_rate"],
        error_y=dict(type="data", symmetric=False,
                     array=(ds["downstream_hi"] - ds["downstream_rate"]).tolist(),
                     arrayminus=(ds["downstream_rate"] - ds["downstream_lo"]).tolist()),
        text=[f"{r * 100:.1f}%<br>n={n:,}" for r, n in zip(ds["downstream_rate"], ds["matured_deals"])],
        textposition="outside", marker_color=GREEN))
    fig_d.update_layout(title="First observed sale within 90 days (95% Wilson CI; n = matured deals)", yaxis_tickformat=".0%",
                        plot_bgcolor="#F4F6FA", paper_bgcolor="white", margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig_d, width="stretch")

po = fn["paid_vs_organic"]
st.metric("Paid minus organic search (first observed sale ≤ 90 d)", f"{po['diff_pp']:+.2f} pp",
          f"95% CI {po['diff_ci_lo_pp']:.1f} to {po['diff_ci_hi_pp']:.1f} pp", delta_color="off",
          help=f"Paid {po['paid_rate'] * 100:.1f}% ({po['paid_first_sale']}/{po['paid_matured']}); "
               f"organic {po['organic_rate'] * 100:.1f}% ({po['organic_first_sale']}/{po['organic_matured']})")
rfs = load_robust_first_sale().set_index("definition")
ch = fn["chi2_downstream"]
st.caption(
    f"Omnibus test across origins: chi-square = {ch['chi2']:.2f}, p = {ch['p_value']:.3f} with first sale at timestamp level; "
    f"p = {rfs.loc['date_level', 'chi2_p_value']:.3f} at date level. The p-value crosses 0.05 on a two-deal difference, so treat it as fragile. "
    f"Paid-vs-organic CI at date level: {rfs.loc['date_level', 'diff_ci_lo_pp']:.1f} to {rfs.loc['date_level', 'diff_ci_hi_pp']:.1f} pp.")
caveat_badge("Exploratory: comparison chosen after viewing the data, no multiple-comparison correction (V-012, L-011). No cost data (L-004).")

# ─── Section 5: days to close ─────────────────────────────────────────────────
section("Days to close", "From first contact to closed deal")
dtc = load_days_to_close()
if empty_state_guard(dtc):
    fig_t = px.bar(dtc, x="band", y="share", text=dtc["share"].apply(lambda x: f"{x * 100:.1f}%"), color_discrete_sequence=[GREEN])
    fig_t.update_layout(title="Share of closed deals by days to close", yaxis_tickformat=".0%",
                        plot_bgcolor="#F4F6FA", paper_bgcolor="white", margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig_t, width="stretch")
d = fn["days_to_close"]
a, b, c = st.columns(3)
a.metric("Median days to close", f"{d['median']:.0f}")
b.metric("Closed within 30 days", f"{d['share_within_30'] * 100:.1f}%")
c.metric("Closed within 90 days", f"{d['share_within_90'] * 100:.1f}%")

# ─── Section 6: SDRs ──────────────────────────────────────────────────────────
section("SDR table", "Deals closed and median days to close; SDRs with fewer than 10 deals are flagged")
precomputed_label()
sdr = load_sdr()
s = fn["sdr"]
a, b, c = st.columns(3)
a.metric("SDRs", s["total_sdrs"])
b.metric("SDRs with ≥ 10 deals", s["sdrs_ge_10_deals"])
c.metric("Top 3 SDRs' share of deals", f"{s['top3_share'] * 100:.1f}%", f"{s['top3_deals']} of {fn['deals']} deals", delta_color="off")
sd = sdr.copy()
sd["Flag"] = sd["small_n"].apply(lambda x: "⚠️ < 10 deals" if x else "")
st.dataframe(sd[["sdr_id", "deals", "median_days_to_close", "Flag"]].rename(
    columns={"sdr_id": "SDR id", "deals": "Deals", "median_days_to_close": "Median days to close"}), width="stretch")
st.caption("Lead-level SDR conversion is not computable (SDR is recorded only for closed deals, L-008).")
download_csv(sdr, label="Download SDR table", filename="sdr_stats.csv")
