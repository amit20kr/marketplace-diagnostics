"""tests/test_pipeline.py – checks for the Olist pipeline (D-029, revised by D-030).

Layers
  A. Known-answer tests of the SQL on a hand-built mini dataset (tests/synth_db.py). Run on every machine.
  B. Structural invariants. Run on the synthetic DB always, and on the real DB too when it exists
     (the `env` fixture is parametrised: [synthetic] and [real]).
  C. Independent audit: the funnel is recomputed in pandas from the raw tables and compared with SQL.
  D. Pure-Python checks of src/stats.py and src/simulator.py.
  E. Real-data-only checks (marked `real`): row counts, simulator on real orders, saved outputs.

Run `pytest` from anywhere inside the project. The header says whether real data was found;
`-ra` lists every skip with its reason; the footer says how many tests ran on real data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from simulator import run_scenarios
from stats import (bootstrap_mh_or_ci, chi_square_table, mann_whitney, mantel_haenszel_or,
                   shift_share, wilson_ci)


def q(env, sql: str) -> pd.DataFrame:
    return pd.read_sql_query(sql, env.conn)


def wf(env) -> dict:
    t = q(env, "SELECT stage, value FROM out_funnel_waterfall")
    return dict(zip(t["stage"], t["value"]))


# ═════════════════════════════════════════════════════════════════════════════
# A. Known answers on the mini dataset (synthetic only)
# ═════════════════════════════════════════════════════════════════════════════

# order: (in_window, delivered_valid, is_late, late_ts, stage_valid)
EXPECTED_FLAGS = {
    "O1": (1, 1, 0, 0, 1), "O2": (1, 1, 1, 1, 1), "O3": (1, 1, 0, 0, 1),
    "O4": (1, 0, None, None, 0),            # shipped: not delivered
    "O5": (1, 0, None, None, 0),            # 'delivered' without a delivery date (D-002)
    "O6": (0, 1, 0, 0, 1),                  # purchased 2016-12: before the window
    "O7": (0, 1, 0, 0, 1),                  # purchased 2018-09: after the window
    "O8": (1, 1, 0, 0, 1), "O9": (1, 1, 0, 0, 0),   # O9: carrier hand-off after delivery (D-004)
    "O10": (1, 1, 0, 1, 1),                 # D-012: on time by DATE, late by TIMESTAMP
    "O11": (1, 1, 0, 0, 1), "O12": (1, 1, 0, 0, 1), "O13": (1, 1, 0, 0, 1),
}


def test_a1_order_flags_known_answers(synth_env):
    fo = q(synth_env, "SELECT order_id, in_window, delivered_valid, is_late, late_ts, stage_valid FROM fact_orders")
    got = {r.order_id: tuple(None if pd.isna(v) else int(v) for v in r[1:]) for r in fo.itertuples(index=False)}
    assert got == EXPECTED_FLAGS


def test_a2_lateness_values_and_stage_times(synth_env):
    fo = q(synth_env, "SELECT * FROM fact_orders").set_index("order_id")
    assert fo.loc["O2", "delay_days"] == 5 and fo.loc["O2", "delay_band"] == "4-7"
    assert fo.loc["O1", "delay_days"] == -2 and fo.loc["O1", "delay_band"] == "on_time"
    assert fo.loc["O10", "delay_days"] == 0 and fo.loc["O10", "delay_band"] == "on_time"
    # O1: purchase 03-01 10:00 -> carrier 03-03 08:00 (1d 22h) -> delivered 03-08 14:00 (5d 6h)
    assert fo.loc["O1", "dispatch_days"] == pytest.approx(1 + 22 / 24, abs=1e-6)
    assert fo.loc["O1", "transit_days"] == pytest.approx(5.25, abs=1e-6)
    assert pd.isna(fo.loc["O9", "dispatch_days"]) and pd.isna(fo.loc["O4", "dispatch_days"])


def test_a3_seller_attribution_and_gmv(synth_env):
    fo = q(synth_env, "SELECT * FROM fact_orders").set_index("order_id")
    assert pd.isna(fo.loc["O8", "seller_id"]) and fo.loc["O8", "n_sellers"] == 2     # D-018
    assert fo.loc["O3", "seller_id"] == "S3" and fo.loc["O3", "n_items"] == 2
    assert fo.loc["O3", "item_value"] == pytest.approx(80.0)                          # 50 + 30, not doubled
    assert pd.isna(fo.loc["O11", "item_value"]) and pd.isna(fo.loc["O11", "seller_id"])  # order without items
    assert fo.loc["O1", "category"] == "electronics" and fo.loc["O3", "category"] == "toys"


def test_a4_review_dedup_and_timing(synth_env):
    fo = q(synth_env, "SELECT * FROM fact_orders").set_index("order_id")
    assert fo.loc["O3", "review_score"] == 2                      # R3b (answered later) beats R3 (D-003)
    assert fo.loc["O2", "review_score"] == 1 and fo.loc["O2", "review_pre_delivery"] == 1   # written 04-12, delivered 04-15
    assert fo.loc["O1", "review_pre_delivery"] == 0 and fo.loc["O3", "review_pre_delivery"] == 0
    assert fo.loc["O12", "review_pre_delivery"] == 1
    assert pd.isna(fo.loc["O4", "review_score"])
    log = dict(q(synth_env, "SELECT item, value FROM out_clean_log").values)
    assert (log["reviews_raw_rows"], log["reviews_clean_rows"], log["reviews_dropped_by_dedup"]) == (7, 6, 1)
    assert log["delivered_without_delivery_date"] == 1 and log["orders_without_items"] == 1


def test_a5_headline_kpis(synth_env):
    k = q(synth_env, "SELECT * FROM out_kpi_overall").iloc[0]
    assert (k["orders_in_window"], k["delivered_valid_orders"], k["late_orders"]) == (11, 9, 1)
    assert k["late_rate"] == pytest.approx(1 / 9, abs=1e-6)
    assert k["late_rate_timestamp_level"] == pytest.approx(2 / 9, abs=1e-6)       # D-012 sensitivity
    assert (k["orders_reviewed"], k["single_seller_orders"], k["multi_seller_orders"]) == (6, 7, 1)
    assert k["one_star_share"] == pytest.approx(1 / 6, abs=1e-6)
    assert k["gmv_items"] == pytest.approx(895.0)
    sens = q(synth_env, "SELECT definition, late_orders FROM out_late_sensitivity").set_index("definition")["late_orders"]
    assert (sens["date_level"], sens["timestamp_level"]) == (1, 2)


def test_a6_funnel_known_answers(synth_env):
    w = wf(synth_env)
    expected = {
        "all_leads": 4, "closed_deals": 3, "deal_sellers_in_sellers_table": 2, "deal_sellers_in_order_items": 2,
        "deal_sellers_with_delivered_order": 2, "deals_matured_90d": 3, "matured_deals_first_sale_within_90d": 1,
        "delivered_orders_from_deal_sellers": 4, "item_gmv_deal_sellers": 440.0, "delivered_orders_all": 11,
        "NAIVE_join_rows_leads_x_deals_x_items": 7,       # fan-out trap: 4 leads become 7 rows
    }
    assert {k: w[k] for k in expected} == pytest.approx(expected)


# ═════════════════════════════════════════════════════════════════════════════
# B. Structural invariants (synthetic always; real too when available)
# ═════════════════════════════════════════════════════════════════════════════

def test_b1_unique_grain(env):
    assert q(env, "SELECT COUNT(*) - COUNT(DISTINCT order_id) AS d FROM fact_orders").d[0] == 0
    assert q(env, "SELECT COUNT(*) - COUNT(DISTINCT order_id) AS d FROM fact_reviews").d[0] == 0
    assert q(env, "SELECT COUNT(*) - COUNT(DISTINCT mql_id) AS d FROM fact_seller_funnel").d[0] == 0
    assert q(env, "SELECT COUNT(*) - COUNT(DISTINCT order_id || '-' || order_item_id) AS d FROM fact_order_items").d[0] == 0


def test_b2_no_gmv_double_counting(env):
    total_orders = q(env, "SELECT SUM(item_value) AS v FROM fact_orders").v[0]
    total_items = q(env, "SELECT SUM(price) AS v FROM fact_order_items").v[0]
    assert total_orders == pytest.approx(total_items, abs=0.01)
    per_order = q(env, """SELECT o.order_id, o.item_value, i.s FROM fact_orders o
                          JOIN (SELECT order_id, SUM(price) AS s FROM fact_order_items GROUP BY order_id) i
                            ON i.order_id = o.order_id""")
    assert ((per_order["item_value"] - per_order["s"]).abs() < 0.01).all()


def test_b3_late_flag_consistency(env):
    d = q(env, "SELECT is_late, late_ts, delay_days, delivered_valid FROM fact_orders WHERE delivered_valid = 1")
    assert (d["is_late"] == (d["delay_days"] > 0).astype(int)).all()
    assert (d["late_ts"] >= d["is_late"]).all()        # timestamp-level lateness is never milder than date-level
    assert q(env, "SELECT COUNT(*) AS c FROM fact_orders WHERE delivered_valid = 0 AND is_late IS NOT NULL").c[0] == 0


def test_b4_stage_times_add_up(env):
    d = q(env, "SELECT purchase_ts, delivered_ts, dispatch_days, transit_days FROM fact_orders WHERE stage_valid = 1")
    elapsed = (pd.to_datetime(d["delivered_ts"], format="ISO8601")
               - pd.to_datetime(d["purchase_ts"], format="ISO8601")).dt.total_seconds() / 86400
    assert (elapsed - (d["dispatch_days"] + d["transit_days"])).abs().max() < 1e-3
    assert (d["dispatch_days"] >= 0).all() and (d["transit_days"] >= 0).all()


def test_b5_window_rules(env):
    fo = q(env, "SELECT purchase_ts, in_window FROM fact_orders")
    inside = fo["purchase_ts"].between("2017-01-01", "2018-08-31 23:59:59")
    assert (fo["in_window"] == inside.astype(int)).all()      # flag agrees with the dates, both directions


def test_b6_funnel_waterfall_is_a_funnel(env):
    w = wf(env)
    assert w["all_leads"] >= w["closed_deals"] >= w["deal_sellers_in_sellers_table"] \
        >= w["deal_sellers_in_order_items"] >= w["deal_sellers_with_delivered_order"]
    assert w["deals_matured_90d"] <= w["closed_deals"]
    assert w["matured_deals_first_sale_within_90d"] <= w["deals_matured_90d"]
    assert w["delivered_orders_from_deal_sellers"] <= w["delivered_orders_all"]
    assert w["NAIVE_join_rows_leads_x_deals_x_items"] >= w["all_leads"]       # the fan-out trap exists


def test_b7_cohort_table_is_coherent(env):
    c = q(env, "SELECT cohort_month, grp, k, cohort_size, active_n, observable FROM out_cohort_retention")
    assert (c["active_n"] <= c["cohort_size"]).all()
    k0 = c[(c["k"] == 0) & (c["observable"] == 1)]
    assert (k0["active_n"] == k0["cohort_size"]).all()        # everyone is active in their own first month


# ═════════════════════════════════════════════════════════════════════════════
# C. Independent audit: SQL funnel == pandas recomputation from the raw tables
# ═════════════════════════════════════════════════════════════════════════════

def test_c1_funnel_equals_independent_pandas(env):
    if not env.frames:
        pytest.skip("raw CSVs not found (set OLIST_RAW or put them in data/raw)")
    o, it, sl, ld, cd = (env.frames[k] for k in ("orders", "order_items", "sellers", "leads", "closed_deals"))
    delivered = o[(o["order_status"] == "delivered") & o["order_delivered_customer_date"].notna()]
    deal_sellers = set(cd["seller_id"].dropna())
    items = it[it["order_id"].isin(set(delivered["order_id"])) & it["seller_id"].isin(deal_sellers)]
    naive = ld.merge(cd[["mql_id", "seller_id"]], on="mql_id", how="left").merge(
        it[["seller_id"]], on="seller_id", how="left")
    expected = {
        "all_leads": ld["mql_id"].nunique(),
        "closed_deals": cd["mql_id"].nunique(),
        "deal_sellers_in_sellers_table": len(deal_sellers & set(sl["seller_id"])),
        "deal_sellers_in_order_items": len(deal_sellers & set(it["seller_id"])),
        "deal_sellers_with_delivered_order": items["seller_id"].nunique(),
        "delivered_orders_from_deal_sellers": items["order_id"].nunique(),
        "item_gmv_deal_sellers": round(pd.to_numeric(items["price"]).sum(), 2),
        "delivered_orders_all": len(delivered),
        "NAIVE_join_rows_leads_x_deals_x_items": len(naive),
    }
    w = wf(env)
    assert {k: w[k] for k in expected} == pytest.approx(expected, abs=0.01)


# ═════════════════════════════════════════════════════════════════════════════
# D. Pure-Python checks (no database)
# ═════════════════════════════════════════════════════════════════════════════

def _random_orders(seed=0, n=500, n_sellers=50):
    rng = np.random.default_rng(seed)
    dispatch = rng.uniform(1, 10, size=n)
    delay = dispatch - np.median(dispatch) + rng.uniform(-2, 2, size=n)
    return pd.DataFrame({
        "order_id": range(n), "in_window": 1, "delivered_valid": 1, "stage_valid": 1,
        "seller_id": rng.choice([f"S{i:03d}" for i in range(n_sellers)], size=n),
        "dispatch_days": dispatch, "delay_days": delay, "is_late": (delay > 0).astype(int),
        "review_score": rng.choice([1, 2, 3, 4, 5], size=n),
        "review_pre_delivery": rng.choice([0, 1], size=n),
    })


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_d1_simulator_invariants(seed):
    """Fixing more sellers never avoids fewer late orders; the 1-star range is ordered; 0% fixes nothing."""
    res = run_scenarios(_random_orders(seed), pcts=(0.0, 0.05, 0.10, 0.20, 0.50), min_orders=5)
    for col in ("n_fixed_sellers", "late_orders_avoided", "est_1star_low", "est_1star_high"):
        assert res[col].is_monotonic_increasing, f"{col} not monotone: {res[col].tolist()}"
    assert (res["est_1star_low"] <= res["est_1star_high"]).all()
    zero = res[res["pct_worst"] == 0.0].iloc[0]
    assert zero["n_fixed_sellers"] == 0 and zero["late_orders_avoided"] == 0


def test_d2_simulator_range_is_ordered_even_when_post_gap_exceeds_crude_gap():
    """Regression: the low/high ordering must come from the code, not from lucky data (D-024)."""
    df = _random_orders(seed=0)
    # post-delivery reviews (pre_delivery == 0) are brutal for late orders, pre-delivery ones are neutral
    late = df["is_late"] == 1
    df["review_pre_delivery"] = np.where(late, np.arange(len(df)) % 2, 1)
    df["review_score"] = np.where(late & (df["review_pre_delivery"] == 0), 1, 5)
    res = run_scenarios(df, pcts=(0.10, 0.50), min_orders=5)
    assert res["late_orders_avoided"].max() > 0
    assert (res["est_1star_low"] <= res["est_1star_high"]).all()


def test_d3_wilson_ci_known_value():
    lo, hi = wilson_ci(842, 8000)                  # 842 deals out of 8000 leads
    assert lo == pytest.approx(0.0987, abs=0.0005) and hi == pytest.approx(0.1122, abs=0.0005)
    lo, hi = wilson_ci(50, 100)
    assert lo == pytest.approx(0.4038, abs=0.001) and hi == pytest.approx(0.5962, abs=0.001)
    assert all(np.isnan(wilson_ci(0, 0)))


def test_d4_shift_share_is_exact():
    normal = pd.DataFrame({"state": ["A", "B"], "orders": [1000, 500], "late": [40, 30]})
    bad = pd.DataFrame({"state": ["A", "B"], "orders": [800, 600], "late": [80, 90]})
    res = shift_share(normal, bad, "state", "orders", "late")
    assert res["mix_effect"] + res["rate_effect"] == pytest.approx(res["change"], abs=1e-12)
    # a group that only exists in the bad period must not break the identity
    bad2 = pd.concat([bad, pd.DataFrame({"state": ["C"], "orders": [100], "late": [20]})], ignore_index=True)
    res2 = shift_share(normal, bad2, "state", "orders", "late")
    assert res2["mix_effect"] + res2["rate_effect"] == pytest.approx(res2["change"], abs=1e-12)


def test_d5_mantel_haenszel_recovers_a_common_odds_ratio():
    # two strata that both have odds ratio exactly 2: (a*d)/(b*c) = (20*10)/(10*10) = (40*20)/(20*20)
    out = mantel_haenszel_or([(20, 10, 10, 10), (40, 20, 20, 20)])
    assert out["mh_or"] == pytest.approx(2.0) and out["n_strata"] == 2
    # a stratum with no late (or no on-time) orders carries no information and is skipped
    out = mantel_haenszel_or([(20, 10, 10, 10), (0, 0, 5, 5), (3, 3, 0, 0)])
    assert out["mh_or"] == pytest.approx(2.0) and out["n_strata"] == 1


def test_d6_bootstrap_mh_ci_brackets_the_estimate():
    rng = np.random.default_rng(3)
    n = 6000
    df = pd.DataFrame({"state": rng.choice(list("ABCD"), n), "late": rng.integers(0, 2, n)})
    p = np.where(df["late"] == 1, 0.35, 0.12)          # true OR ~ 3.9 in every state
    df["one_star"] = (rng.random(n) < p).astype(int)
    pt, lo, hi, k = bootstrap_mh_or_ci(df, ["state"], "late", "one_star", n_boot=300)
    assert k == 4 and lo < pt < hi and 2.5 < pt < 5.5


def test_d7_mann_whitney_sign_convention():
    """D-027: r = 2U/(n1*n2) - 1 is negative when group a scores lower than group b."""
    low = np.array([1, 1, 2, 2, 3, 1, 2])
    high = np.array([4, 5, 5, 4, 5, 3, 5])
    assert mann_whitney(low, high)["r_biserial"] < -0.8
    assert mann_whitney(high, low)["r_biserial"] > 0.8
    assert mann_whitney(low, low)["r_biserial"] == pytest.approx(0.0, abs=1e-9)
    assert np.isnan(mann_whitney(np.array([]), high)["r_biserial"])


def test_d8_chi_square_table():
    out = chi_square_table(pd.DataFrame([[50, 50], [50, 50]]))
    assert out["chi2"] == pytest.approx(0.0, abs=1e-9) and out["cramers_v"] == pytest.approx(0.0, abs=1e-9)
    out = chi_square_table(pd.DataFrame([[90, 10], [10, 90]]))
    # uncorrected V would be exactly 0.80; scipy applies Yates' correction to 2x2 tables, so slightly below
    assert out["p_value"] < 1e-10 and 0.78 < out["cramers_v"] < 0.80 and out["dof"] == 1


# ═════════════════════════════════════════════════════════════════════════════
# E. Real-data-only checks (skipped, with a stated reason, when the real data are absent)
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.real
def test_e1_real_row_counts(real_env):
    expected = {"raw_orders": 99441, "raw_order_items": 112650, "raw_reviews": 99224, "raw_customers": 99441,
                "raw_sellers": 3095, "raw_leads": 8000, "raw_closed_deals": 842, "clean_reviews": 98673}
    got = {t: int(q(real_env, f"SELECT COUNT(*) AS n FROM {t}").n[0]) for t in expected}
    assert got == expected


@pytest.mark.real
def test_e2_simulator_on_real_orders(real_env):
    orders = q(real_env, """SELECT order_id, seller_id, in_window, delivered_valid, stage_valid, is_late, delay_days,
                                   dispatch_days, review_score, review_pre_delivery
                            FROM fact_orders WHERE in_window = 1 AND delivered_valid = 1""")
    res = run_scenarios(orders, pcts=(0.0, 0.05, 0.10, 0.20), min_orders=30)
    for col in ("n_fixed_sellers", "late_orders_avoided", "est_1star_low", "est_1star_high"):
        assert res[col].is_monotonic_increasing, f"{col}: {res[col].tolist()}"
    assert (res["est_1star_low"] <= res["est_1star_high"]).all()
    zero = res[res["pct_worst"] == 0.0].iloc[0]
    assert zero["n_fixed_sellers"] == 0 and zero["late_orders_avoided"] == 0


@pytest.mark.real
def test_e3_adjusted_odds_ratio_is_saved_and_sane(real_summary):
    rv = real_summary["reviews"]                      # D-023: Mantel-Haenszel over review timing x customer state
    lo, hi = rv["mh_or_ci"]
    assert rv["strata_used"] > 3 and rv["strata_used"] <= rv["strata_total"]
    assert lo <= rv["mh_or"] <= hi and rv["mh_or"] > 1.0
    assert rv["mh_or"] < rv["crude_or"]               # adjusting for survey timing must shrink the crude OR (L-009)
    assert rv["mann_whitney"]["r_biserial"] < 0       # D-027: late orders score lower


@pytest.mark.real
def test_e4_saved_outputs_match_the_database(real_env, real_summary, out_dir):
    """Guards against stale outputs/: JSON and CSV must describe the same run as the database."""
    db_kpi = q(real_env, "SELECT delivered_valid_orders, late_orders FROM out_kpi_overall").iloc[0]
    csv_kpi = pd.read_csv(out_dir / "out_kpi_overall.csv").iloc[0]
    js = real_summary["kpi"]
    assert (int(db_kpi.delivered_valid_orders), int(db_kpi.late_orders)) == \
           (int(csv_kpi.delivered_valid_orders), int(csv_kpi.late_orders)) == \
           (js["delivered_valid_orders"], js["late_orders"])
    assert all(r["est_1star_low"] <= r["est_1star_high"] for r in real_summary["simulator"])
