"""stats.py – statistical helpers used by analysis.py and the Streamlit app.

All functions are pure (no side effects). The app must import from here;
do not duplicate the formulas in app pages.
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np
import pandas as pd
from scipy import stats as sps


# ─── Wilson CI ───────────────────────────────────────────────────────────────

def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score 95% CI for a proportion. Returns (lo, hi) in [0, 1]."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, centre - half), min(1.0, centre + half))


# ─── Bootstrap CI ────────────────────────────────────────────────────────────

def bootstrap_ci(
    arr: np.ndarray,
    stat_fn,
    n_boot: int = 2000,
    ci: float = 0.95,
    rng: int = 42,
) -> tuple[float, float, float]:
    """Percentile bootstrap CI.

    Returns (point_estimate, lo, hi).
    """
    rng_obj = np.random.default_rng(rng)
    boots = [stat_fn(rng_obj.choice(arr, size=len(arr), replace=True)) for _ in range(n_boot)]
    boots = np.sort(boots)
    alpha = 1 - ci
    lo_idx = int(n_boot * alpha / 2)
    hi_idx = int(n_boot * (1 - alpha / 2))
    return (stat_fn(arr), float(boots[lo_idx]), float(boots[min(hi_idx, n_boot - 1)]))


# ─── Mann-Whitney ─────────────────────────────────────────────────────────────

def mann_whitney(a: np.ndarray, b: np.ndarray) -> dict:
    """Mann-Whitney U test plus rank-biserial correlation (effect size).

    r = 1 - 2U/(n_a * n_b).  Range [-1, 1]; >0 means group a tends to rank higher.
    """
    if len(a) == 0 or len(b) == 0:
        return {"u_stat": float("nan"), "p_value": float("nan"), "r_biserial": float("nan"),
                "n_a": len(a), "n_b": len(b)}
    u, p = sps.mannwhitneyu(a, b, alternative="two-sided")
    r = 1 - 2 * u / (len(a) * len(b))
    return {"u_stat": float(u), "p_value": float(p), "r_biserial": float(r),
            "n_a": int(len(a)), "n_b": int(len(b))}


# ─── Chi-square ──────────────────────────────────────────────────────────────

def chi_square_table(observed: pd.DataFrame) -> dict:
    """Chi-square test on a contingency table (rows = groups, cols = outcomes).

    Returns chi2, p, dof, cramers_v.
    """
    chi2, p, dof, _ = sps.chi2_contingency(observed.values)
    n = observed.values.sum()
    min_dim = min(observed.shape) - 1
    cramers_v = math.sqrt(chi2 / (n * max(min_dim, 1)))
    return {"chi2": float(chi2), "p_value": float(p), "dof": int(dof), "cramers_v": float(cramers_v)}


# ─── Mantel-Haenszel ─────────────────────────────────────────────────────────

def mantel_haenszel_or(strata: list[tuple[int, int, int, int]]) -> dict:
    """Mantel-Haenszel adjusted odds ratio (point estimate; no CI – L-012).

    Each stratum is (a, b, c, d) in a 2×2: late+bad/late+ok/ontime+bad/ontime+ok.
    Specifically: a=late&1star, b=late&not1star, c=ontime&1star, d=ontime&not1star.
    Returns {"mh_or": float, "n_strata": int}.
    """
    num, denom = 0.0, 0.0
    valid = 0
    for a, b, c, d in strata:
        n = a + b + c + d
        if n == 0:
            continue
        num += a * d / n
        denom += b * c / n
        valid += 1
    mh_or = num / denom if denom != 0 else float("nan")
    return {"mh_or": float(mh_or), "n_strata": valid}


# ─── Shift-share ─────────────────────────────────────────────────────────────

def shift_share(
    normal_df: pd.DataFrame,
    bad_df: pd.DataFrame,
    group_col: str,
    orders_col: str,
    late_col: str,
) -> dict:
    """Shift-share decomposition: change = mix effect + rate effect.

    normal_df / bad_df each have group_col, orders_col (count), late_col (count).
    Returns a dict with baseline_rate, bad_rate, change, mix_effect, rate_effect,
    and a breakdown DataFrame.
    """
    n_df = normal_df.copy().rename(columns={orders_col: "n_orders", late_col: "n_late"})
    b_df = bad_df.copy().rename(columns={orders_col: "b_orders", late_col: "b_late"})
    n_df["n_rate"] = n_df["n_late"] / n_df["n_orders"]
    b_df["b_rate"] = b_df["b_late"] / b_df["b_orders"]

    merged = n_df[[group_col, "n_orders", "n_rate"]].merge(
        b_df[[group_col, "b_orders", "b_rate"]], on=group_col, how="outer"
    ).fillna(0)

    n_total = merged["n_orders"].sum()
    b_total = merged["b_orders"].sum()

    baseline_rate = (n_df["n_late"].sum() / n_df["n_orders"].sum()) if n_df["n_orders"].sum() > 0 else 0
    bad_rate = (b_df["b_late"].sum() / b_df["b_orders"].sum()) if b_df["b_orders"].sum() > 0 else 0

    # expected bad rate at baseline rates, but with bad mix
    merged["share_bad"] = merged["b_orders"] / b_total if b_total > 0 else 0
    merged["rate_effect"] = merged["share_bad"] * (merged["b_rate"] - merged["n_rate"])
    merged["mix_effect"] = (merged["share_bad"] - merged["n_orders"] / n_total if n_total > 0 else 0) * merged["n_rate"]

    return {
        "baseline_rate": baseline_rate,
        "bad_rate": bad_rate,
        "change": bad_rate - baseline_rate,
        "mix_effect": float(merged["mix_effect"].sum()),
        "rate_effect": float(merged["rate_effect"].sum()),
        "breakdown": merged,
    }
