"""simulator.py – deterministic what-if scenario for dispatch improvement.

Logic (spec from docs/03_KPI_AND_ANALYSIS_SPEC.md):
  Input: top X% of worst sellers (by late_orders, min_orders threshold).
  For their orders: delay_new = delay - max(0, dispatch_time - median_dispatch).
  Count orders that flip from late (delay > 0) to on-time (delay_new <= 0).
  Estimated 1-star avoided = flipped_orders * (1star_rate_late - 1star_rate_ontime).

All computation is deterministic; no randomness, no ML.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _get_eligible_sellers(
    orders: pd.DataFrame,
    min_orders: int = 30,
) -> pd.DataFrame:
    """Return seller-level summary for eligible sellers.

    Eligible = in_window delivered single-seller stage_valid with min_orders.
    """
    sel = orders[
        (orders["in_window"] == 1)
        & (orders["delivered_valid"] == 1)
        & (orders["seller_id"].notna())
        & (orders["stage_valid"] == 1)
    ].copy()
    grp = (
        sel.groupby("seller_id")
        .agg(
            n_orders=("order_id", "count"),
            late_orders=("is_late", "sum"),
            avg_dispatch=("dispatch_days", "mean"),
        )
        .reset_index()
    )
    return grp[grp["n_orders"] >= min_orders].copy()


def run_scenario(
    orders: pd.DataFrame,
    pct_worst: float,
    min_orders: int = 30,
) -> dict:
    """Run one what-if scenario.

    Parameters
    ----------
    orders : DataFrame from out_app_orders (or fact_orders columns: order_id,
             seller_id, in_window, delivered_valid, stage_valid, is_late,
             delay_days, dispatch_days, review_score).
    pct_worst : fraction (0-1) of eligible sellers to 'fix'.
    min_orders : minimum orders for a seller to be eligible.

    Returns
    -------
    dict with keys: n_eligible_sellers, n_fixed_sellers, median_dispatch,
                    late_orders_avoided, share_of_all_late, est_1star_avoided.
    """
    eligible = _get_eligible_sellers(orders, min_orders=min_orders)
    if eligible.empty:
        return {
            "n_eligible_sellers": 0, "n_fixed_sellers": 0,
            "median_dispatch": float("nan"),
            "late_orders_avoided": 0, "share_of_all_late": float("nan"),
            "est_1star_avoided": 0,
        }

    median_dispatch = float(eligible["avg_dispatch"].median())

    n_fix = max(1, int(round(len(eligible) * pct_worst)))
    # worst = highest late_orders
    worst_sellers = set(
        eligible.nlargest(n_fix, "late_orders")["seller_id"].tolist()
    )

    # 1-star rates in the full window delivered orders
    window_orders = orders[
        (orders["in_window"] == 1) & (orders["delivered_valid"] == 1)
    ]
    reviewed = window_orders[window_orders["review_score"].notna()]
    rate_late_1star = (
        reviewed[reviewed["is_late"] == 1]["review_score"].eq(1).mean()
        if reviewed[reviewed["is_late"] == 1].shape[0] > 0
        else 0.0
    )
    rate_ontime_1star = (
        reviewed[reviewed["is_late"] == 0]["review_score"].eq(1).mean()
        if reviewed[reviewed["is_late"] == 0].shape[0] > 0
        else 0.0
    )

    # simulate for the fixed sellers' stage-valid orders
    fix_mask = (
        (orders["in_window"] == 1)
        & (orders["delivered_valid"] == 1)
        & (orders["stage_valid"] == 1)
        & (orders["seller_id"].isin(worst_sellers))
    )
    fix_orders = orders[fix_mask].copy()

    fix_orders["delay_reduction"] = (
        (fix_orders["dispatch_days"] - median_dispatch).clip(lower=0)
    )
    fix_orders["delay_new"] = fix_orders["delay_days"] - fix_orders["delay_reduction"]
    flipped = fix_orders[(fix_orders["is_late"] == 1) & (fix_orders["delay_new"] <= 0)]

    late_avoided = int(len(flipped))
    total_late = int(window_orders["is_late"].sum())
    share_avoided = late_avoided / total_late if total_late > 0 else float("nan")
    est_1star = late_avoided * (rate_late_1star - rate_ontime_1star)

    return {
        "n_eligible_sellers": int(len(eligible)),
        "n_fixed_sellers": n_fix,
        "median_dispatch": round(median_dispatch, 3),
        "late_orders_avoided": late_avoided,
        "share_of_all_late": round(share_avoided, 4),
        "est_1star_avoided": round(max(0, est_1star)),
    }


def run_scenarios(
    orders: pd.DataFrame,
    pcts: tuple[float, ...] = (0.05, 0.10, 0.20),
    min_orders: int = 30,
) -> pd.DataFrame:
    """Run multiple percentile scenarios; return a tidy DataFrame."""
    rows = []
    for pct in pcts:
        r = run_scenario(orders, pct, min_orders=min_orders)
        r["pct_worst"] = pct
        rows.append(r)
    return pd.DataFrame(rows)[
        ["pct_worst", "n_eligible_sellers", "n_fixed_sellers", "median_dispatch",
         "late_orders_avoided", "share_of_all_late", "est_1star_avoided"]
    ]
