"""run_pipeline.py – one-command pipeline: CSV -> SQLite -> out_*.csv -> analysis.

Usage:
    python src/run_pipeline.py --raw data/raw --db C:\\work\\olist.sqlite --out outputs

The database is built outside OneDrive to avoid sync-lock issues (AGENTS.md section 6).
Each SQL file (01-06) is executed in order. All out_* tables are exported to --out/.
Slim app files (app_orders.csv.gz, app_funnel.csv) are also written.
Then src/analysis.py is called to write stat_*.csv and analysis_summary.json.

Never modifies data/raw/. Cleans and recreates the database on every run.
"""
from __future__ import annotations

import argparse
import importlib
import sys
import sqlite3
from pathlib import Path


# ─── file discovery (D-010: folder names contain spaces) ─────────────────────

FILES = {
    "orders":               "olist_orders_dataset.csv",
    "order_items":          "olist_order_items_dataset.csv",
    "payments":             "olist_order_payments_dataset.csv",
    "reviews":              "olist_order_reviews_dataset.csv",
    "customers":            "olist_customers_dataset.csv",
    "sellers":              "olist_sellers_dataset.csv",
    "products":             "olist_products_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
    "leads":                "olist_marketing_qualified_leads_dataset.csv",
    "closed_deals":         "olist_closed_deals_dataset.csv",
    # geolocation is NOT loaded (D-014); audit.py handles it
}


def find_csv(raw_root: Path, filename: str) -> Path:
    """Recursively locate filename under raw_root (folders may have spaces)."""
    matches = list(raw_root.rglob(filename))
    if not matches:
        raise FileNotFoundError(f"Could not find {filename!r} under {raw_root}")
    if len(matches) > 1:
        print(f"  [warn] multiple copies of {filename!r}; using {matches[0]}")
    return matches[0]


# ─── load CSVs into raw_* TEXT tables ────────────────────────────────────────

def load_raw(conn: sqlite3.Connection, raw_root: Path) -> None:
    import pandas as pd

    for key, filename in FILES.items():
        table = f"raw_{key}"
        path = find_csv(raw_root, filename)
        print(f"  [load] {path.name} -> {table}")
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        # Replace empty strings with None so SQLite stores NULL
        df = df.replace("", None)
        df.to_sql(table, conn, if_exists="replace", index=False)
    conn.commit()


# ─── run SQL scripts ──────────────────────────────────────────────────────────

def run_sql_file(conn: sqlite3.Connection, path: Path) -> None:
    print(f"  [sql] {path.name}")
    sql = path.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()


# ─── export out_* tables to CSV ──────────────────────────────────────────────

def export_tables(conn: sqlite3.Connection, out_dir: Path) -> list[str]:
    import pandas as pd

    out_dir.mkdir(parents=True, exist_ok=True)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'out_%' ORDER BY name"
    )
    tables = [r[0] for r in cursor]
    exported = []
    for tbl in tables:
        df = pd.read_sql_query(f"SELECT * FROM [{tbl}]", conn)
        dest = out_dir / f"{tbl}.csv"
        df.to_csv(dest, index=False)
        exported.append(tbl)
        print(f"  [export] {tbl} ({len(df)} rows) -> {dest.name}")
    return exported


# ─── write slim app files ─────────────────────────────────────────────────────

def write_app_files(conn: sqlite3.Connection, out_dir: Path) -> None:
    import pandas as pd

    orders = pd.read_sql_query("SELECT * FROM out_app_orders", conn)
    gz_path = out_dir / "app_orders.csv.gz"
    orders.to_csv(gz_path, index=False, compression="gzip")
    print(f"  [app] app_orders.csv.gz ({len(orders)} rows, {gz_path.stat().st_size / 1e6:.1f} MB)")

    funnel = pd.read_sql_query("SELECT * FROM out_app_funnel", conn)
    funnel_path = out_dir / "app_funnel.csv"
    funnel.to_csv(funnel_path, index=False)
    print(f"  [app] app_funnel.csv ({len(funnel)} rows)")


# ─── main ─────────────────────────────────────────────────────────────────────

def main(raw: str, db: str, out: str, sql_dir: str | None = None) -> None:
    raw_root = Path(raw)
    db_path = Path(db)
    out_dir = Path(out)

    if sql_dir is None:
        # locate sql/ relative to this script's location (src/../sql)
        sql_dir_path = Path(__file__).parent.parent / "sql"
    else:
        sql_dir_path = Path(sql_dir)

    sql_files = [
        sql_dir_path / "01_load_clean.sql",
        sql_dir_path / "02_star_schema.sql",
        sql_dir_path / "03_kpis.sql",
        sql_dir_path / "04_funnel.sql",
        sql_dir_path / "05_cohorts.sql",
        sql_dir_path / "06_delivery_reviews.sql",
    ]
    for sf in sql_files:
        if not sf.exists():
            raise FileNotFoundError(f"SQL file missing: {sf}")

    # Recreate the database (idempotent)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
        print(f"  [db] removed old {db_path}")

    print(f"  [db] creating {db_path}")
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA cache_size=-64000")  # 64 MB

    try:
        load_raw(conn, raw_root)
        for sf in sql_files:
            run_sql_file(conn, sf)
        export_tables(conn, out_dir)
        write_app_files(conn, out_dir)
    finally:
        conn.close()

    # Run analysis layer
    print("  [pipeline] running analysis.py …")
    src_dir = Path(__file__).parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    # Re-import fresh each time (in case of repeated calls in tests)
    import importlib
    if "analysis" in sys.modules:
        analysis = importlib.reload(sys.modules["analysis"])
    else:
        import analysis
    analysis.main(out_dir)

    print(f"\n  [pipeline] DONE. outputs in {out_dir}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Olist pipeline: CSV -> SQLite -> CSVs -> analysis")
    parser.add_argument("--raw", required=True, help="path to raw data root (data/raw)")
    parser.add_argument("--db", required=True, help="path to SQLite database (outside OneDrive)")
    parser.add_argument("--out", required=True, help="output directory for CSV/JSON files")
    parser.add_argument("--sql", default=None, help="path to sql/ directory (default: auto-detect)")
    args = parser.parse_args()
    main(args.raw, args.db, args.out, args.sql)
