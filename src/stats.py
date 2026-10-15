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


# ─── Proportion Difference CI ────────────────────────────────────────────────

def proportion_diff_ci(p1: float, n1: int, p2: float, n2: int, z: float = 1.96) -> tuple[float, float, float]:
    """Wald 95% CI for difference in independent proportions p1 - p2.
    
    Returns (diff, lo, hi).
    """
    diff = p1 - p2
    if n1 <= 0 or n2 <= 0:
        return (diff, float("nan"), float("nan"))
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    return (diff, diff - z * se, diff + z * se)


# ─── Mann-Whitney ─────────────────────────────────────────────────────────────

def mann_whitney(a: np.ndarray, b: np.ndarray) -> dict:
    """Mann-Whitney U test plus rank-biserial correlation (effect size).

    r = 2U/(n_a * n_b) - 1 (D-027). Range [-1, 1]; <0 means group a tends to rank lower than group b.
    """
    if len(a) == 0 or len(b) == 0:
        return {"u_stat": float("nan"), "p_value": float("nan"), "p_display": "nan",
                "r_biserial": float("nan"), "n_a": len(a), "n_b": len(b)}
    u, p = sps.mannwhitneyu(a, b, alternative="two-sided")
    r = 2 * u / (len(a) * len(b)) - 1
    p_display = "<1e-300" if (p < 1e-300 or p == 0.0) else (f"{p:.4e}" if p < 0.0001 else f"{p:.4f}")
    return {"u_stat": float(u), "p_value": float(p), "p_display": p_display,
            "r_biserial": float(r), "n_a": int(len(a)), "n_b": int(len(b))}


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
    """Mantel-Haenszel adjusted odds ratio.

    Each stratum is (a, b, c, d) in a 2x2:
    Specifically: a=late&1star, b=late&not1star, c=ontime&1star, d=ontime&not1star.
    Returns {"mh_or": float, "n_strata": int}.
    """
    num, denom = 0.0, 0.0
    valid = 0
    for a, b, c, d in strata:
        n = a + b + c + d
        if n == 0 or (a + b == 0) or (c + d == 0):
            continue
        num += a * d / n
        denom += b * c / n
        valid += 1
    mh_or = num / denom if denom != 0 else float("nan")
    return {"mh_or": float(mh_or), "n_strata": valid}


def bootstrap_mh_or_ci(
    df: pd.DataFrame,
    strata_cols: list[str],
    exposure_col: str,
    outcome_col: str,
    n_boot: int = 1000,
    ci: float = 0.95,
    rng: int = 42,
) -> tuple[float, float, float, int]:
    """Mantel-Haenszel OR and non-parametric bootstrap CI via vectorised multinomial counts (D-023).

    Returns (mh_or, lo, hi, n_strata_valid).
    """
    sub = df.dropna(subset=strata_cols + [exposure_col, outcome_col]).copy()
    strata_keys = sub[strata_cols].drop_duplicates().reset_index(drop=True)
    strata_keys["stratum_id"] = strata_keys.index
    merged = sub.merge(strata_keys, on=strata_cols)

    # cell_id: stratum_id * 4 + exposure * 2 + outcome
    merged["cell_id"] = (
        merged["stratum_id"] * 4
        + merged[exposure_col].astype(int) * 2
        + merged[outcome_col].astype(int)
    )
    n_cells = len(strata_keys) * 4
    counts = np.bincount(merged["cell_id"], minlength=n_cells)

    # Point estimate
    reshaped_pt = counts.reshape((-1, 4))
    d_pt = reshaped_pt[:, 0]  # exp=0, out=0 (ontime, not 1-star)
    c_pt = reshaped_pt[:, 1]  # exp=0, out=1 (ontime, 1-star)
    b_pt = reshaped_pt[:, 2]  # exp=1, out=0 (late, not 1-star)
    a_pt = reshaped_pt[:, 3]  # exp=1, out=1 (late, 1-star)
    n_pt = a_pt + b_pt + c_pt + d_pt
    valid_mask = (n_pt > 0) & ((a_pt + b_pt) > 0) & ((c_pt + d_pt) > 0)

    num_pt = np.where(valid_mask, (a_pt * d_pt) / np.maximum(n_pt, 1), 0.0).sum()
    denom_pt = np.where(valid_mask, (b_pt * c_pt) / np.maximum(n_pt, 1), 0.0).sum()
    pt_mh = float(num_pt / denom_pt) if denom_pt > 0 else float("nan")
    valid_strata = int(valid_mask.sum())

    # Bootstrap resample via multinomial
    rng_obj = np.random.default_rng(rng)
    total_n = len(merged)
    p_vals = counts / total_n
    boot_counts = rng_obj.multinomial(total_n, p_vals, size=n_boot)
    reshaped_b = boot_counts.reshape((n_boot, -1, 4))
    d_b = reshaped_b[:, :, 0]
    c_b = reshaped_b[:, :, 1]
    b_b = reshaped_b[:, :, 2]
    a_b = reshaped_b[:, :, 3]
    n_b = a_b + b_b + c_b + d_b
    valid_b = (n_b > 0) & ((a_b + b_b) > 0) & ((c_b + d_b) > 0)
    num_b = np.where(valid_b, (a_b * d_b) / np.maximum(n_b, 1), 0.0).sum(axis=1)
    denom_b = np.where(valid_b, (b_b * c_b) / np.maximum(n_b, 1), 0.0).sum(axis=1)
    boot_ors = np.where(denom_b > 0, num_b / denom_b, np.nan)

    alpha = 1 - ci
    lo = float(np.nanpercentile(boot_ors, 100 * (alpha / 2)))
    hi = float(np.nanpercentile(boot_ors, 100 * (1 - alpha / 2)))
    return (pt_mh, lo, hi, valid_strata)


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
