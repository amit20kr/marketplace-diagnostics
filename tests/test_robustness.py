"""tests/test_robustness.py – checks for robustness analysis outputs (WP1).

Verifies that:
  1. All 5 robustness CSVs and robustness_summary.json exist in outputs/.
  2. Baseline rows in all 5 robustness tables match the pipeline's saved outputs.
  3. robustness_summary.json contains conclusion_changes and justifications for all 5 checks.
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest


@pytest.mark.real
def test_robustness_files_exist(out_dir: Path):
    expected_files = [
        "robustness_bad_month.csv",
        "robustness_lateness_def.csv",
        "robustness_or_strata.csv",
        "robustness_simulator.csv",
        "robustness_first_sale.csv",
        "robustness_summary.json",
    ]
    for fn in expected_files:
        p = out_dir / fn
        assert p.exists(), f"Missing expected robustness file: {p}"


@pytest.mark.real
def test_robustness_bad_month_baseline(out_dir: Path, real_summary: dict):
    df = pd.read_csv(out_dir / "robustness_bad_month.csv")
    assert len(df) == 3
    assert set(df["threshold"]) == {"8%", "10%", "12%"}

    base = df[df["is_baseline"] == 1].iloc[0]
    deliv = real_summary["delivery"]
    assert base["baseline_late_rate"] == deliv["baseline_late_rate"]
    assert base["bad_months_late_rate"] == deliv["bad_months_late_rate"]
    assert base["change_pp"] == round(deliv["shift_share_change"] * 100, 2)
    assert base["mix_effect_pp"] == round(deliv["shift_share_mix_effect"] * 100, 2)
    assert base["rate_effect_pp"] == round(deliv["shift_share_rate_effect"] * 100, 2)


@pytest.mark.real
def test_robustness_lateness_def_baseline(out_dir: Path, real_summary: dict):
    df = pd.read_csv(out_dir / "robustness_lateness_def.csv")
    assert len(df) == 2
    assert "date_level (baseline)" in df["definition"].values
    assert "timestamp_level" in df["definition"].values

    base = df[df["is_baseline"] == 1].iloc[0]
    kpi = real_summary["kpi"]
    rev = real_summary["reviews"]
    deliv = real_summary["delivery"]

    assert base["late_orders"] == kpi["late_orders"]
    assert base["late_rate"] == kpi["late_rate"]
    assert base["one_star_late"] == rev["one_star_late"]
    assert base["one_star_ontime"] == rev["one_star_ontime"]
    assert base["post_delivery_gap_pp"] == round(rev["post_delivery_gap"] * 100, 2)
    assert base["dispatch_missed_risk_ratio"] == round(deliv["dispatch_missed_risk_ratio"], 2)


@pytest.mark.real
def test_robustness_or_strata_baseline(out_dir: Path, real_summary: dict):
    df = pd.read_csv(out_dir / "robustness_or_strata.csv")
    assert len(df) == 3
    assert set(df["strata_set"]) == {"review_timing_only", "customer_state_only", "timing_x_state"}

    base = df[df["is_baseline"] == 1].iloc[0]
    rev = real_summary["reviews"]
    assert base["mh_or"] == rev["mh_or"]
    assert base["ci_lo"] == rev["mh_or_ci"][0]
    assert base["ci_hi"] == rev["mh_or_ci"][1]
    assert base["n_strata_valid"] == rev["strata_used"]


@pytest.mark.real
def test_robustness_simulator_baseline(out_dir: Path):
    df = pd.read_csv(out_dir / "robustness_simulator.csv")
    assert set(df["min_orders"]) == {20, 30, 50}

    stat_sim = pd.read_csv(out_dir / "stat_simulator.csv")
    base = df[df["is_baseline"] == 1].reset_index(drop=True)

    for col in ["pct_worst", "n_eligible_sellers", "n_fixed_sellers", "median_dispatch",
                "late_orders_avoided", "share_of_all_late", "est_1star_low", "est_1star_high"]:
        assert np.allclose(base[col].values, stat_sim[col].values)


@pytest.mark.real
def test_robustness_first_sale_baseline(out_dir: Path, real_summary: dict):
    df = pd.read_csv(out_dir / "robustness_first_sale.csv")
    assert len(df) == 2

    base = df[df["is_baseline"] == 1].iloc[0]
    fn = real_summary["funnel"]
    po = fn["paid_vs_organic"]
    chi = fn["chi2_downstream"]

    assert base["first_sale_deals"] == 288
    assert base["chi2_stat"] == round(chi["chi2"], 4)
    assert base["chi2_p_value"] == round(chi["p_value"], 4)
    assert base["cramers_v"] == round(chi["cramers_v"], 4)
    assert base["paid_rate"] == po["paid_rate"]
    assert base["organic_rate"] == po["organic_rate"]
    assert base["paid_vs_organic_diff_pp"] == po["diff_pp"]
    assert base["diff_ci_lo_pp"] == po["diff_ci_lo_pp"]
    assert base["diff_ci_hi_pp"] == po["diff_ci_hi_pp"]


@pytest.mark.real
def test_robustness_summary_json(out_dir: Path):
    summary_path = out_dir / "robustness_summary.json"
    with open(summary_path, "r", encoding="utf-8") as f:
        summary_data = json.load(f)

    expected_sections = [
        "bad_month_threshold",
        "lateness_definition",
        "or_strata_sets",
        "simulator_min_orders",
        "first_sale_date_level",
    ]

    for sec in expected_sections:
        assert sec in summary_data, f"Missing section {sec} in robustness_summary.json"
        assert summary_data[sec]["conclusion_changes"] in {"yes", "no"}
        assert len(summary_data[sec]["justification"]) > 10
