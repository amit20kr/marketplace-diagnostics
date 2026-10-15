"""analysis.py – statistics layer: reads exports from SQLite pipeline,
computes statistical quantities (CIs, tests, shift-share, Mantel-Haenszel, simulator),
writes stat_*.csv and analysis_summary.json into --out.

Run from the project root via run_pipeline.py (which calls main()) or standalone:
    python src/analysis.py --out outputs [--orders outputs/app_orders.csv.gz]
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from stats import (
    wilson_ci,
    bootstrap_ci,
    mann_whitney,
    chi_square_table,
    mantel_haenszel_or,
    bootstrap_mh_or_ci,
    proportion_diff_ci,
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

    # 1. Origin conversion & downstream stats
    origin = _load(out_dir, "out_funnel_origin.csv")
    origin_rows = []
    for _, row in origin.iterrows():
        ld = int(row["leads"])
        dl = int(row["deals"])
        mat = int(row["matured_deals"])
        fs = int(row["first_sale_90_n"])
        lo_o, hi_o = wilson_ci(dl, ld) if ld > 0 else (float("nan"), float("nan"))
        lo_d, hi_d = wilson_ci(fs, mat) if mat > 0 else (float("nan"), float("nan"))
        origin_rows.append({
            "origin": row["origin"],
            "leads": ld,
            "deals": dl,
            "conv_rate": round(dl / ld, 4) if ld > 0 else None,
            "conv_lo": round(lo_o, 4) if not np.isnan(lo_o) else None,
            "conv_hi": round(hi_o, 4) if not np.isnan(hi_o) else None,
            "matured_deals": mat,
            "first_sale_90_n": fs,
            "downstream_rate": round(fs / mat, 4) if mat > 0 else None,
            "downstream_lo": round(lo_d, 4) if not np.isnan(lo_d) else None,
            "downstream_hi": round(hi_d, 4) if not np.isnan(hi_d) else None,
            "small_n": 1 if ld < 100 else 0,  # D-016
        })

    origin_df = pd.DataFrame(origin_rows)
    origin_df.to_csv(out_dir / "stat_funnel_origin.csv", index=False)

    # chi-square on lead->deal: origins with >= 100 leads (D-016)
    big_origins = origin_df[origin_df["small_n"] == 0]
    chi2_res = None
    if len(big_origins) >= 2:
        ct = pd.DataFrame({
            "deals": big_origins["deals"],
            "no_deal": big_origins["leads"] - big_origins["deals"],
        })
        chi2_res = chi_square_table(ct)

    # 2. Landing page stats
    landing = _load(out_dir, "out_funnel_landing.csv")
    landing_rows = []
    for _, row in landing.iterrows():
        ld = int(row["leads"])
        dl = int(row["deals"])
        lo_l, hi_l = wilson_ci(dl, ld) if ld > 0 else (float("nan"), float("nan"))
        landing_rows.append({
            "landing_page_id": row["landing_page_id"],
            "leads": ld,
            "deals": dl,
            "conv_rate": round(dl / ld, 4) if ld > 0 else None,
            "conv_lo": round(lo_l, 4) if not np.isnan(lo_l) else None,
            "conv_hi": round(hi_l, 4) if not np.isnan(hi_l) else None,
            "small_n": 1 if ld < 100 else 0,  # D-016
        })
    landing_df = pd.DataFrame(landing_rows)
    landing_df.to_csv(out_dir / "stat_funnel_landing.csv", index=False)

    # chi-square on landing pages with >= 100 leads
    big_landings = landing_df[landing_df["small_n"] == 0]
    chi2_landing = None
    if len(big_landings) >= 2:
        ct_land = pd.DataFrame({
            "deals": big_landings["deals"],
            "no_deal": big_landings["leads"] - big_landings["deals"],
        })
        chi2_landing = chi_square_table(ct_land)

    # 3. Downstream by origin (D-016: matured_deals >= 30)
    down_origins = origin_df[origin_df["matured_deals"] >= 30].copy()
    down_origins["small_n"] = 0
    small_down = origin_df[origin_df["matured_deals"] < 30].copy()
    small_down["small_n"] = 1
    down_combined = pd.concat([down_origins, small_down], ignore_index=True)
    down_csv = down_combined[[
        "origin", "matured_deals", "first_sale_90_n", "downstream_rate",
        "downstream_lo", "downstream_hi", "small_n"
    ]]
    down_csv.to_csv(out_dir / "stat_downstream_origin.csv", index=False)

    chi2_down = None
    if len(down_origins) >= 2:
        ct_down = pd.DataFrame({
            "first_sale": down_origins["first_sale_90_n"],
            "no_first_sale": down_origins["matured_deals"] - down_origins["first_sale_90_n"],
        })
        chi2_down = chi_square_table(ct_down)

    # Paid vs Organic downstream difference (exploratory, L-011)
    paid_row = origin_df[origin_df["origin"] == "paid_search"]
    org_row = origin_df[origin_df["origin"] == "organic_search"]
    po_res = None
    if not paid_row.empty and not org_row.empty:
        p_paid = float(paid_row.iloc[0]["downstream_rate"])
        n_paid = int(paid_row.iloc[0]["matured_deals"])
        p_org = float(org_row.iloc[0]["downstream_rate"])
        n_org = int(org_row.iloc[0]["matured_deals"])
        diff, diff_lo, diff_hi = proportion_diff_ci(p_paid, n_paid, p_org, n_org)
        po_res = {
            "paid_rate": round(p_paid, 4),
            "paid_matured": n_paid,
            "paid_first_sale": int(paid_row.iloc[0]["first_sale_90_n"]),
            "organic_rate": round(p_org, 4),
            "organic_matured": n_org,
            "organic_first_sale": int(org_row.iloc[0]["first_sale_90_n"]),
            "diff_pp": round(diff * 100, 2),
            "diff_ci_lo_pp": round(diff_lo * 100, 2),
            "diff_ci_hi_pp": round(diff_hi * 100, 2),
            "is_exploratory": True,
        }

    # 4. Days to close
    app_funnel = _load(out_dir, "app_funnel.csv")
    deals_data = app_funnel[app_funnel["is_deal"] == 1].copy()
    deals_with_dtc = deals_data[deals_data["days_to_close"].notna()]
    med_dtc = float(deals_with_dtc["days_to_close"].median()) if len(deals_with_dtc) > 0 else float("nan")
    share_30 = float((deals_with_dtc["days_to_close"] <= 30).mean()) if len(deals_with_dtc) > 0 else float("nan")
    share_90 = float((deals_with_dtc["days_to_close"] <= 90).mean()) if len(deals_with_dtc) > 0 else float("nan")

    # distribution bands
    dtc_vals = deals_with_dtc["days_to_close"]
    bands = [
        ("0-7 days", (dtc_vals <= 7)),
        ("8-14 days", (dtc_vals > 7) & (dtc_vals <= 14)),
        ("15-30 days", (dtc_vals > 14) & (dtc_vals <= 30)),
        ("31-60 days", (dtc_vals > 30) & (dtc_vals <= 60)),
        ("61-90 days", (dtc_vals > 60) & (dtc_vals <= 90)),
        ("91+ days", (dtc_vals > 90)),
    ]
    dtc_rows = []
    tot_dtc = len(deals_with_dtc)
    for band_name, mask in bands:
        cnt = int(mask.sum())
        dtc_rows.append({
            "band": band_name,
            "deals": cnt,
            "share": round(cnt / tot_dtc, 4) if tot_dtc > 0 else None,
        })
    dtc_df = pd.DataFrame(dtc_rows)
    dtc_df.to_csv(out_dir / "stat_days_to_close.csv", index=False)

    # 5. SDR table
    sdr_deals = deals_data[deals_data["sdr_id"].notna()]
    sdr_grp = (
        sdr_deals.groupby("sdr_id")
        .agg(
            deals=("mql_id", "count"),
            median_days_to_close=("days_to_close", "median"),
        )
        .reset_index()
        .sort_values("deals", ascending=False)
    )
    sdr_grp["small_n"] = (sdr_grp["deals"] < 10).astype(int)  # D-016
    sdr_grp.to_csv(out_dir / "stat_sdr.csv", index=False)

    total_sdr_deals = int(sdr_grp["deals"].sum())
    top3_deals = int(sdr_grp.head(3)["deals"].sum()) if len(sdr_grp) >= 3 else total_sdr_deals
    top3_share = top3_deals / total_sdr_deals if total_sdr_deals > 0 else float("nan")
    sdrs_ge_10 = int((sdr_grp["deals"] >= 10).sum())

    return {
        "leads": leads,
        "deals": deals,
        "lead_to_deal_rate": round(conv, 4),
        "lead_to_deal_ci_lo": round(lo, 4),
        "lead_to_deal_ci_hi": round(hi, 4),
        "chi2_origin": chi2_res,
        "chi2_landing": chi2_landing,
        "chi2_downstream": chi2_down,
        "paid_vs_organic": po_res,
        "days_to_close": {
            "median": round(med_dtc, 1),
            "share_within_30": round(share_30, 4),
            "share_within_90": round(share_90, 4),
        },
        "sdr": {
            "total_sdrs": int(len(sdr_grp)),
            "sdrs_ge_10_deals": sdrs_ge_10,
            "top3_deals": top3_deals,
            "top3_share": round(top3_share, 4),
        },
    }


# ─── review stats ─────────────────────────────────────────────────────────────

def review_stats(orders: pd.DataFrame, out_dir: Path) -> dict:
    w = orders[(orders["in_window"] == 1) & (orders["delivered_valid"] == 1)].copy()
    reviewed = w[w["review_score"].notna()].copy()

    late = reviewed[reviewed["is_late"] == 1]["review_score"].values
    ontime = reviewed[reviewed["is_late"] == 0]["review_score"].values

    mw = mann_whitney(late, ontime)

    # 1-star rates and bootstrap CI for the crude gap
    def one_star_rate(arr):
        return (arr == 1).mean()

    pt_late, lo_late, hi_late = bootstrap_ci(late, one_star_rate)
    pt_ontime, lo_ontime, hi_ontime = bootstrap_ci(ontime, one_star_rate)
    gap = pt_late - pt_ontime

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

    # Delay bands summary (stat_review_band.csv)
    band_order = ["on_time", "1-3", "4-7", "8+"]
    rb_rows = []
    for band in band_order:
        sub_b = reviewed[reviewed["delay_band"] == band]
        n_b = len(sub_b)
        n_1 = int((sub_b["review_score"] == 1).sum())
        mean_sc = float(sub_b["review_score"].mean()) if n_b > 0 else float("nan")
        p_1 = n_1 / n_b if n_b > 0 else float("nan")
        lo_1, hi_1 = wilson_ci(n_1, n_b) if n_b > 0 else (float("nan"), float("nan"))
        rb_rows.append({
            "delay_band": band,
            "n_orders": n_b,
            "mean_score": round(mean_sc, 4),
            "n_1star": n_1,
            "share_1star": round(p_1, 4),
            "share_1star_lo": round(lo_1, 4),
            "share_1star_hi": round(hi_1, 4),
        })
    rb_df = pd.DataFrame(rb_rows)
    rb_df.to_csv(out_dir / "stat_review_band.csv", index=False)

    # Timing split: post-delivery reviews only (review_pre_delivery == 0)
    post = reviewed[reviewed["review_pre_delivery"] == 0]
    post_late = post[post["is_late"] == 1]["review_score"].values
    post_ontime = post[post["is_late"] == 0]["review_score"].values
    post_1star_late = (post_late == 1).mean() if len(post_late) > 0 else float("nan")
    post_1star_ontime = (post_ontime == 1).mean() if len(post_ontime) > 0 else float("nan")
    post_gap = post_1star_late - post_1star_ontime

    # Crude OR
    pt_l = pt_late; pt_o = pt_ontime
    crude_or = (pt_l / (1 - pt_l)) / (pt_o / (1 - pt_o)) if (0 < pt_o < 1 and 0 < pt_l < 1) else float("nan")

    # Adjusted OR (D-023: review_pre_delivery x customer_state strata, outcome 1-star)
    reviewed["is_1star"] = (reviewed["review_score"] == 1).astype(int)
    mh_or_val, mh_lo, mh_hi, valid_strata = bootstrap_mh_or_ci(
        reviewed,
        strata_cols=["review_pre_delivery", "customer_state"],
        exposure_col="is_late",
        outcome_col="is_1star",
        n_boot=1000,
        ci=0.95,
        rng=42,
    )
    total_strata = int(reviewed.groupby(["review_pre_delivery", "customer_state"]).ngroups)

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
        "mh_or": round(float(mh_or_val), 4),
        "mh_or_ci": [round(float(mh_lo), 4), round(float(mh_hi), 4)],
        "strata_used": valid_strata,
        "strata_total": total_strata,
        "post_delivery_n_late": int(len(post_late)),
        "post_delivery_n_ontime": int(len(post_ontime)),
        "post_delivery_1star_late": round(float(post_1star_late), 4) if not np.isnan(post_1star_late) else None,
        "post_delivery_1star_ontime": round(float(post_1star_ontime), 4) if not np.isnan(post_1star_ontime) else None,
        "post_delivery_gap": round(float(post_gap), 4),
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

    # stat_shift_share_state.csv: breakdown per state with pp contributions
    ss_df = ss["breakdown"].copy()
    ss_df["normal_rate"] = ss_df["n_rate"]
    ss_df["bad_rate"] = ss_df["b_rate"]
    ss_df["rate_effect_pp"] = ss_df["rate_effect"] * 100
    ss_df["mix_effect_pp"] = ss_df["mix_effect"] * 100
    ss_df["total_effect_pp"] = ss_df["rate_effect_pp"] + ss_df["mix_effect_pp"]
    ss_export = ss_df[[
        "customer_state", "n_orders", "n_rate", "b_orders", "b_rate",
        "rate_effect_pp", "mix_effect_pp", "total_effect_pp"
    ]].rename(columns={"n_orders": "normal_orders", "b_orders": "bad_orders"}).sort_values(
        "rate_effect_pp", ascending=False
    )
    ss_export.round(4).to_csv(out_dir / "stat_shift_share_state.csv", index=False)

    # Stage decomposition on stage-valid orders: bad vs normal months
    stage_orders = w[w["stage_valid"] == 1].copy()
    stage_orders["period"] = stage_orders["purchase_month"].apply(
        lambda m: "bad" if m in bad_months else "normal"
    )
    stage_bn = (
        stage_orders.groupby("period")
        .agg(
            n_orders=("order_id", "count"),
            avg_dispatch_days=("dispatch_days", "mean"),
            avg_transit_days=("transit_days", "mean"),
            avg_promised_days=("promised_days", "mean"),
        )
        .reset_index()
    )
    stage_bn.round(4).to_csv(out_dir / "stat_stage_bad_vs_normal.csv", index=False)

    # Late vs on-time stage decomposition
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

    # State concentration: stat_late_state.csv
    state_agg = (
        w.groupby("customer_state")
        .agg(
            orders=("order_id", "count"),
            late_orders=("is_late", "sum"),
        )
        .reset_index()
        .sort_values("late_orders", ascending=False)
    )
    tot_late_all = int(w["is_late"].sum())
    state_agg["late_rate"] = state_agg["late_orders"] / state_agg["orders"]
    cis_st = [wilson_ci(lo, o) for lo, o in zip(state_agg["late_orders"], state_agg["orders"])]
    state_agg["ci_lo"] = [round(c[0], 4) for c in cis_st]
    state_agg["ci_hi"] = [round(c[1], 4) for c in cis_st]
    state_agg["share_of_all_late"] = round(state_agg["late_orders"] / tot_late_all, 4) if tot_late_all > 0 else 0
    state_agg["cum_share_of_late"] = round(state_agg["late_orders"].cumsum() / tot_late_all, 4) if tot_late_all > 0 else 0
    state_agg.to_csv(out_dir / "stat_late_state.csv", index=False)

    top3_states_share = float(state_agg.head(3)["late_orders"].sum() / tot_late_all) if tot_late_all > 0 else 0

    # Lane concentration: stat_late_lane.csv (lanes with >= 50 orders per D-016)
    lane_data = w[w["seller_state"].notna() & w["customer_state"].notna()].copy()
    lane_data["lane"] = lane_data["seller_state"] + "->" + lane_data["customer_state"]
    lane_agg = (
        lane_data.groupby("lane")
        .agg(
            orders=("order_id", "count"),
            late_orders=("is_late", "sum"),
        )
        .reset_index()
    )
    lane_agg = lane_agg[lane_agg["orders"] >= 50].sort_values("late_orders", ascending=False)
    lane_agg["late_rate"] = round(lane_agg["late_orders"] / lane_agg["orders"], 4)
    cis_ln = [wilson_ci(lo, o) for lo, o in zip(lane_agg["late_orders"], lane_agg["orders"])]
    lane_agg["ci_lo"] = [round(c[0], 4) for c in cis_ln]
    lane_agg["ci_hi"] = [round(c[1], 4) for c in cis_ln]
    lane_agg.to_csv(out_dir / "stat_late_lane.csv", index=False)

    # SP->RJ lane
    sp_rj = lane_agg[lane_agg["lane"] == "SP->RJ"]
    sp_rj_dict = sp_rj.iloc[0].to_dict() if not sp_rj.empty else {}

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
        "top3_states_share_of_late": round(top3_states_share, 4),
        "sp_rj_lane": sp_rj_dict,
    }


# ─── seller stats ─────────────────────────────────────────────────────────────

def seller_stats(orders: pd.DataFrame, out_dir: Path) -> dict:
    w = orders[(orders["in_window"] == 1) & (orders["delivered_valid"] == 1)].copy()

    # Deal sellers lookup
    kpi_seller = _load(out_dir, "out_kpi_seller.csv")
    deal_sellers = set(kpi_seller[kpi_seller["is_deal_seller"] == 1]["seller_id"])

    # 1. 2018 seller comparison: sellers with >= 10 single-seller delivered orders in 2018
    w_2018 = w[
        (w["n_sellers"] == 1)
        & (w["seller_id"].notna())
        & (w["purchase_month"] >= "2018-01")
        & (w["purchase_month"] <= "2018-08")
    ].copy()

    s_agg = (
        w_2018.groupby("seller_id")
        .agg(
            n_orders=("order_id", "count"),
            ontime_rate=("is_late", lambda s: float((s == 0).mean())),
            avg_dispatch=("dispatch_days", "mean"),
            avg_review=("review_score", "mean"),
        )
        .reset_index()
    )
    s_agg = s_agg[s_agg["n_orders"] >= 10].copy()
    s_agg["is_acquired"] = s_agg["seller_id"].isin(deal_sellers).astype(int)

    acq = s_agg[s_agg["is_acquired"] == 1]
    non = s_agg[s_agg["is_acquired"] == 0]

    compare_rows = []
    comp_dict = {
        "n_acquired_sellers": len(acq),
        "n_non_funnel_sellers": len(non),
        "metrics": {},
    }

    metrics = [
        ("ontime_rate", "On-time rate"),
        ("avg_dispatch", "Seller dispatch days"),
        ("avg_review", "Review score"),
    ]
    for col, label in metrics:
        v_acq = acq[col].dropna().values
        v_non = non[col].dropna().values
        med_acq = float(np.median(v_acq)) if len(v_acq) else float("nan")
        med_non = float(np.median(v_non)) if len(v_non) else float("nan")
        mw = mann_whitney(v_acq, v_non)
        compare_rows.append({
            "metric": label,
            "acquired_median": round(med_acq, 4),
            "non_funnel_median": round(med_non, 4),
            "mann_whitney_u": mw["u_stat"],
            "p_value": mw["p_value"],
            "p_display": mw["p_display"],
            "rank_biserial_r": round(mw["r_biserial"], 4),
        })
        comp_dict["metrics"][col] = {
            "acquired_median": round(med_acq, 4),
            "non_funnel_median": round(med_non, 4),
            "rank_biserial_r": round(mw["r_biserial"], 4),
            "p_value": mw["p_value"],
        }

    pd.DataFrame(compare_rows).to_csv(out_dir / "stat_seller_compare_2018.csv", index=False)

    # 2. Seller Pareto & concentration (single-seller orders in window, sellers >= 20 orders)
    single_orders = w[(w["n_sellers"] == 1) & (w["seller_id"].notna())]
    p_agg = (
        single_orders.groupby("seller_id")
        .agg(
            n_orders=("order_id", "count"),
            late_orders=("is_late", "sum"),
        )
        .reset_index()
    )
    p_agg = p_agg[p_agg["n_orders"] >= 20].sort_values("late_orders", ascending=False).reset_index(drop=True)
    p_agg["late_rate"] = round(p_agg["late_orders"] / p_agg["n_orders"], 4)

    tot_p_late = int(p_agg["late_orders"].sum())
    tot_p_orders = int(p_agg["n_orders"].sum())
    p_agg["cum_orders"] = p_agg["n_orders"].cumsum()
    p_agg["cum_late_orders"] = p_agg["late_orders"].cumsum()
    p_agg["cum_order_share"] = round(p_agg["cum_orders"] / tot_p_orders, 4) if tot_p_orders > 0 else 0
    p_agg["cum_late_share"] = round(p_agg["cum_late_orders"] / tot_p_late, 4) if tot_p_late > 0 else 0
    p_agg.to_csv(out_dir / "stat_seller_pareto.csv", index=False)

    # Concentration summary: worst 10%
    n_pareto_sellers = len(p_agg)
    n_worst_10 = int(round(n_pareto_sellers * 0.10))
    worst_10 = p_agg.head(n_worst_10)
    rest_90 = p_agg.iloc[n_worst_10:]

    tot_late_window = int(w["is_late"].sum())
    w10_late = int(worst_10["late_orders"].sum())
    w10_orders = int(worst_10["n_orders"].sum())
    r90_late = int(rest_90["late_orders"].sum())
    r90_orders = int(rest_90["n_orders"].sum())

    conc_dict = {
        "eligible_sellers_ge_20_orders": n_pareto_sellers,
        "worst_10_count": n_worst_10,
        "worst_10_late_orders": w10_late,
        "worst_10_orders": w10_orders,
        "worst_10_share_of_all_late": round(w10_late / tot_late_window, 4) if tot_late_window > 0 else None,
        "worst_10_share_of_pareto_late": round(w10_late / tot_p_late, 4) if tot_p_late > 0 else None,
        "worst_10_share_of_pareto_orders": round(w10_orders / tot_p_orders, 4) if tot_p_orders > 0 else None,
        "worst_10_late_rate": round(w10_late / w10_orders, 4) if w10_orders > 0 else None,
        "rest_90_late_rate": round(r90_late / r90_orders, 4) if r90_orders > 0 else None,
    }

    return {
        "seller_compare_2018": comp_dict,
        "seller_concentration": conc_dict,
    }


# ─── cohort stats ─────────────────────────────────────────────────────────────

def cohort_stats(orders: pd.DataFrame, out_dir: Path) -> dict:
    # 1. New definition cohorts from out_cohort_retention.csv (produced by sql/05 under D-025)
    cohort_new = _load(out_dir, "out_cohort_retention.csv")
    months_of_interest = ["2018-01", "2018-02", "2018-03", "2018-04", "2018-05"]
    sub_new = cohort_new[cohort_new["cohort_month"].isin(months_of_interest) & (cohort_new["observable"] == 1)]

    new_ret_rows = []
    comp_rows = []
    for k in [1, 2, 3]:
        # Acquired
        sk_acq = sub_new[(sub_new["k"] == k) & (sub_new["grp"] == "acquired")]
        act_acq = int(sk_acq["active_n"].sum())
        tot_acq = int(sk_acq["cohort_size"].sum())
        p_acq = act_acq / tot_acq if tot_acq > 0 else float("nan")
        lo_acq, hi_acq = wilson_ci(act_acq, tot_acq) if tot_acq > 0 else (float("nan"), float("nan"))
        new_ret_rows.append({
            "k": k, "grp": "acquired", "active": act_acq, "total": tot_acq,
            "retention": round(p_acq, 4), "ci_lo": round(lo_acq, 4), "ci_hi": round(hi_acq, 4),
        })

        # Non-funnel
        sk_non = sub_new[(sub_new["k"] == k) & (sub_new["grp"] == "non_funnel")]
        act_non = int(sk_non["active_n"].sum())
        tot_non = int(sk_non["cohort_size"].sum())
        p_non = act_non / tot_non if tot_non > 0 else float("nan")
        lo_non, hi_non = wilson_ci(act_non, tot_non) if tot_non > 0 else (float("nan"), float("nan"))
        new_ret_rows.append({
            "k": k, "grp": "non_funnel", "active": act_non, "total": tot_non,
            "retention": round(p_non, 4), "ci_lo": round(lo_non, 4), "ci_hi": round(hi_non, 4),
        })

        # Difference and Wald 95% CI
        diff, diff_lo, diff_hi = proportion_diff_ci(p_acq, tot_acq, p_non, tot_non)
        comp_rows.append({
            "k": k,
            "acquired_active": act_acq,
            "acquired_total": tot_acq,
            "acquired_retention": round(p_acq, 4),
            "non_funnel_active": act_non,
            "non_funnel_total": tot_non,
            "non_funnel_retention": round(p_non, 4),
            "diff_pp": round(diff * 100, 2),
            "diff_ci_lo_pp": round(diff_lo * 100, 2),
            "diff_ci_hi_pp": round(diff_hi * 100, 2),
        })

    pd.DataFrame(comp_rows).to_csv(out_dir / "stat_cohort_compare.csv", index=False)

    # 2. Old definition (single-seller delivered orders only) computed from orders
    kpi_seller = _load(out_dir, "out_kpi_seller.csv")
    deal_sellers = set(kpi_seller[kpi_seller["is_deal_seller"] == 1]["seller_id"])

    single = orders[(orders["n_sellers"] == 1) & (orders["seller_id"].notna())].copy()
    def str_to_mi(s):
        return int(s[:4]) * 12 + int(s[5:7])
    def mi_to_str(mi):
        y = (mi - 1) // 12
        m = (mi - 1) % 12 + 1
        return f"{y:04d}-{m:02d}"

    single["mi"] = single["purchase_month"].apply(str_to_mi)
    sm_df = single[["seller_id", "purchase_month", "mi"]].drop_duplicates()
    cohort_df = sm_df.groupby("seller_id")["mi"].min().reset_index().rename(columns={"mi": "cohort_mi"})
    cohort_df["cohort_month"] = cohort_df["cohort_mi"].apply(mi_to_str)
    cohort_df["grp"] = cohort_df["seller_id"].apply(lambda s: "acquired" if s in deal_sellers else "non_funnel")

    sub_c = cohort_df[cohort_df["cohort_month"].isin(months_of_interest)]
    check_rows = []
    for grp in ["acquired", "non_funnel"]:
        sg = sub_c[sub_c["grp"] == grp]
        tot = len(sg)
        for k in [1, 2, 3]:
            # check active
            active_cnt = 0
            for _, r in sg.iterrows():
                target_mi = r["cohort_mi"] + k
                if target_mi in sm_df[sm_df["seller_id"] == r["seller_id"]]["mi"].values:
                    active_cnt += 1
            check_rows.append({
                "definition": "old_single_seller_only",
                "grp": grp,
                "k": k,
                "active": active_cnt,
                "total": tot,
                "retention_rate": round(active_cnt / tot, 4) if tot > 0 else None,
            })

    # Append new definition rows to check file
    for r in new_ret_rows:
        check_rows.append({
            "definition": "new_all_delivered_items_d025",
            "grp": r["grp"],
            "k": r["k"],
            "active": r["active"],
            "total": r["total"],
            "retention_rate": r["retention"],
        })
    pd.DataFrame(check_rows).to_csv(out_dir / "stat_cohort_definition_check.csv", index=False)

    return {
        "monthly_retention_jan_may_2018": new_ret_rows,
        "cohort_compare": comp_rows,
    }


# ─── simulator stats ──────────────────────────────────────────────────────────

def simulator_stats(orders: pd.DataFrame, out_dir: Path) -> list[dict]:
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
    rv = review_stats(orders, out_dir)
    pd.DataFrame([{
        "is_late": k, "metric": "1star_rate",
        "value": rv["one_star_late"] if k == 1 else rv["one_star_ontime"],
    } for k in [1, 0]]).to_csv(out_dir / "stat_review_summary.csv", index=False)

    print("  [analysis] delivery stats …")
    dlv = delivery_stats(orders, out_dir)

    print("  [analysis] seller stats …")
    sel = seller_stats(orders, out_dir)

    print("  [analysis] cohort stats …")
    coh = cohort_stats(orders, out_dir)

    print("  [analysis] simulator …")
    sim = simulator_stats(orders, out_dir)

    summary = {
        "kpi": kpi,
        "funnel": fn,
        "reviews": rv,
        "delivery": dlv,
        "seller": sel,
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
