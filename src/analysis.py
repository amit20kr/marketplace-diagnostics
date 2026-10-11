"""analysis.py – statistics layer: reads out_*.csv exports from the SQLite pipeline,
computes statistical quantities (CIs, tests, shift-share, Mantel-Haenszel, simulator),
writes stat_*.csv and analysis_summary.json into --out.

Run from the project root via run_pipeline.py (which calls main()) or standalone:
    python src/analysis.py --out outputs [--orders outputs/app_orders.csv.gz]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from stats import (
    wilson_ci,
    bootstrap_ci,
    mann_whitney,
    chi_square_table,
    mantel_haenszel_or,
    shift_share,
)
from simulator import run_scenarios


# ─── helpers ─────────────────────────────────────────────────────────────────

def _load(out_dir: Path, name: str) -> pd.DataFrame:
    p = out_dir / name
    if p.exists():
        return pd.read_csv(p)
    raise FileNotFoundError(f"Expected {p}")


# ─── funnel stats ─────────────────────────────────────────────────────────────

def funnel_stats(out_dir: Path) -> dict:
    wf = _load(out_dir, "out_funnel_waterfall.csv")
    wf_d = dict(zip(wf["stage"], wf["value"]))
    leads = int(wf_d.get("all_leads", 0))
    deals = int(wf_d.get("closed_deals", 0))
    lo, hi = wilson_ci(deals, leads)
    conv = deals / leads if leads else float("nan")

    origin = _load(out_dir, "out_funnel_origin.csv")
    origin_cis = []
    for _, row in origin.iterrows():
        lo_o, hi_o = wilson_ci(int(row["deals"]), int(row["leads"]))
        lo_d, hi_d = (
            wilson_ci(int(row["first_sale_90_n"]), int(row["matured_deals"]))
            if row["matured_deals"] > 0
            else (float("nan"), float("nan"))
        )
        origin_cis.append({
            "origin": row["origin"],
            "leads": int(row["leads"]),
            "deals": int(row["deals"]),
            "conv_rate": round(row["deals"] / row["leads"], 4) if row["leads"] > 0 else None,
            "conv_lo": round(lo_o, 4), "conv_hi": round(hi_o, 4),
            "matured_deals": int(row["matured_deals"]),
            "first_sale_90_n": int(row["first_sale_90_n"]),
            "downstream_rate": round(row["first_sale_90_n"] / row["matured_deals"], 4) if row["matured_deals"] > 0 else None,
            "downstream_lo": round(lo_d, 4) if not np.isnan(lo_d) else None,
            "downstream_hi": round(hi_d, 4) if not np.isnan(hi_d) else None,
        })

    # chi-square: origin vs deal/no-deal (D-016: include only origins >=100 leads)
    big_origins = [o for o in origin_cis if o["leads"] >= 100]
    chi2_res = None
    if len(big_origins) >= 2:
        ct = pd.DataFrame(big_origins)[["deals", "leads"]].copy()
        ct["no_deal"] = ct["leads"] - ct["deals"]
        chi2_res = chi_square_table(ct[["deals", "no_deal"]])

    return {
        "leads": leads, "deals": deals,
        "lead_to_deal_rate": round(conv, 4),
        "lead_to_deal_ci_lo": round(lo, 4), "lead_to_deal_ci_hi": round(hi, 4),
        "origin_cis": origin_cis,
        "chi2_origin": chi2_res,
    }


# ─── review stats ─────────────────────────────────────────────────────────────

def review_stats(orders: pd.DataFrame) -> dict:
    w = orders[(orders["in_window"] == 1) & (orders["delivered_valid"] == 1)].copy()
    reviewed = w[w["review_score"].notna()].copy()

    late = reviewed[reviewed["is_late"] == 1]["review_score"].values
    ontime = reviewed[reviewed["is_late"] == 0]["review_score"].values

    mw = mann_whitney(late, ontime)

    # 1-star rates and bootstrap CI for the gap
    def one_star_rate(arr):
        return (arr == 1).mean()

    pt_late, lo_late, hi_late = bootstrap_ci(late, one_star_rate)
    pt_ontime, lo_ontime, hi_ontime = bootstrap_ci(ontime, one_star_rate)
    gap = pt_late - pt_ontime
    # approximate CI for gap using percentile bootstrap on difference
    rng_obj = np.random.default_rng(42)
    n_boot = 2000
    boots_gap = [
        one_star_rate(rng_obj.choice(late, size=len(late), replace=True))
        - one_star_rate(rng_obj.choice(ontime, size=len(ontime), replace=True))
        for _ in range(n_boot)
    ]
    boots_gap_sorted = sorted(boots_gap)
    gap_lo = boots_gap_sorted[int(n_boot * 0.025)]
    gap_hi = boots_gap_sorted[int(n_boot * 0.975)]

    # Mantel-Haenszel: strata by delay_band
    strata = []
    for band in ["1-3", "4-7", "8+"]:
        sub = reviewed[reviewed["delay_band"] == band]
        a = int((sub["review_score"] == 1).sum())
        b = int((sub["review_score"] != 1).sum())
        sub_ontime = reviewed[reviewed["delay_band"] == "on_time"]
        c = int((sub_ontime["review_score"] == 1).sum())
        d = int((sub_ontime["review_score"] != 1).sum())
        strata.append((a, b, c, d))

    mh = mantel_haenszel_or(strata)

    # timing split: post-delivery reviews only
    post = reviewed[reviewed["review_pre_delivery"] == 0]
    post_late = post[post["is_late"] == 1]["review_score"].values
    post_ontime = post[post["is_late"] == 0]["review_score"].values
    post_1star_late = (post_late == 1).mean() if len(post_late) > 0 else float("nan")
    post_1star_ontime = (post_ontime == 1).mean() if len(post_ontime) > 0 else float("nan")

    # crude OR
    pt_l = pt_late; pt_o = pt_ontime
    crude_or = (pt_l / (1 - pt_l)) / (pt_o / (1 - pt_o)) if (0 < pt_o < 1 and 0 < pt_l < 1) else float("nan")

    return {
        "n_late_reviewed": int(len(late)),
        "n_ontime_reviewed": int(len(ontime)),
        "avg_review_late": round(float(np.mean(late)), 4) if len(late) else None,
        "avg_review_ontime": round(float(np.mean(ontime)), 4) if len(ontime) else None,
        "one_star_late": round(float(pt_late), 4),
        "one_star_ontime": round(float(pt_ontime), 4),
        "one_star_late_ci": [round(lo_late, 4), round(hi_late, 4)],
        "one_star_ontime_ci": [round(lo_ontime, 4), round(hi_ontime, 4)],
        "one_star_gap": round(float(gap), 4),
        "one_star_gap_ci": [round(gap_lo, 4), round(gap_hi, 4)],
        "mann_whitney": mh_dict(mw),
        "crude_or": round(float(crude_or), 4) if not np.isnan(crude_or) else None,
        "mh_or": round(float(mh["mh_or"]), 4),
        "mh_n_strata": int(mh["n_strata"]),
        "post_delivery_n_late": int(len(post_late)),
        "post_delivery_n_ontime": int(len(post_ontime)),
        "post_delivery_1star_late": round(float(post_1star_late), 4) if not np.isnan(post_1star_late) else None,
        "post_delivery_1star_ontime": round(float(post_1star_ontime), 4) if not np.isnan(post_1star_ontime) else None,
    }


def mh_dict(d: dict) -> dict:
    return {k: (round(float(v), 4) if isinstance(v, float) else v) for k, v in d.items()}


# ─── delivery stats ───────────────────────────────────────────────────────────

def delivery_stats(orders: pd.DataFrame, out_dir: Path) -> dict:
    w = orders[(orders["in_window"] == 1) & (orders["delivered_valid"] == 1)].copy()

    # shift-share: bad months = late_rate > 10%
    monthly = _load(out_dir, "out_kpi_monthly.csv")
    bad_months = set(monthly[monthly["late_rate"] > 0.10]["month"].tolist())
    monthly["is_bad"] = monthly["month"].isin(bad_months)

    # state-level detail for shift-share
    state_month = _load(out_dir, "out_late_month_state.csv")
    state_month["is_bad"] = state_month["month"].isin(bad_months)
    normal_state = (
        state_month[~state_month["is_bad"]]
        .groupby("customer_state")[["orders", "late_orders"]]
        .sum()
        .reset_index()
    )
    bad_state = (
        state_month[state_month["is_bad"]]
        .groupby("customer_state")[["orders", "late_orders"]]
        .sum()
        .reset_index()
    )

    ss = shift_share(normal_state, bad_state, "customer_state", "orders", "late_orders")

    # stage decomposition on late orders
    late_orders = w[w["is_late"] == 1]
    ontime_orders = w[w["is_late"] == 0]
    late_sv = late_orders[late_orders["stage_valid"] == 1]
    ontime_sv = ontime_orders[ontime_orders["stage_valid"] == 1]

    avg_dispatch_late = float(late_sv["dispatch_days"].mean()) if len(late_sv) > 0 else float("nan")
    avg_dispatch_ontime = float(ontime_sv["dispatch_days"].mean()) if len(ontime_sv) > 0 else float("nan")
    avg_transit_late = float(late_sv["transit_days"].mean()) if len(late_sv) > 0 else float("nan")
    avg_transit_ontime = float(ontime_sv["transit_days"].mean()) if len(ontime_sv) > 0 else float("nan")

    extra_dispatch = avg_dispatch_late - avg_dispatch_ontime
    extra_transit = avg_transit_late - avg_transit_ontime
    extra_total = extra_dispatch + extra_transit
    pct_dispatch = extra_dispatch / extra_total if extra_total != 0 else float("nan")
    pct_transit = extra_transit / extra_total if extra_total != 0 else float("nan")

    # dispatch compliance
    comp_data = w[w["dispatch_compliant"].notna()].copy()
    missed = comp_data[comp_data["dispatch_compliant"] == 0]
    met = comp_data[comp_data["dispatch_compliant"] == 1]
    late_rate_missed = float(missed["is_late"].mean()) if len(missed) > 0 else float("nan")
    late_rate_met = float(met["is_late"].mean()) if len(met) > 0 else float("nan")
    rr = late_rate_missed / late_rate_met if late_rate_met > 0 else float("nan")

    return {
        "bad_months": sorted(bad_months),
        "baseline_late_rate": round(ss["baseline_rate"], 4),
        "bad_months_late_rate": round(ss["bad_rate"], 4),
        "shift_share_change": round(ss["change"], 4),
        "shift_share_mix_effect": round(ss["mix_effect"], 4),
        "shift_share_rate_effect": round(ss["rate_effect"], 4),
        "avg_dispatch_late": round(avg_dispatch_late, 4) if not np.isnan(avg_dispatch_late) else None,
        "avg_dispatch_ontime": round(avg_dispatch_ontime, 4) if not np.isnan(avg_dispatch_ontime) else None,
        "avg_transit_late": round(avg_transit_late, 4) if not np.isnan(avg_transit_late) else None,
        "avg_transit_ontime": round(avg_transit_ontime, 4) if not np.isnan(avg_transit_ontime) else None,
        "extra_dispatch_days": round(extra_dispatch, 4) if not np.isnan(extra_dispatch) else None,
        "extra_transit_days": round(extra_transit, 4) if not np.isnan(extra_transit) else None,
        "pct_extra_dispatch": round(pct_dispatch, 4) if not np.isnan(pct_dispatch) else None,
        "pct_extra_transit": round(pct_transit, 4) if not np.isnan(pct_transit) else None,
        "dispatch_missed_n": int(len(missed)),
        "dispatch_met_n": int(len(met)),
        "dispatch_missed_late_rate": round(late_rate_missed, 4) if not np.isnan(late_rate_missed) else None,
        "dispatch_met_late_rate": round(late_rate_met, 4) if not np.isnan(late_rate_met) else None,
        "dispatch_missed_risk_ratio": round(rr, 4) if not np.isnan(rr) else None,
        "dispatch_missed_pct_of_late": round(len(missed[missed["is_late"] == 1]) / float(w["is_late"].sum()), 4)
            if w["is_late"].sum() > 0 else None,
    }


# ─── simulator stats ──────────────────────────────────────────────────────────

def simulator_stats(orders: pd.DataFrame, out_dir: Path) -> dict:
    # The simulator needs in_window, delivered_valid, stage_valid, seller_id, is_late,
    # delay_days, dispatch_days, review_score columns.
    needed = {"in_window", "delivered_valid", "stage_valid", "seller_id",
              "is_late", "delay_days", "dispatch_days", "review_score", "order_id"}
    # app_orders doesn't have in_window/delivered_valid; add them as constant 1 since
    # app_orders is already filtered to in_window=1 AND delivered_valid=1
    sim_orders = orders.copy()
    if "in_window" not in sim_orders.columns:
        sim_orders["in_window"] = 1
    if "delivered_valid" not in sim_orders.columns:
        sim_orders["delivered_valid"] = 1
    if "order_id" not in sim_orders.columns:
        sim_orders["order_id"] = range(len(sim_orders))

    scenarios = run_scenarios(sim_orders, pcts=(0.05, 0.10, 0.20), min_orders=30)
    scenarios.to_csv(out_dir / "stat_simulator.csv", index=False)
    return scenarios.to_dict("records")


# ─── cohort stats ─────────────────────────────────────────────────────────────

def cohort_stats(out_dir: Path) -> dict:
    cohort = _load(out_dir, "out_cohort_retention.csv")
    # Focus on Jan-May 2018 cohorts (preliminary result); month 1 and 2 retention
    months_of_interest = ["2018-01", "2018-02", "2018-03", "2018-04", "2018-05"]
    sub = cohort[cohort["cohort_month"].isin(months_of_interest) & (cohort["observable"] == 1)]

    rows = []
    for k in [1, 2, 3]:
        for grp in ["acquired", "non_funnel"]:
            sk = sub[(sub["k"] == k) & (sub["grp"] == grp)]
            active = int(sk["active_n"].sum())
            total = int(sk["cohort_size"].sum())
            lo, hi = wilson_ci(active, total)
            rows.append({
                "k": k, "grp": grp, "active": active, "total": total,
                "retention": round(active / total, 4) if total > 0 else None,
                "ci_lo": round(lo, 4), "ci_hi": round(hi, 4),
            })
    return {"monthly_retention_jan_may_2018": rows}


# ─── overall KPI summary ──────────────────────────────────────────────────────

def overall_kpi(out_dir: Path) -> dict:
    overall = _load(out_dir, "out_kpi_overall.csv")
    if len(overall) == 0:
        return {}
    r = overall.iloc[0]
    n = int(r["delivered_valid_orders"])
    late = int(r["late_orders"])
    lo, hi = wilson_ci(late, n)
    return {
        "delivered_valid_orders": n,
        "late_orders": late,
        "late_rate": round(float(r["late_rate"]), 4),
        "late_rate_ci_lo": round(lo, 4),
        "late_rate_ci_hi": round(hi, 4),
        "avg_review": round(float(r["avg_review"]), 4),
        "one_star_share": round(float(r["one_star_share"]), 4),
        "avg_dispatch_days": round(float(r["avg_dispatch_days"]), 4),
        "avg_transit_days": round(float(r["avg_transit_days"]), 4),
        "dispatch_compliance": round(float(r["dispatch_compliance"]), 4),
        "gmv_items": round(float(r["gmv_items"]), 2),
        "aov": round(float(r["aov"]), 4),
        "freight_to_item_value": round(float(r["freight_to_item_value"]), 4),
        "single_seller_orders": int(r["single_seller_orders"]),
        "multi_seller_orders": int(r["multi_seller_orders"]),
    }


# ─── main ─────────────────────────────────────────────────────────────────────

def main(out_dir: Path, orders_path: Path | None = None) -> None:
    out_dir = Path(out_dir)

    if orders_path is None:
        orders_path = out_dir / "app_orders.csv.gz"
        if not orders_path.exists():
            orders_path = out_dir / "app_orders.csv"

    print(f"  [analysis] loading orders from {orders_path}")
    orders = pd.read_csv(orders_path)

    # analysis.py gets app_orders which is already filtered; add sentinel columns
    orders["in_window"] = 1
    orders["delivered_valid"] = 1
    if "order_id" not in orders.columns:
        orders = orders.reset_index().rename(columns={"index": "order_id"})

    print("  [analysis] overall KPIs …")
    kpi = overall_kpi(out_dir)

    print("  [analysis] funnel stats …")
    fn = funnel_stats(out_dir)

    print("  [analysis] review stats …")
    rv = review_stats(orders)
    pd.DataFrame([{
        "is_late": k, "metric": "1star_rate",
        "value": rv["one_star_late"] if k == 1 else rv["one_star_ontime"],
    } for k in [1, 0]]).to_csv(out_dir / "stat_review_summary.csv", index=False)

    print("  [analysis] delivery stats …")
    dlv = delivery_stats(orders, out_dir)

    print("  [analysis] cohort stats …")
    coh = cohort_stats(out_dir)

    print("  [analysis] simulator …")
    sim = simulator_stats(orders, out_dir)

    # Write origin CIs as a CSV
    pd.DataFrame(fn.pop("origin_cis")).to_csv(out_dir / "stat_funnel_origin_ci.csv", index=False)

    summary = {
        "kpi": kpi,
        "funnel": fn,
        "reviews": rv,
        "delivery": dlv,
        "cohorts": coh,
        "simulator": sim,
    }

    out_path = out_dir / "analysis_summary.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  [analysis] wrote {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--orders", default=None)
    args = parser.parse_args()
    main(Path(args.out), Path(args.orders) if args.orders else None)
