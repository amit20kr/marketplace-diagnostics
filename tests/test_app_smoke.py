"""tests/test_app_smoke.py - Smoke tests for Streamlit app pages (default state)."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).resolve().parent.parent / "app"


def test_executive_summary_smoke():
    at = AppTest.from_file(str(APP_DIR / "pages" / "1_Executive_Summary.py"), default_timeout=30)
    at.run()
    assert not at.exception, f"Exceptions found: {at.exception}"


def test_acquisition_funnel_smoke():
    at = AppTest.from_file(str(APP_DIR / "pages" / "2_Acquisition_Funnel.py"), default_timeout=30)
    at.run()
    assert not at.exception, f"Exceptions found: {at.exception}"


def test_seller_cohorts_smoke():
    at = AppTest.from_file(str(APP_DIR / "pages" / "3_Seller_Cohorts.py"), default_timeout=30)
    at.run()
    assert not at.exception, f"Exceptions found: {at.exception}"


def test_delivery_diagnostics_smoke():
    at = AppTest.from_file(str(APP_DIR / "pages" / "4_Delivery_Diagnostics.py"), default_timeout=30)
    at.run()
    assert not at.exception, f"Exceptions found: {at.exception}"


def test_data_trust_smoke():
    at = AppTest.from_file(str(APP_DIR / "pages" / "5_Data_Trust.py"), default_timeout=30)
    at.run()
    assert not at.exception, f"Exceptions found: {at.exception}"


def test_action_plan_smoke():
    at = AppTest.from_file(str(APP_DIR / "pages" / "6_Action_Plan.py"), default_timeout=30)
    at.run()
    assert not at.exception, f"Exceptions found: {at.exception}"


def test_empty_filter_smoke():
    """Assert no exceptions on pages 1 and 4 when an empty month/state combination is filtered."""
    # ('2017-01', 'AM') has zero rows in outputs/app_orders.csv.gz
    at1 = AppTest.from_file(str(APP_DIR / "pages" / "1_Executive_Summary.py"), default_timeout=30)
    at1.session_state["sel_months"] = ["2017-01"]
    at1.session_state["sel_states"] = ["AM"]
    at1.run()
    assert not at1.exception, f"Exception on page 1 with empty filter: {at1.exception}"

    at4 = AppTest.from_file(str(APP_DIR / "pages" / "4_Delivery_Diagnostics.py"), default_timeout=30)
    at4.session_state["sel_months"] = ["2017-01"]
    at4.session_state["sel_states"] = ["AM"]
    at4.run()
    assert not at4.exception, f"Exception on page 4 with empty filter: {at4.exception}"

