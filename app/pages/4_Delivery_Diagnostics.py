"""pages/4_Delivery_Diagnostics.py – Page 4: monthly trend, stage decomp, state/lane/category drill, Pareto."""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

APP_DIR = Path(__file__).resolve().parents[1]
ROOT = APP_DIR.parent
for p in [str(APP_DIR), str(ROOT / "src")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from data import (load_summary, load_orders, load_kpi_monthly, load_late_state,
                  load_late_lane, load_seller_pareto, load_stage_bad_vs_normal,
                  load_shift_share_state, load_late_category, apply_order_filters)
from ui import (caveat_badge, precomputed_label, sql_expander, method_expander,
                section, download_csv, empty_state_guard, ORANGE, BLUE, GREEN, RED, GREY)

st.title("🚚 Delivery Diagnostics")
st.caption("Monthly trend, shift-share, stage decomposition, state/lane/category drill, seller Pareto")

summary = load_summary()
dlv = summary["delivery"]

# ─── Filters ──────────────────────────────────────────────────────────────────
orders = load_orders()
sel_m = st.session_state.get("sel_months", [])
sel_s = st.session_state.get("sel_states", [])
sel_c = st.session_state.get("sel_categories", [])
filtered = apply_order_filters(orders, sel_m or None, sel_s or None, sel_c or None)

if not empty_state_guard(filtered, min_rows=10):
    st.stop()

# ─── Section 1: Monthly Late Rate Trend ──────────────────────────────────────
section("Monthly Late Rate Trend")
precomputed_label()

monthly = load_kpi_monthly()
fig_monthly = px.line(
    monthly, x="month", y="late_rate",
    markers=True, color_discrete_sequence=[ORANGE],
    labels={"month": "Month", "late_rate": "Late Rate"},
)
fig_monthly.add_hline(y=0.10, line_dash="dash", line_color=RED,
                      annotation_text="10% threshold (D-017)")
fig_monthly.update_layout(
    title="Late Orders as % of Delivered Orders by Month",
    yaxis_tickformat=".1%", plot_bgcolor="#F4F6FA", paper_bgcolor="white",
)
st.plotly_chart(fig_monthly, width="stretch")

bad_months = dlv.get("bad_months", [])
st.caption(f"Bad months (late rate > 10%): **{', '.join(bad_months)}**")
st.caption(f"Baseline late rate (normal months): {dlv['baseline_late_rate']*100:.2f}%  →  Bad months: {dlv['bad_months_late_rate']*100:.2f}%")

# ─── Section 2: Stage Decomposition ──────────────────────────────────────────
section("Stage Decomposition: Bad vs Normal Months")
precomputed_label()

stage_bn = load_stage_bad_vs_normal()
if not stage_bn.empty:
    cols_to_show = ["period", "n_orders", "avg_dispatch_days", "avg_transit_days", "avg_promised_days"]
    st.dataframe(
        stage_bn[cols_to_show].rename(columns={
            "period": "Period", "n_orders": "Orders",
            "avg_dispatch_days": "Avg Dispatch (days)",
            "avg_transit_days": "Avg Transit (days)",
            "avg_promised_days": "Avg Promised (days)",
        }),
        width="stretch",
    )

col1, col2, col3 = st.columns(3)
col1.metric("Dispatch share of extra time", f"{dlv.get('pct_extra_dispatch', 0)*100:.1f}%")
col2.metric("Transit share of extra time",  f"{dlv.get('pct_extra_transit', 0)*100:.1f}%")
col3.metric("Extra dispatch days (late vs on-time)", f"{dlv.get('extra_dispatch_days', 0):.2f} d")

method_expander("Shift-share decomposition", """
Change in late rate = Mix effect + Rate effect
  Mix effect  = Σ (bad_share_s - normal_share_s) × normal_rate_s
  Rate effect = Σ bad_share_s × (bad_rate_s - normal_rate_s)

Where s = customer_state. Per-state contributions: outputs/stat_shift_share_state.csv (computed in src/analysis.py with src/stats.py).
""")

# ─── Section 3: State → Lane → Category Drill-Down ────────────────────────────
st.markdown("**Where did the late-rate rise happen? Contribution of each state (bad vs normal months)**")
precomputed_label()
ss = load_shift_share_state().sort_values("total_effect_pp", ascending=False).head(10)
if empty_state_guard(ss):
    fig_ss = go.Figure()
    fig_ss.add_trace(go.Bar(x=ss["customer_state"], y=ss["rate_effect_pp"], name="Rate effect (within-state)", marker_color=RED))
    fig_ss.add_trace(go.Bar(x=ss["customer_state"], y=ss["mix_effect_pp"], name="Mix effect", marker_color=GREY))
    fig_ss.update_layout(barmode="relative", title="Top 10 states: contribution to the change in late rate (percentage points)",
                         plot_bgcolor="#F4F6FA", paper_bgcolor="white", legend=dict(orientation="h"))
    st.plotly_chart(fig_ss, width="stretch")
    st.caption(f"All states: mix effect {dlv['shift_share_mix_effect']*100:+.2f} pp, rate effect {dlv['shift_share_rate_effect']*100:+.2f} pp, "
               f"total {dlv['shift_share_change']*100:+.2f} pp. The rise happened inside states, not because orders moved to harder states.")

section("State → Lane → Category Drill-Down")

tab_state, tab_lane, tab_cat = st.tabs(["By State", "By Lane", "By Category"])

with tab_state:
    precomputed_label()
    late_state = load_late_state()
    min_n_state = st.slider("Minimum orders (state)", 50, 2000, 500, step=50, key="min_n_state")
    ls = late_state[late_state["orders"] >= min_n_state].sort_values("late_rate", ascending=False)
    if empty_state_guard(ls):
        fig_st = px.bar(
            ls.head(20), x="customer_state", y="late_rate",
            error_y=(ls.head(20)["ci_hi"] - ls.head(20)["late_rate"]),
            error_y_minus=(ls.head(20)["late_rate"] - ls.head(20)["ci_lo"]),
            text=ls.head(20)["late_rate"].apply(lambda x: f"{x*100:.1f}%"),
            color="late_rate", color_continuous_scale="Oranges",
            labels={"customer_state": "State", "late_rate": "Late Rate"},
        )
        fig_st.update_layout(
            title="Late Rate by Customer State (top 20, with 95% Wilson CI)",
            yaxis_tickformat=".1%", showlegend=False,
            plot_bgcolor="#F4F6FA", paper_bgcolor="white",
        )
        st.plotly_chart(fig_st, width="stretch")
        st.caption(f"Top 3 states share of all late orders: **{dlv['top3_states_share_of_late']*100:.1f}%**")
        download_csv(ls, label="Download State Stats", filename="late_state.csv")

with tab_lane:
    precomputed_label()
    late_lane = load_late_lane()
    min_n_lane = st.slider("Minimum orders (lane)", 50, 1000, 200, step=50, key="min_n_lane")
    ll = late_lane[late_lane["orders"] >= min_n_lane].sort_values("late_rate", ascending=False)
    if empty_state_guard(ll):
        fig_lane = px.bar(
            ll.head(20), x="lane", y="late_rate",
            text=ll.head(20)["late_rate"].apply(lambda x: f"{x*100:.1f}%"),
            color="late_rate", color_continuous_scale="Blues",
            labels={"lane": "Seller→Customer Lane", "late_rate": "Late Rate"},
        )
        fig_lane.update_layout(
            title="Top 20 Lanes by Late Rate",
            yaxis_tickformat=".1%", showlegend=False,
            plot_bgcolor="#F4F6FA", paper_bgcolor="white",
        )
        st.plotly_chart(fig_lane, width="stretch")
        sp_rj = dlv.get("sp_rj_lane", {})
        if sp_rj:
            st.caption(f"SP→RJ lane: {sp_rj.get('orders',0):,} orders, "
                       f"late rate {sp_rj.get('late_rate',0)*100:.1f}% "
                       f"[{sp_rj.get('ci_lo',0)*100:.1f}%, {sp_rj.get('ci_hi',0)*100:.1f}%]")
        download_csv(ll, label="Download Lane Stats", filename="late_lane.csv")

with tab_cat:
    st.caption("Filtered by sidebar selections (live computation from app_orders)")
    cat_late = (
        filtered.groupby("category")
        .agg(orders=("order_id", "count"), late=("is_late", "sum"))
        .reset_index()
    )
    cat_late["late_rate"] = cat_late["late"] / cat_late["orders"]
    min_n_cat = st.slider("Minimum orders (category)", 50, 500, 100, step=10, key="min_n_cat")
    cat_f = cat_late[cat_late["orders"] >= min_n_cat].sort_values("late_rate", ascending=False)
    if empty_state_guard(cat_f):
        fig_cat = px.bar(
            cat_f.head(20), x="category", y="late_rate",
            text=cat_f.head(20)["late_rate"].apply(lambda x: f"{x*100:.1f}%"),
            color="late_rate", color_continuous_scale="Greens",
            labels={"category": "Category", "late_rate": "Late Rate"},
        )
        fig_cat.update_layout(
            title="Top 20 Categories by Late Rate (filtered)",
            yaxis_tickformat=".1%", showlegend=False,
            plot_bgcolor="#F4F6FA", paper_bgcolor="white",
        )
        st.plotly_chart(fig_cat, width="stretch")

# ─── Section 4: Seller Pareto ─────────────────────────────────────────────────
section("Seller Pareto (Late Orders)", "Sellers with ≥ 20 single-seller orders in window")
precomputed_label()

pareto = load_seller_pareto()
conc = summary.get("seller", {}).get("seller_concentration", {})
c1, c2, c3 = st.columns(3)
c1.metric("Eligible Sellers (≥20 orders)", conc.get("eligible_sellers_ge_20_orders", "—"))
c2.metric("Worst 10% of eligible sellers: share of late orders", f"{conc.get('worst_10_share_of_all_late', 0)*100:.1f}% of all late",
          f"{conc.get('worst_10_share_of_pareto_late', 0)*100:.1f}% of eligible sellers' late orders on {conc.get('worst_10_share_of_pareto_orders', 0)*100:.1f}% of their orders", delta_color="off")
c3.metric("Worst 10% late rate", f"{conc.get('worst_10_late_rate', 0)*100:.1f}%",
          f"vs {conc.get('rest_90_late_rate', 0)*100:.1f}% for rest")

if not pareto.empty:
    fig_pareto = go.Figure()
    fig_pareto.add_trace(go.Bar(
        x=list(range(1, len(pareto)+1)), y=pareto["late_orders"],
        name="Late Orders", marker_color=RED, opacity=0.7,
    ))
    fig_pareto.add_trace(go.Scatter(
        x=list(range(1, len(pareto)+1)), y=pareto["cum_late_share"],
        name="Cumulative Late Share", yaxis="y2",
        line=dict(color=ORANGE, width=2), mode="lines",
    ))
    fig_pareto.update_layout(
        title="Seller Pareto Chart — Late Orders (sorted descending)",
        yaxis=dict(title="Late Orders"),
        yaxis2=dict(title="Cumulative Share", overlaying="y", side="right", tickformat=".0%"),
        plot_bgcolor="#F4F6FA", paper_bgcolor="white",
        legend=dict(orientation="h"),
    )
    st.plotly_chart(fig_pareto, width="stretch")
    download_csv(pareto, label="Download Pareto Data", filename="seller_pareto.csv")
