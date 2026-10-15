"""pages/3_Seller_Cohorts.py - Page 3: seller retention cohorts and acquired vs non-funnel comparison."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

APP_DIR = Path(__file__).resolve().parents[1]
ROOT = APP_DIR.parent
for p in [str(APP_DIR), str(ROOT / "src")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from data import load_summary, load_cohort_retention, load_cohort_compare, load_seller_compare_2018  # noqa: E402
from ui import (caveat_badge, precomputed_label, sql_expander, method_expander, section,  # noqa: E402
                download_csv, empty_state_guard, ORANGE, BLUE)

st.title("👥 Seller Cohorts")
st.caption("Cohort retention and acquired vs non-funnel sellers. Seller data: the sidebar order filters do not apply on this page.")

summary = load_summary()
sc = summary["seller"]["seller_compare_2018"]

# ─── Section 1: retention ─────────────────────────────────────────────────────
section("Seller retention by first-sale cohort",
        "A seller is active in a month if any delivered-valid order in that month contains one of its items (D-025). Cohort = month of first observed sale.")
precomputed_label()

ret = load_cohort_retention()
ret = ret[(ret["observable"] == 1) & (ret["k"] >= 1)].copy()
ret["retention"] = ret["active_n"] / ret["cohort_size"]
min_n = st.slider("Mask cells with cohort size below", 5, 50, 20, step=5, key="min_cohort_n",
                  help="Small cohorts give unstable percentages; they are blanked, not hidden.")
ret.loc[ret["cohort_size"] < min_n, "retention"] = np.nan

if empty_state_guard(ret):
    ca, cb = st.columns(2)
    for col, grp, title, scale in ((ca, "acquired", "Acquired (funnel) sellers", "Oranges"),
                                   (cb, "non_funnel", "Non-funnel sellers", "Blues")):
        sub = ret[ret["grp"] == grp]
        piv = sub.pivot(index="cohort_month", columns="k", values="retention")
        size = sub.groupby("cohort_month")["cohort_size"].first()
        piv.index = [f"{m} (n={int(size[m])})" for m in piv.index]
        with col:
            st.markdown(f"**{title}**")
            if piv.notna().any().any():
                fig = px.imshow(piv, text_auto=".0%", color_continuous_scale=scale, zmin=0, zmax=1,
                                labels={"x": "Months after first sale", "y": "Cohort", "color": "Retention"})
                fig.update_layout(coloraxis_showscale=False, paper_bgcolor="white", margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig, width="stretch")
            else:
                st.warning("Every cell is below the minimum cohort size. Lower the slider.")
    caveat_badge("Blank cells: cohort too small (see slider) or not enough months observed after the first sale (censoring).")

st.markdown("**Acquired minus non-funnel, Jan–May 2018 cohorts pooled**")
cc = load_cohort_compare()
if empty_state_guard(cc):
    show = cc[["k", "acquired_active", "acquired_total", "acquired_retention", "non_funnel_active", "non_funnel_total",
               "non_funnel_retention", "diff_pp", "diff_ci_lo_pp", "diff_ci_hi_pp"]].copy()
    show["CI excludes 0?"] = np.where((show["diff_ci_lo_pp"] > 0) | (show["diff_ci_hi_pp"] < 0), "yes", "no")
    st.dataframe(show.rename(columns={
        "k": "Month after first sale", "acquired_active": "Acq. active", "acquired_total": "Acq. n",
        "acquired_retention": "Acq. retention", "non_funnel_active": "Non-funnel active", "non_funnel_total": "Non-funnel n",
        "non_funnel_retention": "Non-funnel retention", "diff_pp": "Diff (pp)", "diff_ci_lo_pp": "CI low", "diff_ci_hi_pp": "CI high"}),
        width="stretch", hide_index=True)
    m1 = cc[cc["k"] == 1].iloc[0]
    st.caption(f"Month 1: difference {m1['diff_pp']:+.1f} pp with CI {m1['diff_ci_lo_pp']:.1f} to {m1['diff_ci_hi_pp']:.1f}, so no clear difference. "
               "Later months are compared in the same table.")
download_csv(cc, label="Download cohort comparison", filename="cohort_compare.csv")
sql_expander("Cohort retention (D-025)", "05_cohorts.sql")

# ─── Section 2: seller comparison ─────────────────────────────────────────────
section("Acquired vs non-funnel sellers, 2018",
        f"{sc['n_acquired_sellers']} acquired vs {sc['n_non_funnel_sellers']} non-funnel sellers with at least 10 single-seller delivered orders (D-018)")
precomputed_label()
caveat_badge("Selection (L-010): sellers are seen only if they appear in the order data and cohorts start at the first observed sale. "
             "The funnel may recruit stronger sellers, or they may have been strong anyway.")

cmp_df = load_seller_compare_2018()
if empty_state_guard(cmp_df):
    cols = st.columns(len(cmp_df))
    for col, (_, r) in zip(cols, cmp_df.iterrows()):
        with col:
            fig = go.Figure(go.Bar(x=["Acquired", "Non-funnel"], y=[r["acquired_median"], r["non_funnel_median"]],
                                   text=[f"{r['acquired_median']:.2f}", f"{r['non_funnel_median']:.2f}"],
                                   textposition="outside", marker_color=[ORANGE, BLUE]))
            fig.update_layout(title=f"{r['metric']} (median)", showlegend=False, plot_bgcolor="#F4F6FA",
                              paper_bgcolor="white", margin=dict(l=10, r=10, t=50, b=10), height=300)
            st.plotly_chart(fig, width="stretch")
            st.caption(f"Rank-biserial r = {r['rank_biserial_r']:+.2f} · Mann-Whitney p = {r['p_display']}")
    download_csv(cmp_df, label="Download seller comparison", filename="seller_compare_2018.csv")

method_expander("Mann-Whitney effect size (D-027)",
                "Seller-level values compared with a Mann-Whitney U test. Rank-biserial r = 2U/(n_a·n_b) − 1, range −1 to 1; "
                "positive r means acquired sellers tend to have higher values. For dispatch days a negative r means acquired sellers are faster. "
                "With hundreds of sellers a small p-value is easy to reach, so the effect size (about 0.3, moderate) matters more than p.")
