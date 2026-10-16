"""pages/6_Action_Plan.py - Page 6: value at stake, ranked actions, pilot designs, risks.

Numbers are computed from outputs/ at render time. Effort ratings are analyst judgement and labelled as such.
No cost, margin or CAC data exists, so nothing here is a return-on-investment figure.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parents[1]
ROOT = APP_DIR.parent
for p in [str(APP_DIR), str(ROOT / "src")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from data import load_summary, load_orders, OUT  # noqa: E402
from ui import caveat_badge, section, download_csv, empty_state_guard  # noqa: E402

st.title("🧭 Action Plan")
st.caption("From findings to decisions: what is at stake, which action first, and how to prove it works. "
           "Full window; the sidebar order filters do not apply on this page.")


@st.cache_data
def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(OUT / name)


summary = load_summary()
kpi, fn = summary["kpi"], summary["funnel"]
orders = load_orders()
n_months = max(int(orders["purchase_month"].nunique()), 1)

# ─── 1. Value at stake ────────────────────────────────────────────────────────
section("1 · Value at stake", "Item value of the orders affected. This is exposure, not lost revenue and not profit.")
late = orders[orders["is_late"] == 1]
post1 = late[(late["review_score"] == 1) & (late["review_pre_delivery"] == 0)]
val_all = float(orders["item_value"].sum())
val_late = float(late["item_value"].sum())
val_post1 = float(post1["item_value"].sum())

c1, c2, c3 = st.columns(3)
c1.metric("Item value of late orders", f"BRL {val_late / 1e6:.2f} M",
          f"{val_late / val_all * 100:.1f}% of item value · {len(late):,} orders", delta_color="off",
          help="Price of items only (no freight). Late = delivered after the estimated date (D-012).")
c2.metric("…of which late orders with a 1-star review written after delivery", f"BRL {val_post1 / 1e6:.2f} M",
          f"{len(post1):,} orders", delta_color="off",
          help="Reviews written after delivery avoid the survey-timing bias (L-009).")
c3.metric("Item value, all delivered orders", f"BRL {val_all / 1e6:.2f} M", f"{len(orders):,} orders", delta_color="off")
caveat_badge("Exposure only: orders being late does not mean the value was lost. There is no cost, margin or acquisition-cost data (L-004), so no ROI is claimed.")

# ─── 2. Ranked actions ────────────────────────────────────────────────────────
section("2 · Which action first", "Impact comes from the data; effort is analyst judgement and should be replaced by the business's own estimate.")
lane = _read("stat_late_lane.csv").set_index("lane")
sim = _read("robustness_simulator.csv")
sim10 = sim[(sim["pct_worst"] - 0.10).abs() < 1e-9]
base10 = sim10[sim10["is_baseline"] == 1].iloc[0]
total_late = float(kpi["late_orders"])

rows = []
r1_avoid = None
if "SP->RJ" in lane.index and "SP->MG" in lane.index:
    rj, mg = lane.loc["SP->RJ"], lane.loc["SP->MG"]
    r1_avoid = float(rj["orders"] * (rj["late_rate"] - mg["late_rate"]))
    rows.append({
        "Action": "R1 · Carrier leg: pilot a second carrier on slow lanes",
        "Addressable late orders (scenario)": f"~{r1_avoid:,.0f}",
        "Share of all late": f"{r1_avoid / total_late * 100:.1f}%",
        "How sized": f"SP→RJ ({rj['orders']:,.0f} orders, {rj['late_rate'] * 100:.1f}% late) brought to the SP→MG rate ({mg['late_rate'] * 100:.1f}%)",
        "Effort (judgement)": "High",
    })
rows.append({
    "Action": "R2 · Seller dispatch scorecard for sellers who miss the shipping limit",
    "Addressable late orders (scenario)": f"~{base10['late_orders_avoided']:,.0f} (range {sim10['late_orders_avoided'].min():,.0f}–{sim10['late_orders_avoided'].max():,.0f})",
    "Share of all late": f"{base10['share_of_all_late'] * 100:.1f}% (range {sim10['share_of_all_late'].min() * 100:.1f}–{sim10['share_of_all_late'].max() * 100:.1f}%)",
    "How sized": f"Worst 10% of eligible sellers moved to the median dispatch time; range over eligibility cut-offs of {int(sim10['min_orders'].min())}–{int(sim10['min_orders'].max())} orders",
    "Effort (judgement)": "Medium",
})
rows.append({
    "Action": "R3 · Keep the funnel; test social and email follow-up",
    "Addressable late orders (scenario)": "not a delivery action",
    "Share of all late": "n/a",
    "How sized": f"Lead→deal {fn['lead_to_deal_rate'] * 100:.1f}% overall; the test asks whether a lower-converting channel is worth the SDR time. Needs cost per lead.",
    "Effort (judgement)": "Low",
})
actions = pd.DataFrame(rows)
if empty_state_guard(actions):
    st.dataframe(actions, width="stretch", hide_index=True)
    st.markdown(
        "**Suggested order:** start with **R2** (medium effort, no carrier negotiation, quick to measure) and **R3** (low effort), "
        "and open **R1** as the larger programme because the data says most of the delay sits in the carrier leg. "
        "**Do not add the R1 and R2 figures together:** the late orders they address overlap."
    )
    download_csv(actions, label="Download ranked actions", filename="action_plan.csv")

# ─── 3. Pilot designs ─────────────────────────────────────────────────────────
section("3 · How to prove it works", "Each action needs a controlled pilot, because everything above is an association in observational data.")

st.markdown("**Pilot size for R1 (two-proportion test, 5% significance, 80% power)**")
if "SP->RJ" in lane.index:
    p1 = float(lane.loc["SP->RJ", "late_rate"])
    lane_orders = float(lane.loc["SP->RJ", "orders"])
    delta = st.slider("Smallest reduction in late rate worth detecting (percentage points)", 1.0, float(min(8.0, p1 * 100 - 1)), 3.0, 0.5,
                      key="pilot_delta")
    p2 = p1 - delta / 100
    za, zb = 1.959964, 0.841621
    pbar = (p1 + p2) / 2
    n_arm = ((za * math.sqrt(2 * pbar * (1 - pbar)) + zb * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2) / (delta / 100) ** 2
    monthly = lane_orders / n_months
    weeks = (2 * n_arm) / (monthly / 4.345)
    a, b, c = st.columns(3)
    a.metric("Baseline late rate, SP→RJ", f"{p1 * 100:.1f}%")
    b.metric("Orders needed per arm", f"{math.ceil(n_arm):,}")
    c.metric("Weeks at average lane volume", f"{weeks:.0f}", f"{monthly:,.0f} orders a month on average", delta_color="off")
    st.caption("Assumes orders are randomly split between the current and the new carrier. Average volume over the whole window; "
               "peak months have more orders, so a pilot run in peak season finishes sooner but is not representative of normal months.")

with st.expander("R1 · Second-carrier pilot on SP→RJ"):
    st.markdown("""
- **Design:** randomly assign orders on the lane to the current or the new carrier for a fixed period outside peak months.
- **Primary metric:** late rate (date-level, D-012). **Secondary:** carrier transit days, post-delivery 1-star share, cost per order (to be measured, not in this data).
- **Guardrails:** cancellation rate and stock-outs on the lane; stop if the new carrier's late rate is worse by more than the noise floor shown above.
- **Decision rule:** set the success threshold with management before the pilot starts, not after seeing the results.
""")
with st.expander("R2 · Dispatch scorecard pilot"):
    st.markdown("""
- **Design:** among eligible sellers (at least 30 orders), randomly assign the flagged sellers to receive the scorecard and a dispatch target, or to continue as now.
- **Primary metric:** share of orders handed to the carrier by the shipping limit date. **Secondary:** late rate and post-delivery 1-star share of those sellers' orders.
- **Guardrails:** seller order volume, cancellations and listing removals (so the scorecard does not simply push sellers out).
- **Duration:** long enough to cover several hundred orders per group; check with the dispatch compliance rate in the Delivery Diagnostics page.
""")
with st.expander("R3 · Social and email follow-up test"):
    st.markdown("""
- **Design:** randomly assign new social and email leads to the current follow-up or to an enhanced SDR cadence.
- **Primary metric:** lead-to-deal rate with a confidence interval. **Secondary:** days to close and first observed sale within 90 days.
- **Needs:** SDR hours and cost per lead, which this data does not contain. Without them the test can show a conversion lift but not whether it pays.
- **Caution:** social and email have few deals (see the Acquisition Funnel page), so intervals will be wide; plan the sample before starting.
""")

# ─── 4. Risks ─────────────────────────────────────────────────────────────────
section("4 · What could go wrong")
st.markdown("""
- **Association is not causation.** Better dispatch or a new carrier may not deliver the gains the scenarios show; the pilots exist to find out.
- **Overlap.** The late orders addressed by R1 and R2 overlap, so the savings are not additive.
- **Selection.** Acquired sellers look stronger, but the funnel may simply have recruited stronger sellers (L-010).
- **Coverage.** Only part of the closed-deal sellers appear in the order data (L-002), so seller conclusions describe that subset.
- **Public sample, 2017–2018.** Carrier networks, volumes and customer expectations may have changed since.
- **No money data.** Costs, margins and acquisition costs are missing (L-004); a business case needs them before any commitment.
""")
