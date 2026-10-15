"""app/data.py – cached data loaders for the Streamlit app.

Reads ONLY from outputs/. Never reads data/raw/ or the SQLite database.
Every loader uses st.cache_data so reload is instant.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st

# Make src/ importable for stats.py and simulator.py
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

OUT = ROOT / "outputs"


# ─── Core loaders ─────────────────────────────────────────────────────────────

@st.cache_data
def load_summary() -> dict:
    return json.loads((OUT / "analysis_summary.json").read_text(encoding="utf-8"))


@st.cache_data
def load_orders() -> pd.DataFrame:
    """app_orders.csv.gz – order-grain fact table (in-window, delivered-valid)."""
    df = pd.read_csv(OUT / "app_orders.csv.gz")
    df["purchase_month"] = df["purchase_month"].astype(str)
    return df


@st.cache_data
def load_funnel() -> pd.DataFrame:
    """app_funnel.csv – one row per lead (includes deal columns for deals)."""
    return pd.read_csv(OUT / "app_funnel.csv")


# ─── KPI tables ───────────────────────────────────────────────────────────────

@st.cache_data
def load_kpi_monthly() -> pd.DataFrame:
    return pd.read_csv(OUT / "out_kpi_monthly.csv")


@st.cache_data
def load_kpi_overall() -> pd.DataFrame:
    return pd.read_csv(OUT / "out_kpi_overall.csv")


# ─── Funnel stat tables ───────────────────────────────────────────────────────

@st.cache_data
def load_funnel_waterfall() -> pd.DataFrame:
    return pd.read_csv(OUT / "out_funnel_waterfall.csv")


@st.cache_data
def load_funnel_origin_stat() -> pd.DataFrame:
    return pd.read_csv(OUT / "stat_funnel_origin.csv")


@st.cache_data
def load_funnel_landing_stat() -> pd.DataFrame:
    return pd.read_csv(OUT / "stat_funnel_landing.csv")


@st.cache_data
def load_days_to_close() -> pd.DataFrame:
    return pd.read_csv(OUT / "stat_days_to_close.csv")


@st.cache_data
def load_sdr() -> pd.DataFrame:
    return pd.read_csv(OUT / "stat_sdr.csv")


@st.cache_data
def load_downstream_origin() -> pd.DataFrame:
    return pd.read_csv(OUT / "stat_downstream_origin.csv")


# ─── Cohort tables ────────────────────────────────────────────────────────────

@st.cache_data
def load_cohort_retention() -> pd.DataFrame:
    return pd.read_csv(OUT / "out_cohort_retention.csv")


@st.cache_data
def load_cohort_compare() -> pd.DataFrame:
    return pd.read_csv(OUT / "stat_cohort_compare.csv")


# ─── Delivery stat tables ─────────────────────────────────────────────────────

@st.cache_data
def load_late_state() -> pd.DataFrame:
    return pd.read_csv(OUT / "stat_late_state.csv")


@st.cache_data
def load_late_lane() -> pd.DataFrame:
    return pd.read_csv(OUT / "stat_late_lane.csv")


@st.cache_data
def load_seller_pareto() -> pd.DataFrame:
    return pd.read_csv(OUT / "stat_seller_pareto.csv")


@st.cache_data
def load_stage_bad_vs_normal() -> pd.DataFrame:
    return pd.read_csv(OUT / "stat_stage_bad_vs_normal.csv")


@st.cache_data
def load_shift_share_state() -> pd.DataFrame:
    return pd.read_csv(OUT / "stat_shift_share_state.csv")


@st.cache_data
def load_late_category() -> pd.DataFrame:
    return pd.read_csv(OUT / "out_late_category.csv")


# ─── Review tables ────────────────────────────────────────────────────────────

@st.cache_data
def load_review_band() -> pd.DataFrame:
    return pd.read_csv(OUT / "stat_review_band.csv")


@st.cache_data
def load_review_timing() -> pd.DataFrame:
    return pd.read_csv(OUT / "out_review_timing.csv")


# ─── Seller tables ────────────────────────────────────────────────────────────

@st.cache_data
def load_seller_compare_2018() -> pd.DataFrame:
    return pd.read_csv(OUT / "stat_seller_compare_2018.csv")


# ─── Robustness tables (WP1) ──────────────────────────────────────────────────

@st.cache_data
def load_robust_lateness() -> pd.DataFrame:
    return pd.read_csv(OUT / "robustness_lateness_def.csv")


@st.cache_data
def load_robust_first_sale() -> pd.DataFrame:
    return pd.read_csv(OUT / "robustness_first_sale.csv")


# ─── Filter helpers ───────────────────────────────────────────────────────────

def apply_order_filters(
    df: pd.DataFrame,
    months: list[str] | None = None,
    states: list[str] | None = None,
    categories: list[str] | None = None,
) -> pd.DataFrame:
    """Apply global sidebar filters to order-grain data."""
    if months:
        df = df[df["purchase_month"].isin(months)]
    if states:
        df = df[df["customer_state"].isin(states)]
    if categories:
        df = df[df["category"].isin(categories)]
    return df


def get_filter_options(orders: pd.DataFrame) -> tuple[list, list, list]:
    months = sorted(orders["purchase_month"].dropna().unique().tolist())
    states = sorted(orders["customer_state"].dropna().unique().tolist())
    categories = sorted(orders["category"].dropna().unique().tolist())
    return months, states, categories
