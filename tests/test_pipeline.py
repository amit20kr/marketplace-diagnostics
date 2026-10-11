"""tests/test_pipeline.py – 11 checks for the Olist pipeline.

Tests T01 and T07 are real-data-only (skipif REAL_DATA is False).
Tests T02-T08 use an in-memory synthetic SQLite DB built by the synth_conn fixture.
Tests T09-T11 are pure-Python (no DB needed).

Environment variables:
  OLIST_RAW  – path to raw data folder   (default: data/raw)
  OLIST_DB   – path to the SQLite file    (default: C:/work/olist.sqlite)
  OLIST_OUT  – path to outputs folder     (default: outputs)

Run without real data:  pytest -q
Run with real data:     $env:OLIST_DB="C:\\work\\olist.sqlite"; pytest -q
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# ─── config ──────────────────────────────────────────────────────────────────

RAW = Path(os.environ.get("OLIST_RAW", "data/raw"))
DB  = Path(os.environ.get("OLIST_DB",  "C:/work/olist.sqlite"))
OUT = Path(os.environ.get("OLIST_OUT", "outputs"))

REAL_DATA = DB.exists() and (OUT / "out_kpi_overall.csv").exists()

# ─── Add src/ to sys.path ─────────────────────────────────────────────────────
_src = Path(__file__).parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from stats import wilson_ci, shift_share


# ─── real-data fixtures ───────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def conn():
    if not DB.exists():
        pytest.skip(f"Database not found at {DB}; run the pipeline first.")
    c = sqlite3.connect(str(DB))
    yield c
    c.close()


# ─── synthetic DB fixture (for T02-T08) ──────────────────────────────────────

@pytest.fixture(scope="session")
def synth_conn():
    """Build a tiny SQLite DB from synthetic data and run the full SQL pipeline."""
    tmp = tempfile.mktemp(suffix=".sqlite")
    c = sqlite3.connect(tmp)
    c.execute("PRAGMA journal_mode=WAL")

    c.execute("""CREATE TABLE raw_orders (
        order_id TEXT, customer_id TEXT, order_status TEXT,
        order_purchase_timestamp TEXT, order_approved_at TEXT,
        order_delivered_carrier_date TEXT, order_delivered_customer_date TEXT,
        order_estimated_delivery_date TEXT)""")
    c.executemany("INSERT INTO raw_orders VALUES (?,?,?,?,?,?,?,?)", [
        ("O1","C1","delivered","2017-03-01 10:00:00","2017-03-01 11:00:00",
         "2017-03-03 08:00:00","2017-03-08 14:00:00","2017-03-10 00:00:00"),
        ("O2","C2","delivered","2017-04-01 10:00:00","2017-04-01 11:00:00",
         "2017-04-03 08:00:00","2017-04-15 14:00:00","2017-04-10 00:00:00"),  # LATE
        ("O3","C3","delivered","2017-05-01 10:00:00","2017-05-01 11:00:00",
         "2017-05-03 08:00:00","2017-05-07 14:00:00","2017-05-09 00:00:00"),
        ("O4","C4","shipped","2017-06-01 10:00:00","2017-06-01 11:00:00",
         None, None, "2017-06-20 00:00:00"),
    ])

    c.execute("""CREATE TABLE raw_order_items (
        order_id TEXT, order_item_id TEXT, product_id TEXT, seller_id TEXT,
        shipping_limit_date TEXT, price TEXT, freight_value TEXT)""")
    c.executemany("INSERT INTO raw_order_items VALUES (?,?,?,?,?,?,?)", [
        ("O1","1","P1","S1","2017-03-05 00:00:00","100.0","15.0"),
        ("O2","1","P2","S2","2017-04-05 00:00:00","200.0","20.0"),
        ("O3","1","P3","S3","2017-05-05 00:00:00","50.0","8.0"),
        ("O3","2","P4","S3","2017-05-05 00:00:00","30.0","5.0"),
        ("O4","1","P1","S1","2017-06-05 00:00:00","80.0","12.0"),
    ])

    c.execute("""CREATE TABLE raw_reviews (
        order_id TEXT, review_id TEXT, review_score TEXT,
        review_creation_date TEXT, review_answer_timestamp TEXT)""")
    c.executemany("INSERT INTO raw_reviews VALUES (?,?,?,?,?)", [
        ("O1","R1","5","2017-03-09 00:00:00","2017-03-09 10:00:00"),
        ("O2","R2","1","2017-04-12 00:00:00","2017-04-12 10:00:00"),
        ("O3","R3","4","2017-05-08 00:00:00","2017-05-08 10:00:00"),
    ])

    c.execute("CREATE TABLE raw_customers (customer_id TEXT, customer_unique_id TEXT, customer_state TEXT)")
    c.executemany("INSERT INTO raw_customers VALUES (?,?,?)", [
        ("C1","U1","SP"), ("C2","U2","RJ"), ("C3","U3","MG"), ("C4","U4","SP"),
    ])

    c.execute("CREATE TABLE raw_sellers (seller_id TEXT, seller_city TEXT, seller_state TEXT)")
    c.executemany("INSERT INTO raw_sellers VALUES (?,?,?)", [
        ("S1","Sao Paulo","SP"), ("S2","Rio","RJ"), ("S3","BH","MG"),
    ])

    c.execute("CREATE TABLE raw_products (product_id TEXT, product_category_name TEXT)")
    c.executemany("INSERT INTO raw_products VALUES (?,?)", [
        ("P1","eletronicos"), ("P2","livros"), ("P3","brinquedos"), ("P4","brinquedos"),
    ])

    c.execute("CREATE TABLE raw_category_translation (product_category_name TEXT, product_category_name_english TEXT)")
    c.executemany("INSERT INTO raw_category_translation VALUES (?,?)", [
        ("eletronicos","electronics"), ("livros","books"), ("brinquedos","toys"),
    ])

    c.execute("CREATE TABLE raw_leads (mql_id TEXT, first_contact_date TEXT, landing_page_id TEXT, origin TEXT)")
    c.executemany("INSERT INTO raw_leads VALUES (?,?,?,?)", [
        ("L1","2017-07-01","PG1","organic_search"),
        ("L2","2017-08-01","PG2","paid_search"),
    ])

    c.execute("""CREATE TABLE raw_closed_deals (
        mql_id TEXT, seller_id TEXT, sdr_id TEXT, sr_id TEXT, won_date TEXT,
        business_segment TEXT, lead_type TEXT, lead_behaviour_profile TEXT,
        business_type TEXT, has_company TEXT, has_gtin TEXT,
        average_stock TEXT, declared_product_catalog_size TEXT,
        declared_monthly_revenue TEXT)""")
    c.executemany("INSERT INTO raw_closed_deals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [
        ("L1","S1","SDR1","SR1","2017-10-01 00:00:00","online","online_medium",
         None,"enterprise",None,None,None,None,"5000"),
    ])
    c.commit()

    sql_dir = Path(__file__).parent.parent / "sql"
    for fname in ["01_load_clean.sql","02_star_schema.sql","03_kpis.sql",
                  "04_funnel.sql","05_cohorts.sql","06_delivery_reviews.sql"]:
        c.executescript((sql_dir / fname).read_text(encoding="utf-8"))
        c.commit()

    yield c
    c.close()
    try:
        os.unlink(tmp)
    except Exception:
        pass


# ─── T01: row counts (real data only) ────────────────────────────────────────

@pytest.mark.skipif(not REAL_DATA, reason="real data not loaded")
def test_t01_row_counts(conn):
    """Public row counts must match: orders 99441, items 112650, etc."""
    for table, expected in [
        ("raw_orders", 99441), ("raw_order_items", 112650),
        ("raw_reviews", 99224), ("raw_customers", 99441),
        ("raw_sellers", 3095),  ("raw_leads", 8000), ("raw_closed_deals", 842),
    ]:
        actual = pd.read_sql_query(f"SELECT COUNT(*) AS n FROM {table}", conn).iloc[0]["n"]
        assert actual == expected, f"{table}: expected {expected}, got {actual}"


# ─── T02: unique grain on fact_orders ────────────────────────────────────────

def test_t02_fact_orders_unique_grain(synth_conn):
    """fact_orders must have exactly one row per order_id."""
    df = pd.read_sql_query(
        "SELECT order_id, COUNT(*) AS n FROM fact_orders GROUP BY order_id HAVING n > 1",
        synth_conn,
    )
    assert len(df) == 0, f"{len(df)} duplicate order_ids in fact_orders"


# ─── T03: no GMV double-counting ─────────────────────────────────────────────

def test_t03_no_gmv_double_count(synth_conn):
    """GMV in fact_orders must equal sum of item prices in fact_order_items."""
    item_gmv = pd.read_sql_query(
        "SELECT order_id, SUM(price) AS item_sum FROM fact_order_items GROUP BY order_id",
        synth_conn,
    )
    order_gmv = pd.read_sql_query(
        "SELECT order_id, item_value FROM fact_orders WHERE item_value IS NOT NULL",
        synth_conn,
    )
    merged = item_gmv.merge(order_gmv, on="order_id")
    diff = (merged["item_sum"] - merged["item_value"]).abs()
    assert (diff < 0.01).all(), f"GMV mismatch in {(diff >= 0.01).sum()} orders"


# ─── T04: late-flag consistency ──────────────────────────────────────────────

def test_t04_late_flag_consistency(synth_conn):
    """is_late must equal (delay_days > 0) for all delivered-valid orders."""
    df = pd.read_sql_query(
        """SELECT order_id, is_late, delay_days FROM fact_orders
           WHERE delivered_valid = 1 AND delay_days IS NOT NULL""",
        synth_conn,
    )
    expected_late = (df["delay_days"] > 0).astype(int)
    mismatches = (df["is_late"] != expected_late).sum()
    assert mismatches == 0, f"{mismatches} late-flag mismatches"


# ─── T05: stage times add up ─────────────────────────────────────────────────

def test_t05_stage_times_add_up(synth_conn):
    """dispatch_days + transit_days must be within 1 day of total elapsed for stage-valid orders."""
    df = pd.read_sql_query(
        """SELECT order_id, dispatch_days, transit_days, purchase_ts, delivered_ts
           FROM fact_orders
           WHERE stage_valid = 1 AND dispatch_days IS NOT NULL AND transit_days IS NOT NULL""",
        synth_conn,
    )

    def elapsed_days(r):
        try:
            ts = datetime.strptime(r["purchase_ts"][:19], "%Y-%m-%d %H:%M:%S")
            td = datetime.strptime(r["delivered_ts"][:19], "%Y-%m-%d %H:%M:%S")
            return (td - ts).total_seconds() / 86400
        except Exception:
            return np.nan

    df["elapsed"] = df.apply(elapsed_days, axis=1)
    diff = (df["elapsed"] - (df["dispatch_days"] + df["transit_days"])).abs().dropna()
    assert (diff < 1.0).all(), f"Stage time mismatch in {(diff >= 1).sum()} orders"


# ─── T06: funnel waterfall non-increasing ────────────────────────────────────

def test_t06_funnel_waterfall(synth_conn):
    """Funnel stages (leads -> deals -> sellers) must be non-increasing."""
    wf = pd.read_sql_query("SELECT stage, value FROM out_funnel_waterfall ORDER BY ord", synth_conn)
    wf_d = dict(zip(wf["stage"], wf["value"]))
    assert wf_d["all_leads"] >= wf_d["closed_deals"], "leads < deals"
    assert wf_d["closed_deals"] >= wf_d["deal_sellers_in_sellers_table"], "deals < sellers_in_table"
    assert wf_d["deal_sellers_in_sellers_table"] >= wf_d["deal_sellers_with_delivered_order"], "sellers not monotone"


# ─── T07: funnel equals pandas audit (real data only) ────────────────────────

@pytest.mark.skipif(not REAL_DATA, reason="real data not loaded")
def test_t07_funnel_equals_pandas_audit(conn):
    """SQL funnel waterfall must match audit.py real-data numbers."""
    wf = pd.read_sql_query("SELECT stage, value FROM out_funnel_waterfall", conn)
    wf_d = dict(zip(wf["stage"], wf["value"]))
    assert int(wf_d["all_leads"]) == 8000
    assert int(wf_d["closed_deals"]) == 842
    assert int(wf_d["deal_sellers_in_sellers_table"]) == 380
    assert int(wf_d["deal_sellers_with_delivered_order"]) == 376


# ─── T08: window rules ───────────────────────────────────────────────────────

def test_t08_window_rules(synth_conn):
    """No in-window orders outside 2017-01-01 to 2018-08-31."""
    df = pd.read_sql_query("SELECT purchase_month FROM fact_orders WHERE in_window = 1", synth_conn)
    assert (df["purchase_month"] >= "2017-01").all(), "in_window order before 2017-01"
    assert (df["purchase_month"] < "2018-09").all(), "in_window order after 2018-08"


# ─── T09: simulator monotonic ────────────────────────────────────────────────

def test_t09_simulator_monotonic():
    """run_scenarios: more sellers fixed -> more late orders avoided (weakly monotonic)."""
    from simulator import run_scenarios

    rng = np.random.default_rng(0)
    n = 500
    seller_ids = rng.choice([f"S{i:03d}" for i in range(50)], size=n)
    dispatch = rng.uniform(1, 10, size=n)
    delay = dispatch - np.median(dispatch) + rng.uniform(-2, 2, size=n)
    df = pd.DataFrame({
        "order_id": range(n), "in_window": 1, "delivered_valid": 1, "stage_valid": 1,
        "seller_id": seller_ids, "dispatch_days": dispatch, "delay_days": delay,
        "is_late": (delay > 0).astype(int),
        "review_score": rng.choice([1, 2, 3, 4, 5], size=n),
    })
    res = run_scenarios(df, pcts=(0.05, 0.10, 0.20), min_orders=5)
    avoided = res["late_orders_avoided"].tolist()
    for i in range(len(avoided) - 1):
        assert avoided[i] <= avoided[i + 1], f"Not monotonic: {avoided}"


# ─── T10: Wilson CI known value ──────────────────────────────────────────────

def test_t10_wilson_ci():
    """Wilson CI for 842/8000 should be close to 9.87-11.22%."""
    lo, hi = wilson_ci(842, 8000)
    assert abs(lo - 0.0987) < 0.002, f"Wilson CI lo = {lo:.4f}, expected ~0.0987"
    assert abs(hi - 0.1122) < 0.002, f"Wilson CI hi = {hi:.4f}, expected ~0.1122"


# ─── T11: shift-share decomposition exact ────────────────────────────────────

def test_t11_shift_share():
    """mix_effect + rate_effect must sum exactly to the overall change."""
    normal = pd.DataFrame({"state": ["A", "B"], "orders": [1000, 500], "late": [40, 30]})
    bad    = pd.DataFrame({"state": ["A", "B"], "orders": [800,  600], "late": [80, 90]})
    res = shift_share(normal, bad, "state", "orders", "late")
    reconstructed = res["mix_effect"] + res["rate_effect"]
    assert abs(res["change"] - reconstructed) < 1e-8, (
        f"Mismatch: change={res['change']:.8f} vs mix+rate={reconstructed:.8f}"
    )
