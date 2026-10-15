"""Hand-built mini Olist dataset with KNOWN answers (13 orders, 4 sellers, 4 leads, 3 deals).

Purpose: lets the SQL pipeline (sql/01..06) be unit-tested on every machine, with or without the
real data. Each order exists to exercise one rule; the expected values are asserted in
tests/test_pipeline.py. This data says NOTHING about the real Olist business.

    order  what it tests
    O1     plain on-time order (single seller)
    O2     late by 5 days (band 4-7); its review was written BEFORE delivery (survey timing, L-009)
    O3     two items, same seller (GMV must not double count); two reviews -> dedup keeps the latest (D-003)
    O4     status 'shipped' (never delivered)
    O5     status 'delivered' but no delivery date -> not delivered-valid (D-002)
    O6     purchased 2016-12 (before the window, D-011)
    O7     purchased 2018-09 (after the window, D-011)
    O8     two sellers in one order -> seller_id NULL (D-018)
    O9     carrier hand-off AFTER delivery -> stage-invalid (D-004)
    O10    delivered 15:00 on the estimated DATE -> on time at date level, late at timestamp level (D-012)
    O11    delivered order without any item
    O12    later order of deal seller S1; review written before delivery
    O13    first order of deal seller S4 (45 days after the deal was won)
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

SQL_FILES = ["01_load_clean.sql", "02_star_schema.sql", "03_kpis.sql",
             "04_funnel.sql", "05_cohorts.sql", "06_delivery_reviews.sql"]

_ORDER_COLS = ["order_id", "customer_id", "order_status", "order_purchase_timestamp", "order_approved_at",
               "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date"]


def _frames() -> dict[str, pd.DataFrame]:
    n = None
    orders = [
        ("O1", "C1", "delivered", "2017-03-01 10:00:00", "2017-03-01 11:00:00", "2017-03-03 08:00:00", "2017-03-08 14:00:00", "2017-03-10 00:00:00"),
        ("O2", "C2", "delivered", "2017-04-01 10:00:00", "2017-04-01 11:00:00", "2017-04-03 08:00:00", "2017-04-15 14:00:00", "2017-04-10 00:00:00"),
        ("O3", "C3", "delivered", "2017-05-01 10:00:00", "2017-05-01 11:00:00", "2017-05-03 08:00:00", "2017-05-07 14:00:00", "2017-05-09 00:00:00"),
        ("O4", "C4", "shipped", "2017-06-01 10:00:00", "2017-06-01 11:00:00", n, n, "2017-06-20 00:00:00"),
        ("O5", "C5", "delivered", "2017-06-10 10:00:00", "2017-06-10 11:00:00", "2017-06-12 08:00:00", n, "2017-06-25 00:00:00"),
        ("O6", "C6", "delivered", "2016-12-15 10:00:00", "2016-12-15 11:00:00", "2016-12-17 08:00:00", "2016-12-28 14:00:00", "2016-12-30 00:00:00"),
        ("O7", "C7", "delivered", "2018-09-05 10:00:00", "2018-09-05 11:00:00", "2018-09-07 08:00:00", "2018-09-20 14:00:00", "2018-09-25 00:00:00"),
        ("O8", "C8", "delivered", "2017-07-01 10:00:00", "2017-07-01 11:00:00", "2017-07-03 08:00:00", "2017-07-09 12:00:00", "2017-07-15 00:00:00"),
        ("O9", "C9", "delivered", "2017-08-01 10:00:00", "2017-08-01 11:00:00", "2017-08-10 09:00:00", "2017-08-08 12:00:00", "2017-08-20 00:00:00"),
        ("O10", "C10", "delivered", "2017-09-01 10:00:00", "2017-09-01 11:00:00", "2017-09-03 08:00:00", "2017-09-10 15:00:00", "2017-09-10 00:00:00"),
        ("O11", "C11", "delivered", "2017-09-15 10:00:00", "2017-09-15 11:00:00", "2017-09-17 08:00:00", "2017-09-25 14:00:00", "2017-09-30 00:00:00"),
        ("O12", "C12", "delivered", "2017-10-20 10:00:00", "2017-10-20 11:00:00", "2017-10-22 08:00:00", "2017-10-30 14:00:00", "2017-11-05 00:00:00"),
        ("O13", "C13", "delivered", "2017-11-15 10:00:00", "2017-11-15 11:00:00", "2017-11-17 08:00:00", "2017-11-25 14:00:00", "2017-12-01 00:00:00"),
    ]
    items = [  # order_id, item_id, product_id, seller_id, shipping_limit_date, price, freight
        ("O1", "1", "P1", "S1", "2017-03-05 00:00:00", "100.0", "15.0"),
        ("O2", "1", "P2", "S2", "2017-04-05 00:00:00", "200.0", "20.0"),
        ("O3", "1", "P3", "S3", "2017-05-05 00:00:00", "50.0", "8.0"),
        ("O3", "2", "P4", "S3", "2017-05-05 00:00:00", "30.0", "5.0"),
        ("O4", "1", "P1", "S1", "2017-06-05 00:00:00", "80.0", "12.0"),
        ("O5", "1", "P2", "S2", "2017-06-15 00:00:00", "60.0", "6.0"),
        ("O6", "1", "P3", "S3", "2016-12-20 00:00:00", "40.0", "4.0"),
        ("O7", "1", "P3", "S3", "2018-09-10 00:00:00", "40.0", "4.0"),
        ("O8", "1", "P1", "S1", "2017-07-05 00:00:00", "70.0", "7.0"),
        ("O8", "2", "P2", "S2", "2017-07-05 00:00:00", "30.0", "3.0"),
        ("O9", "1", "P3", "S3", "2017-08-05 00:00:00", "55.0", "5.0"),
        ("O10", "1", "P2", "S2", "2017-09-05 00:00:00", "90.0", "9.0"),
        ("O12", "1", "P1", "S1", "2017-10-25 00:00:00", "120.0", "12.0"),
        ("O13", "1", "P5", "S4", "2017-11-20 00:00:00", "150.0", "15.0"),
    ]
    reviews = [  # order_id, review_id, score, created, answered
        ("O1", "R1", "5", "2017-03-09 00:00:00", "2017-03-09 10:00:00"),
        ("O2", "R2", "1", "2017-04-12 00:00:00", "2017-04-12 10:00:00"),
        ("O3", "R3", "4", "2017-05-08 00:00:00", "2017-05-08 10:00:00"),
        ("O3", "R3b", "2", "2017-05-09 00:00:00", "2017-05-09 10:00:00"),
        ("O10", "R10", "5", "2017-09-11 00:00:00", "2017-09-11 10:00:00"),
        ("O12", "R12", "4", "2017-10-29 00:00:00", "2017-10-29 10:00:00"),
        ("O13", "R13", "5", "2017-11-26 00:00:00", "2017-11-26 10:00:00"),
    ]
    states = ["SP", "RJ", "MG", "SP", "SP", "SP", "RJ", "SP", "MG", "RJ", "SP", "SP", "MG"]
    customers = [(f"C{i + 1}", f"U{i + 1}", s) for i, s in enumerate(states)]
    return {
        "orders": pd.DataFrame(orders, columns=_ORDER_COLS),
        "order_items": pd.DataFrame(items, columns=["order_id", "order_item_id", "product_id", "seller_id",
                                                    "shipping_limit_date", "price", "freight_value"]),
        "reviews": pd.DataFrame(reviews, columns=["order_id", "review_id", "review_score",
                                                  "review_creation_date", "review_answer_timestamp"]),
        "customers": pd.DataFrame(customers, columns=["customer_id", "customer_unique_id", "customer_state"]),
        "sellers": pd.DataFrame([("S1", "Sao Paulo", "SP"), ("S2", "Rio", "RJ"), ("S3", "BH", "MG"), ("S4", "Campinas", "SP")],
                                columns=["seller_id", "seller_city", "seller_state"]),
        "products": pd.DataFrame([("P1", "eletronicos"), ("P2", "livros"), ("P3", "brinquedos"), ("P4", "brinquedos"), ("P5", "livros")],
                                 columns=["product_id", "product_category_name"]),
        "category_translation": pd.DataFrame([("eletronicos", "electronics"), ("livros", "books"), ("brinquedos", "toys")],
                                             columns=["product_category_name", "product_category_name_english"]),
        "leads": pd.DataFrame([("L1", "2017-07-01", "PG1", "organic_search"),
                               ("L2", "2017-08-01", "PG2", "paid_search"),
                               ("L3", "2017-08-15", "PG1", None),
                               ("L4", "2017-09-01", "PG2", "organic_search")],
                              columns=["mql_id", "first_contact_date", "landing_page_id", "origin"]),
        "closed_deals": pd.DataFrame([("L1", "S1", "SDR1", "SR1", "2017-10-01 00:00:00", "home", "online_medium", None, "reseller"),
                                      ("L2", "S4", "SDR1", "SR1", "2017-10-01 12:00:00", "home", "online_big", None, "reseller"),
                                      ("L3", "S9", "SDR2", "SR2", "2017-10-10 00:00:00", "auto", "online_small", None, "reseller")],
                                     columns=["mql_id", "seller_id", "sdr_id", "sr_id", "won_date", "business_segment",
                                              "lead_type", "lead_behaviour_profile", "business_type"]),
    }


def build_synthetic_db(sql_dir: Path | str | None = None) -> tuple[sqlite3.Connection, dict[str, pd.DataFrame]]:
    """Return (in-memory connection with raw_* tables + sql/01..06 applied, raw DataFrames)."""
    sql_dir = Path(sql_dir) if sql_dir else Path(__file__).resolve().parents[1] / "sql"
    frames = _frames()
    con = sqlite3.connect(":memory:")
    for name, df in frames.items():
        df.to_sql(f"raw_{name}", con, index=False, if_exists="replace")  # text columns stay TEXT, like the real loader
    for fname in SQL_FILES:
        con.executescript((sql_dir / fname).read_text(encoding="utf-8"))
        con.commit()
    return con, frames
