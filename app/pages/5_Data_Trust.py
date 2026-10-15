"""pages/5_Data_Trust.py - Page 5: join coverage, five robustness checks, limitations.

Every table is read from outputs/ (robustness_*.csv, out_funnel_waterfall.csv).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parents[1]
ROOT = APP_DIR.parent
for p in [str(APP_DIR), str(ROOT / "src")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from data import load_funnel_waterfall, load_robust_lateness, load_robust_first_sale, OUT  # noqa: E402
from ui import caveat_badge, section, download_csv, empty_state_guard  # noqa: E402

st.title("🛡️ Data Trust & Robustness")
st.caption("How far the numbers can be trusted: what the data covers, and whether the findings survive changing an analyst choice. "
           "The sidebar order filters do not apply on this page.")


@st.cache_data
def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(OUT / name)


# ─── 1. Coverage ──────────────────────────────────────────────────────────────
section("What the data can and cannot link",
        "Each stage counts distinct keys. Leads, deals and sellers are separate populations; nothing is attributed by guessing.")
wf = load_funnel_waterfall()
labels = {
    "all_leads": "All marketing leads (MQLs)",
    "closed_deals": "Closed deals (one seller each)",
    "deal_sellers_in_sellers_table": "Deal sellers present in the sellers table",
    "deal_sellers_in_order_items": "Deal sellers present in order items",
    "deal_sellers_with_delivered_order": "Deal sellers with at least one delivered order",
    "deals_matured_90d": "Deals with at least 90 days of data after closing",
    "matured_deals_first_sale_within_90d": "…of those, first observed sale within 90 days",
    "delivered_orders_from_deal_sellers": "Delivered orders from deal sellers",
    "item_gmv_deal_sellers": "Item GMV of those orders (BRL)",
    "delivered_orders_all": "Delivered orders, whole dataset",
    "NAIVE_join_rows_leads_x_deals_x_items": "Rows from a naive leads × deals × items join (fan-out, NOT used)",
}
cov = wf.assign(Stage=wf["stage"].map(labels).fillna(wf["stage"]))[["Stage", "value"]].rename(columns={"value": "Count"})
cov["Count"] = cov["Count"].map(lambda v: f"{v:,.0f}")
if empty_state_guard(cov):
    st.dataframe(cov, width="stretch", hide_index=True)
wd = dict(zip(wf["stage"], wf["value"]))
st.caption(f"Only {wd['deal_sellers_in_order_items']:.0f} of {wd['closed_deals']:.0f} closed-deal sellers can be followed into the order data (L-002), "
           f"so any statement about acquired sellers describes this subset. The naive join would produce {wd['NAIVE_join_rows_leads_x_deals_x_items']:,.0f} rows "
           f"from {wd['all_leads']:,.0f} leads, which is why every count here is on distinct keys.")

# ─── 2. Robustness ────────────────────────────────────────────────────────────
section("Five checks on analyst choices",
        "Each check re-runs a result under a different, reasonable choice. The baseline row equals the number used on the other pages.")

# a) bad-month threshold
st.markdown("**a · Bad-month threshold (8%, 10%, 12%)**")
bm = _read("robustness_bad_month.csv")
if empty_state_guard(bm):
    st.dataframe(bm[["threshold", "qualifying_months", "change_pp", "mix_effect_pp", "rate_effect_pp", "is_baseline"]]
                 .rename(columns={"change_pp": "Late-rate change (pp)", "mix_effect_pp": "Mix effect (pp)",
                                  "rate_effect_pp": "Rate effect (pp)", "is_baseline": "Baseline"}),
                 width="stretch", hide_index=True)
    if bm["qualifying_months"].nunique() == 1:
        st.caption("The same months qualify at every threshold, so the choice of 10% (D-017) does not drive the result.")
    else:
        st.caption("The set of bad months changes with the threshold; compare the rows above before relying on the 10% choice.")

# b) lateness definition
st.markdown("**b · Lateness defined by date or by timestamp**")
ld = load_robust_lateness()
if empty_state_guard(ld):
    view = ld[["definition", "late_orders", "late_rate", "one_star_gap_pp", "post_delivery_gap_pp", "dispatch_missed_risk_ratio"]].copy()
    view["late_rate"] = (view["late_rate"] * 100).round(2).astype(str) + "%"
    st.dataframe(view.rename(columns={"late_orders": "Late orders", "late_rate": "Late rate", "one_star_gap_pp": "Crude 1-star gap (pp)",
                                      "post_delivery_gap_pp": "Post-delivery 1-star gap (pp)",
                                      "dispatch_missed_risk_ratio": "Missed-dispatch risk ratio"}),
                 width="stretch", hide_index=True)
    st.caption("The estimated delivery date has no time of day, so a delivery at 14:00 on deadline day counts as late at timestamp level. "
               "Date level (D-012) avoids that artifact. The direction of the review gap and the dispatch risk ratio hold under both; "
               "the post-delivery review gap is smaller under the timestamp definition, so quote it as a range.")

# c) OR strata
st.markdown("**c · Adjusted odds ratio under three adjustment sets**")
orr = _read("robustness_or_strata.csv")
if empty_state_guard(orr):
    st.dataframe(orr[["strata_set", "n_strata_valid", "mh_or", "ci_lo", "ci_hi", "is_baseline"]].rename(
        columns={"strata_set": "Adjusted for", "n_strata_valid": "Strata used", "mh_or": "Mantel-Haenszel OR",
                 "ci_lo": "CI low", "ci_hi": "CI high", "is_baseline": "Baseline"}).round(2),
        width="stretch", hide_index=True)
    st.caption("Review timing is the confounder that matters: adjusting for it alone moves the odds ratio from the crude value to about 4, "
               "while customer state alone barely changes it. Adding state to timing refines the estimate without moving it much.")

# d) simulator
st.markdown("**d · Dispatch scenario under different seller eligibility cut-offs (worst 10% fixed)**")
sim = _read("robustness_simulator.csv")
sim10 = sim[(sim["pct_worst"] - 0.10).abs() < 1e-9]
if empty_state_guard(sim10):
    sv = sim10[["min_orders", "n_eligible_sellers", "n_fixed_sellers", "late_orders_avoided", "share_of_all_late",
                "est_1star_low", "est_1star_high", "is_baseline"]].copy()
    sv["share_of_all_late"] = (sv["share_of_all_late"] * 100).round(1).astype(str) + "%"
    st.dataframe(sv.rename(columns={"min_orders": "Min orders to be eligible", "n_eligible_sellers": "Eligible sellers",
                                    "n_fixed_sellers": "Sellers fixed", "late_orders_avoided": "Late orders avoided",
                                    "share_of_all_late": "Share of all late", "est_1star_low": "1-star avoided (low)",
                                    "est_1star_high": "1-star avoided (high)", "is_baseline": "Baseline"}),
                 width="stretch", hide_index=True)
    st.caption("A scenario, not a forecast. The size of the opportunity scales with how many sellers are eligible, but it stays a single-digit "
               "share of all late orders under every cut-off, so the conclusion (dispatch is secondary to transit) is unchanged.")

# e) first sale
st.markdown("**e · First observed sale measured at timestamp or date level**")
fs = load_robust_first_sale()
if empty_state_guard(fs):
    fv = fs[["definition", "first_sale_deals", "first_sale_rate", "chi2_p_value", "paid_rate", "organic_rate",
             "paid_vs_organic_diff_pp", "diff_ci_lo_pp", "diff_ci_hi_pp"]].copy()
    for c in ("first_sale_rate", "paid_rate", "organic_rate"):
        fv[c] = (fv[c] * 100).round(1).astype(str) + "%"
    st.dataframe(fv.rename(columns={"definition": "Definition", "first_sale_deals": "Deals with first sale",
                                    "first_sale_rate": "Rate", "chi2_p_value": "Origin chi-square p",
                                    "paid_rate": "Paid search", "organic_rate": "Organic search",
                                    "paid_vs_organic_diff_pp": "Paid − organic (pp)", "diff_ci_lo_pp": "CI low",
                                    "diff_ci_hi_pp": "CI high"}).round(3),
                 width="stretch", hide_index=True)
    st.caption("A difference of two deals moves the omnibus origin test across 0.05, so that p-value is fragile and should not be a headline. "
               "The paid-minus-organic interval stays above zero under both definitions, but the comparison was chosen after looking at the data "
               "and has no multiple-comparison correction (L-011): exploratory only.")
download_csv(fs, label="Download first-sale robustness table", filename="robustness_first_sale.csv")

# ─── 3. Limitations ───────────────────────────────────────────────────────────
section("Limitations that shape every conclusion")
st.markdown("""
- **L-001 · Sample:** a public Olist sample. "Not observed selling" does not mean "did not sell".
- **L-002 · Coverage:** only part of the closed-deal sellers appear in the order data (see the table above).
- **L-004 · No money data:** no cost, margin or acquisition cost, so nothing is costed and no return on investment is claimed.
- **L-008 · Lead fields:** SDR, segment and lead type exist only for closed deals, so they cannot explain which leads convert.
- **L-009 · Survey timing:** many reviews on late orders were written before delivery, so the crude review gap overstates the penalty of lateness.
- **L-010 · Selection:** acquired sellers are seen only if they appear in the order data; the funnel may recruit stronger sellers or they may have been strong anyway.
- **L-011 · Exploratory tests:** channel comparisons were chosen after viewing the data and are not corrected for multiple testing.
- **Association, not causation:** nothing here estimates a causal effect; the dispatch scenario is arithmetic, not a forecast.
""")
caveat_badge("Reproduce every number: python src/run_pipeline.py, then pytest. All app numbers are read from the files in outputs/.")
