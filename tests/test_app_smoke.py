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
