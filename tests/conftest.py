"""Shared test setup: where the real artefacts live, and the fixtures every test uses.

Two data modes (D-029, revised by D-030):
  synthetic  tests/synth_db.py, built in memory from sql/01..06. Runs on EVERY machine, no data needed.
  real       the pipeline's SQLite database and outputs/. Added automatically when they exist.
The header printed by pytest tells you which mode you are in; `-ra` (pytest.ini) lists skip reasons.

Paths are anchored to the project root, so `pytest` works from any folder. Override with env vars:
  OLIST_RAW (raw CSV folder, default data/raw)   OLIST_DB (SQLite file, default C:/work/olist.sqlite)
  OLIST_OUT (outputs folder, default outputs)
"""
from __future__ import annotations

import os
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "src", ROOT / "tests"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from synth_db import build_synthetic_db  # noqa: E402


def _path(env_name: str, default) -> Path:
    p = Path(os.environ.get(env_name, default))
    return p if p.is_absolute() else ROOT / p


RAW = _path("OLIST_RAW", "data/raw")
DB = _path("OLIST_DB", "C:/work/olist.sqlite")
OUT = _path("OLIST_OUT", "outputs")


def _db_has_pipeline_tables(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        c = sqlite3.connect(str(path))
        try:
            names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            c.close()
        return {"fact_orders", "fact_order_items", "out_funnel_waterfall", "raw_orders"} <= names
    except sqlite3.Error:
        return False


REAL_DB = _db_has_pipeline_tables(DB)
REAL_RAW = RAW.exists() and any(RAW.rglob("olist_orders_dataset.csv"))
REAL_OUT = (OUT / "analysis_summary.json").exists() and (OUT / "out_kpi_overall.csv").exists()


@dataclass
class Env:
    mode: str                      # "synthetic" | "real"
    conn: sqlite3.Connection
    frames: dict                   # raw tables as DataFrames, keyed like raw_<name> (orders, order_items, closed_deals, ...)


def _read_real_frames() -> dict:
    def rd(name, **kw):
        return pd.read_csv(next(RAW.rglob(name)), **kw)
    return {
        "orders": rd("olist_orders_dataset.csv"),
        "order_items": rd("olist_order_items_dataset.csv"),
        "sellers": rd("olist_sellers_dataset.csv"),
        "leads": rd("olist_marketing_qualified_leads_dataset.csv"),
        "closed_deals": rd("olist_closed_deals_dataset.csv"),
    }


# ─── fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def synth_env():
    con, frames = build_synthetic_db(ROOT / "sql")
    yield Env("synthetic", con, frames)
    con.close()


@pytest.fixture(scope="session")
def real_env():
    if not REAL_DB:
        pytest.skip(f"real database not found / not built at {DB} (run src/run_pipeline.py or set OLIST_DB)")
    con = sqlite3.connect(str(DB))
    try:
        frames = _read_real_frames() if REAL_RAW else {}
        yield Env("real", con, frames)
    finally:
        con.close()


_MODES = ["synthetic"] + ([pytest.param("real", marks=pytest.mark.real)] if REAL_DB else [])


@pytest.fixture(scope="session", params=_MODES)
def env(request):
    """Structural tests run on the synthetic DB always, and on the real DB too when it exists."""
    return request.getfixturevalue("synth_env" if request.param == "synthetic" else "real_env")


@pytest.fixture(scope="session")
def real_summary():
    import json
    if not REAL_OUT:
        pytest.skip(f"saved pipeline outputs not found in {OUT} (run src/run_pipeline.py or set OLIST_OUT)")
    return json.loads((OUT / "analysis_summary.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def out_dir():
    if not REAL_OUT:
        pytest.skip(f"saved pipeline outputs not found in {OUT} (run src/run_pipeline.py or set OLIST_OUT)")
    return OUT


# ─── reporting: say plainly which mode ran ───────────────────────────────────

def pytest_configure(config):
    config.addinivalue_line("markers", "real: test that runs against the real Olist database / outputs")


def pytest_report_header(config):
    flag = lambda ok: "found" if ok else "MISSING"  # noqa: E731
    mode = "SYNTHETIC + REAL" if REAL_DB else "SYNTHETIC ONLY (checks that need the real database are skipped)"
    return [f"olist tests: {mode}",
            f"  db  : {DB} [{flag(REAL_DB)}]",
            f"  out : {OUT} [{flag(REAL_OUT)}]",
            f"  raw : {RAW} [{flag(REAL_RAW)}]"]


def pytest_terminal_summary(terminalreporter):
    passed = terminalreporter.stats.get("passed", [])
    n_real = sum(1 for r in passed if r.nodeid.endswith("[real]") or "real" in getattr(r, "keywords", {}))
    terminalreporter.write_sep("-", f"olist: {len(passed)} passed, of which {n_real} ran on REAL data (D-029)")
