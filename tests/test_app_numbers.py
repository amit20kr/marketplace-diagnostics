"""tests/test_app_numbers.py - Verify rendered metrics match analysis_summary.json and test empty filters."""
import json
from pathlib import Path
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).resolve().parent.parent / "app"
ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def summary():
    summary_path = ROOT / "outputs" / "analysis_summary.json"
    with open(summary_path, encoding="utf-8") as f:
        return json.load(f)


def test_executive_summary_metrics(summary):
    at = AppTest.from_file(str(APP_DIR / "pages" / "1_Executive_Summary.py"), default_timeout=30)
    at.run()
    assert not at.exception, f"Exceptions on page 1: {at.exception}"

    metrics = {m.label: m.value for m in at.metric}

    # delivered_valid_orders formatted with commas
    expected_orders = f"{summary['kpi']['delivered_valid_orders']:,}"
    assert metrics.get("Delivered orders") == expected_orders

    # late rate
    expected_late = f"{summary['kpi']['late_rate'] * 100:.2f}%"
    assert metrics.get("Late rate") == expected_late

    # lead-to-deal rate
    expected_lead_deal = f"{summary['funnel']['lead_to_deal_rate'] * 100:.1f}%"
    assert metrics.get("Lead \u2192 deal rate") == expected_lead_deal


def test_acquisition_funnel_metrics(summary):
    at = AppTest.from_file(str(APP_DIR / "pages" / "2_Acquisition_Funnel.py"), default_timeout=30)
    at.run()
    assert not at.exception, f"Exceptions on page 2: {at.exception}"

    # Verify metrics on page 2 match analysis_summary.json
    metrics = {m.label: m.value for m in at.metric}
    fn = summary["funnel"]
    expected_dtc_median = f"{fn['days_to_close']['median']:.0f}"
    assert metrics.get("Median days to close") == expected_dtc_median
    assert metrics.get("Closed within 30 days") == f"{fn['days_to_close']['share_within_30'] * 100:.1f}%"
    assert metrics.get("Closed within 90 days") == f"{fn['days_to_close']['share_within_90'] * 100:.1f}%"
    assert metrics.get("SDRs") == str(fn["sdr"]["total_sdrs"])


def test_empty_filter_no_exception():
    # Find a (customer_state, category) pair with zero rows in outputs/app_orders.csv.gz
    df = pd.read_csv(ROOT / "outputs" / "app_orders.csv.gz")
    existing_pairs = set(zip(df["customer_state"], df["category"]))

    empty_pair = None
    for s in sorted(df["customer_state"].dropna().unique()):
        for c in sorted(df["category"].dropna().unique()):
            if (s, c) not in existing_pairs:
                empty_pair = (s, c)
                break
        if empty_pair is not None:
            break

    assert empty_pair is not None, "Could not find an empty (state, category) pair"
    state, category = empty_pair

    # Run page 1 with empty filter in session_state
    at1 = AppTest.from_file(str(APP_DIR / "pages" / "1_Executive_Summary.py"), default_timeout=30)
    at1.session_state["sel_states"] = [state]
    at1.session_state["sel_categories"] = [category]
    at1.run()
    assert not at1.exception, f"Exception on page 1 with empty filter: {at1.exception}"

    # Run page 4 with empty filter in session_state
    at4 = AppTest.from_file(str(APP_DIR / "pages" / "4_Delivery_Diagnostics.py"), default_timeout=30)
    at4.session_state["sel_states"] = [state]
    at4.session_state["sel_categories"] = [category]
    at4.run()
    assert not at4.exception, f"Exception on page 4 with empty filter: {at4.exception}"
