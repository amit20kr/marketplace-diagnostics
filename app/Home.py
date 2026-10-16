"""app/Home.py - entry point for the Streamlit multi-page app (pages 1-6).

Navigation via st.navigation. Global sidebar filters live in st.session_state.
Reads ONLY outputs/ (via data.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parent
for p in [str(APP_DIR), str(ROOT / "src")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from data import load_orders, get_filter_options  # noqa: E402

st.set_page_config(
    page_title="Olist Seller Diagnostics",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = [
    st.Page("pages/1_Executive_Summary.py", title="Executive Summary", icon="🏠"),
    st.Page("pages/2_Acquisition_Funnel.py", title="Acquisition Funnel", icon="🔭"),
    st.Page("pages/3_Seller_Cohorts.py", title="Seller Cohorts", icon="👥"),
    st.Page("pages/4_Delivery_Diagnostics.py", title="Delivery Diagnostics", icon="🚚"),
    st.Page("pages/5_Data_Trust.py", title="Data Trust & Robustness", icon="🛡️"),
    st.Page("pages/6_Action_Plan.py", title="Action Plan", icon="🧭"),
]
pg = st.navigation(pages)

# Initialise filter state BEFORE the widgets are created (no default= with key=)
for _k in ("sel_months", "sel_states", "sel_categories"):
    st.session_state.setdefault(_k, [])


def _reset_filters() -> None:
    """on_click callback: safe place to modify widget-bound session state."""
    for k in ("sel_months", "sel_states", "sel_categories"):
        st.session_state[k] = []


with st.sidebar:
    st.markdown("## 📦 Olist Diagnostics")
    st.caption("Seller Acquisition & Delivery Analysis · 2017-01 to 2018-08")
    st.divider()
    st.markdown("### 🔽 Global Filters")
    st.caption("Applied to order-level charts only. Funnel and cohort pages are unaffected.")

    orders = load_orders()
    all_months, all_states, all_categories = get_filter_options(orders)

    st.multiselect("Month", all_months, key="sel_months", placeholder="All months")
    st.multiselect("Customer State", all_states, key="sel_states", placeholder="All states")
    st.multiselect("Category", all_categories, key="sel_categories", placeholder="All categories")
    st.button("🔄 Reset Filters", on_click=_reset_filters)

    st.divider()
    st.caption(
        "Data: [Olist Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) "
        "(CC BY-NC-SA 4.0). Attribution: Olist. Portfolio project, non-commercial."
    )

pg.run()
