"""Phase A data audit for the Olist project (pandas only, no DuckDB needed).

Usage (from the project root):
    python src/audit.py --raw data/raw --out outputs/audit

Finds the 11 CSVs anywhere under --raw (folder names may contain spaces),
profiles them, checks keys/orphans/dates/timestamps, and builds the funnel
join-coverage waterfall with DISTINCT keys. Writes CSVs + audit_summary.json
+ audit_summary.md. It never modifies raw files and never "fixes" data.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

FILES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
    "leads": "olist_marketing_qualified_leads_dataset.csv",
    "closed_deals": "olist_closed_deals_dataset.csv",
}
DATE_COLS = {
    "orders": ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
               "order_delivered_customer_date", "order_estimated_delivery_date"],
    "order_items": ["shipping_limit_date"],
    "reviews": ["review_creation_date", "review_answer_timestamp"],
    "leads": ["first_contact_date"],
    "closed_deals": ["won_date"],
}


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def md_table(df, max_rows=60):
    if df is None or len(df) == 0:
        return "_(empty)_\n"
    d = df.head(max_rows).astype(object)
    cols = [str(c) for c in d.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in r.tolist()) + " |")
    return "\n".join(lines) + "\n"


def load_all(raw):
    raw = Path(raw)
    tables, inv = {}, []
    for name, fname in FILES.items():
        matches = list(raw.rglob(fname))
        if not matches:
            inv.append({"table": name, "file": fname, "found": False})
            continue
        p = matches[0]
        df = pd.read_csv(p)
        for c in DATE_COLS.get(name, []):
            df[c] = pd.to_datetime(df[c], errors="coerce")
        tables[name] = df
        inv.append({"table": name, "file": fname, "found": True, "size_mb": round(p.stat().st_size / 1e6, 2),
                    "rows": len(df), "cols": df.shape[1], "sha256": sha256(p)})
    return tables, pd.DataFrame(inv)


def profile(tables):
    rows, tsum = [], []
    for name, df in tables.items():
        tsum.append({"table": name, "rows": len(df), "cols": df.shape[1],
                     "full_duplicate_rows": int(df.duplicated().sum())})
        for c in df.columns:
            rows.append({"table": name, "column": c, "dtype": str(df[c].dtype),
                         "nulls": int(df[c].isna().sum()),
                         "null_pct": round(100 * df[c].isna().mean(), 2),
                         "distinct": int(df[c].nunique(dropna=True))})
    return pd.DataFrame(tsum), pd.DataFrame(rows)


def dup_keys(df, cols):
    return int(df.duplicated(subset=cols).sum())


def orphan(child, ccol, parent, pcol):
    cvals = child[ccol].dropna()
    missing = ~cvals.isin(set(parent[pcol].dropna()))
    return {"child_rows_checked": len(cvals), "orphan_rows": int(missing.sum()),
            "orphan_distinct_keys": int(cvals[missing].nunique()),
            "orphan_pct_rows": round(100 * missing.mean(), 3) if len(cvals) else None}


def relationship_checks(t):
    keys = [
        ("orders", ["order_id"]), ("customers", ["customer_id"]), ("sellers", ["seller_id"]),
        ("products", ["product_id"]), ("leads", ["mql_id"]), ("closed_deals", ["mql_id"]),
        ("closed_deals", ["seller_id"]), ("order_items", ["order_id", "order_item_id"]),
        ("reviews", ["review_id"]), ("reviews", ["order_id"]), ("payments", ["order_id", "payment_sequential"]),
    ]
    krows = [{"table": tb, "key": "+".join(cols), "rows": len(t[tb]), "duplicate_rows_on_key": dup_keys(t[tb], cols)}
             for tb, cols in keys if tb in t]
    pairs = [
        ("order_items", "order_id", "orders", "order_id"), ("order_items", "product_id", "products", "product_id"),
        ("order_items", "seller_id", "sellers", "seller_id"), ("orders", "customer_id", "customers", "customer_id"),
        ("payments", "order_id", "orders", "order_id"), ("reviews", "order_id", "orders", "order_id"),
        ("closed_deals", "mql_id", "leads", "mql_id"), ("closed_deals", "seller_id", "sellers", "seller_id"),
        ("orders", "order_id", "order_items", "order_id"),
    ]
    orows = []
    for c, cc, p, pc in pairs:
        if c in t and p in t:
            orows.append({"child": f"{c}.{cc}", "parent": f"{p}.{pc}", **orphan(t[c], cc, t[p], pc)})
    if "geolocation" in t:
        g = t["geolocation"].rename(columns={"geolocation_zip_code_prefix": "zip"})
        for tb, col in [("customers", "customer_zip_code_prefix"), ("sellers", "seller_zip_code_prefix")]:
            orows.append({"child": f"{tb}.{col}", "parent": "geolocation.zip_prefix",
                          **orphan(t[tb], col, g, "zip")})
    o, oi, pay, rev = t["orders"], t["order_items"], t["payments"], t["reviews"]
    card = {
        "items_per_order_max": int(oi.groupby("order_id").size().max()),
        "items_per_order_mean": round(oi.groupby("order_id").size().mean(), 3),
        "orders_with_multiple_sellers": int((oi.groupby("order_id")["seller_id"].nunique() > 1).sum()),
        "orders_with_multiple_payments": int((pay.groupby("order_id").size() > 1).sum()),
        "orders_with_multiple_reviews": int((rev.groupby("order_id").size() > 1).sum()),
        "orders_without_items": int((~o["order_id"].isin(set(oi["order_id"]))).sum()),
        "customers_distinct_customer_id": int(t["customers"]["customer_id"].nunique()),
        "customers_distinct_customer_unique_id": int(t["customers"]["customer_unique_id"].nunique()),
        "deals_per_seller_max": int(t["closed_deals"].groupby("seller_id").size().max()),
        "lead_table_columns": list(t["leads"].columns),
        "lead_table_has_sdr_column": bool(any("sdr" in c for c in t["leads"].columns)),
    }
    return pd.DataFrame(krows), pd.DataFrame(orows), card


def funnel(t):
    leads, cd, sellers, oi, o = t["leads"], t["closed_deals"], t["sellers"], t["order_items"], t["orders"]
    delivered = o[o["order_status"] == "delivered"]
    deliv_items = oi.merge(delivered[["order_id", "order_purchase_timestamp"]], on="order_id", how="inner")
    sellers_in_items = set(oi["seller_id"])
    sellers_deliv = set(deliv_items["seller_id"])
    deal_sellers = set(cd["seller_id"].dropna())

    # delivered orders on/after won_date, per deal seller
    cdk = cd[["mql_id", "seller_id", "won_date"]].drop_duplicates()
    m = cdk.merge(deliv_items[["seller_id", "order_id", "order_purchase_timestamp"]], on="seller_id", how="inner")
    post = m[m["order_purchase_timestamp"] >= m["won_date"]]
    sellers_post = set(post["seller_id"])

    attrib_orders = deliv_items[deliv_items["seller_id"].isin(deal_sellers)]
    wf = [
        ("1 all leads (rows)", len(leads)),
        ("1b distinct mql_id in leads", leads["mql_id"].nunique()),
        ("2 closed deals (rows)", len(cd)),
        ("2b distinct mql_id in closed deals", cd["mql_id"].nunique()),
        ("2c closed deals whose mql_id is in leads", int(cd["mql_id"].isin(set(leads["mql_id"])).sum())),
        ("3 distinct closed-deal sellers", len(deal_sellers)),
        ("4 ...present in sellers table", len(deal_sellers & set(sellers["seller_id"]))),
        ("5 ...present in order_items (any order status)", len(deal_sellers & sellers_in_items)),
        ("6 ...with >=1 delivered order", len(deal_sellers & sellers_deliv)),
        ("7 ...with >=1 delivered order on/after won_date", len(sellers_post)),
        ("8 distinct delivered orders from deal sellers", attrib_orders["order_id"].nunique()),
        ("8b item GMV (price) of those delivered orders", round(float(attrib_orders["price"].sum()), 2)),
        ("8c share of all delivered orders touched by deal sellers (%)",
         round(100 * attrib_orders["order_id"].nunique() / delivered["order_id"].nunique(), 2)),
    ]
    # naive fan-out demonstration
    naive = leads.merge(cd[["mql_id", "seller_id"]], on="mql_id", how="left").merge(
        oi[["seller_id", "order_id"]], on="seller_id", how="left")
    wf.append(("FAN-OUT: leads x deals x order_items naive join rows", len(naive)))
    wf_df = pd.DataFrame(wf, columns=["stage", "value"])

    # by origin
    lo = leads[["mql_id", "origin"]].copy()
    lo["origin"] = lo["origin"].fillna("(missing)")
    lo["is_deal"] = lo["mql_id"].isin(set(cd["mql_id"]))
    sel = cd[["mql_id", "seller_id"]].copy()
    sel["in_items"] = sel["seller_id"].isin(sellers_in_items)
    sel["has_delivered"] = sel["seller_id"].isin(sellers_deliv)
    lo = lo.merge(sel, on="mql_id", how="left")
    by_origin = lo.groupby("origin").agg(
        leads=("mql_id", "nunique"), deals=("is_deal", "sum"),
        deal_sellers_in_orders=("in_items", lambda s: int(s.fillna(False).sum())),
        deal_sellers_delivered=("has_delivered", lambda s: int(s.fillna(False).sum()))).reset_index()
    by_origin["lead_to_deal_pct"] = (100 * by_origin["deals"] / by_origin["leads"]).round(2)
    by_origin["deal_to_observed_selling_pct"] = (100 * by_origin["deal_sellers_delivered"] / by_origin["deals"].replace(0, np.nan)).round(2)
    by_origin = by_origin.sort_values("leads", ascending=False)
    return wf_df, by_origin, m, deliv_items


def dates(t, m_deals_orders):
    o, leads, cd = t["orders"], t["leads"], t["closed_deals"]
    rng = []
    for tb, cols in DATE_COLS.items():
        for c in cols:
            s = t[tb][c].dropna()
            rng.append({"table": tb, "column": c, "non_null": len(s),
                        "min": s.min(), "max": s.max()})
    rng = pd.DataFrame(rng)

    def monthly(s, name):
        return s.dropna().dt.to_period("M").value_counts().sort_index().rename(name)
    monthly_df = pd.concat([monthly(leads["first_contact_date"], "leads_first_contact"),
                            monthly(cd["won_date"], "deals_won"),
                            monthly(o["order_purchase_timestamp"], "orders_purchased")], axis=1).fillna(0).astype(int)
    monthly_df.index = monthly_df.index.astype(str)
    monthly_df = monthly_df.reset_index().rename(columns={"index": "month"})

    data_end = o["order_purchase_timestamp"].max()
    cdw = cd[["mql_id", "seller_id", "won_date"]].copy()
    cdw["days_observable_after_won"] = (data_end - cdw["won_date"]).dt.days
    first_order = (t["order_items"].merge(o[["order_id", "order_purchase_timestamp"]], on="order_id")
                   .groupby("seller_id")["order_purchase_timestamp"].min().rename("first_order_any_status"))
    cdw = cdw.merge(first_order, on="seller_id", how="left")
    cdw["linked"] = cdw["first_order_any_status"].notna()
    cdw["gap_days_first_order_minus_won"] = (cdw["first_order_any_status"] - cdw["won_date"]).dt.days
    link = cdw[cdw["linked"]]
    summ = {
        "order_data_last_purchase": str(data_end),
        "deals_total": len(cdw),
        "deals_won_after_last_order": int((cdw["won_date"] > data_end).sum()),
        "deals_with_>=90d_window": int((cdw["days_observable_after_won"] >= 90).sum()),
        "deals_with_>=180d_window": int((cdw["days_observable_after_won"] >= 180).sum()),
        "linked_deals": len(link),
        "linked_deals_first_order_BEFORE_won_date": int((link["gap_days_first_order_minus_won"] < 0).sum()),
        "linked_deals_first_order_on_or_after_won_date": int((link["gap_days_first_order_minus_won"] >= 0).sum()),
        "linked_with_>=90d_window": int((link["days_observable_after_won"] >= 90).sum()),
        "linked_with_>=180d_window": int((link["days_observable_after_won"] >= 180).sum()),
        "gap_days_quantiles": link["gap_days_first_order_minus_won"].quantile([0, .1, .25, .5, .75, .9, 1]).round(1).to_dict(),
    }
    return rng, monthly_df, cdw, summ


def timestamp_sanity(t):
    o = t["orders"]
    p, a, c, d, e = (o["order_purchase_timestamp"], o["order_approved_at"], o["order_delivered_carrier_date"],
                     o["order_delivered_customer_date"], o["order_estimated_delivery_date"])
    status = o["order_status"].value_counts().rename_axis("order_status").reset_index(name="orders")
    deliv = o["order_status"] == "delivered"
    checks = {
        "delivered_orders": int(deliv.sum()),
        "delivered_with_null_customer_date": int((deliv & d.isna()).sum()),
        "delivered_with_null_carrier_date": int((deliv & c.isna()).sum()),
        "delivered_with_null_approved_date": int((deliv & a.isna()).sum()),
        "non_delivered_with_customer_date": int((~deliv & d.notna()).sum()),
        "approved_before_purchase": int((a < p).sum()),
        "carrier_before_purchase": int((c < p).sum()),
        "carrier_before_approved": int((c < a).sum()),
        "customer_before_carrier": int((d < c).sum()),
        "customer_before_purchase": int((d < p).sum()),
        "estimated_before_purchase": int((e < p).sum()),
    }
    rev, oi = t["reviews"], t["order_items"]
    rv = rev.merge(o[["order_id", "order_status", "order_delivered_customer_date"]], on="order_id", how="left")
    checks.update({
        "review_rows": len(rev),
        "review_distinct_orders": int(rev["order_id"].nunique()),
        "orders_with_gt1_review": int((rev.groupby("order_id").size() > 1).sum()),
        "reviews_created_before_delivery": int((rv["review_creation_date"] < rv["order_delivered_customer_date"]).sum()),
        "reviews_on_non_delivered_orders": int((rv["order_status"] != "delivered").sum()),
        "orders_without_any_review": int((~o["order_id"].isin(set(rev["order_id"]))).sum()),
        "review_score_missing": int(rev["review_score"].isna().sum()),
    })
    # payments vs items reconciliation (orders with items and payments)
    items_tot = oi.groupby("order_id").agg(items_total=("price", "sum"), freight_total=("freight_value", "sum"))
    items_tot["expected"] = items_tot["items_total"] + items_tot["freight_total"]
    pay_tot = t["payments"].groupby("order_id")["payment_value"].sum().rename("paid")
    rec = items_tot.join(pay_tot, how="inner")
    checks["orders_with_items_and_payments"] = len(rec)
    checks["payment_matches_items_plus_freight_(abs_diff<=0.01)"] = int(((rec["paid"] - rec["expected"]).abs() <= 0.01).sum())
    checks["payment_match_rate_pct"] = round(100 * checks["payment_matches_items_plus_freight_(abs_diff<=0.01)"] / len(rec), 2)
    checks["items_price_nonpositive"] = int((oi["price"] <= 0).sum())
    checks["items_freight_negative"] = int((oi["freight_value"] < 0).sum())
    cat = t["products"]["product_category_name"]
    trans = set(t["category_translation"]["product_category_name"])
    checks["products_null_category"] = int(cat.isna().sum())
    checks["products_category_without_translation"] = int((cat.notna() & ~cat.isin(trans)).sum())
    return pd.DataFrame(list(checks.items()), columns=["check", "value"]), status


def closed_deal_nulls(t):
    cd = t["closed_deals"]
    return pd.DataFrame({"column": cd.columns, "null_pct": (100 * cd.isna().mean()).round(2).values}).sort_values("null_pct", ascending=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--out", default="outputs/audit")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    t, inv = load_all(a.raw)
    missing = inv[~inv["found"]]["table"].tolist()
    inv.to_csv(out / "01_file_inventory.csv", index=False)
    tsum, prof = profile(t)
    tsum.to_csv(out / "02_table_summary.csv", index=False)
    prof.to_csv(out / "03_column_profile.csv", index=False)
    krows, orows, card = relationship_checks(t)
    krows.to_csv(out / "04_key_uniqueness.csv", index=False)
    orows.to_csv(out / "05_orphan_checks.csv", index=False)
    wf, by_origin, _, _ = funnel(t)
    wf.to_csv(out / "06_funnel_waterfall.csv", index=False)
    by_origin.to_csv(out / "07_funnel_by_origin.csv", index=False)
    rng, monthly_df, cdw, dsum = dates(t, None)
    rng.to_csv(out / "08_date_ranges.csv", index=False)
    monthly_df.to_csv(out / "09_monthly_counts.csv", index=False)
    cdw.to_csv(out / "10_deal_timing.csv", index=False)
    tchecks, status = timestamp_sanity(t)
    tchecks.to_csv(out / "11_timestamp_and_quality_checks.csv", index=False)
    status.to_csv(out / "12_order_status.csv", index=False)
    cdn = closed_deal_nulls(t)
    cdn.to_csv(out / "13_closed_deals_nulls.csv", index=False)

    summary = {"missing_files": missing, "cardinalities": card, "date_summary": dsum}
    (out / "audit_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    md = ["# Phase A audit (auto-generated by src/audit.py)\n"]
    if missing:
        md.append(f"**Files not found / skipped:** {missing}\n")
    for title, df in [("File inventory", inv.drop(columns=["sha256"], errors="ignore")), ("Table summary", tsum),
                      ("Key uniqueness", krows), ("Orphan checks", orows), ("Funnel waterfall (distinct keys)", wf),
                      ("Funnel by origin", by_origin), ("Date ranges", rng),
                      ("Timestamp and quality checks", tchecks), ("Order status", status),
                      ("Closed-deal null rates", cdn)]:
        md.append(f"\n## {title}\n\n{md_table(df)}")
    md.append("\n## Cardinalities\n\n```json\n" + json.dumps(card, indent=2, default=str) + "\n```\n")
    md.append("\n## Date compatibility summary\n\n```json\n" + json.dumps(dsum, indent=2, default=str) + "\n```\n")
    (out / "audit_summary.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
