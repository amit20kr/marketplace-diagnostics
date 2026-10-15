# Phase A Audit Notes (curated)

Source: `src/audit.py`, run by Claude on copies of 10 of the 11 CSVs. **`olist_geolocation_dataset.csv` could not be copied (too large) and is NOT yet audited.** Antigravity must re-run `python src/audit.py --raw data/raw --out outputs/audit` on the real folder to regenerate all CSVs (including geolocation, SHA-256 hashes) and confirm these numbers.

## 1. Table sizes (match public figures)
| Table | Rows | Cols |
|---|---|---|
| customers | 99,441 | 5 |
| orders | 99,441 | 8 |
| order_items | 112,650 | 7 |
| payments | 103,886 | 5 |
| reviews | 99,224 | 7 |
| products | 32,951 | 9 |
| sellers | 3,095 | 4 |
| category_translation | 71 | 2 |
| leads (MQLs) | 8,000 | 4 (`mql_id`, `first_contact_date`, `landing_page_id`, `origin`) |
| closed_deals | 842 | 14 |
| geolocation | not audited | |

No full-duplicate rows in any audited table.

## 2. Keys and relationships
- Unique: orders.order_id, customers.customer_id, sellers.seller_id, products.product_id, leads.mql_id, closed_deals.mql_id, closed_deals.seller_id (one deal per seller), (order_id, order_item_id), (order_id, payment_sequential).
- **Not unique:** reviews.review_id (814 duplicate rows) and reviews.order_id (551 duplicate rows; 547 orders have >1 review). 98,673 distinct orders have reviews; 768 orders have none.
- Orphans: 0 for order_items->orders/products/sellers, orders->customers, payments->orders, reviews->orders, closed_deals->leads.
- **closed_deals.seller_id -> sellers: 462 of 842 (54.9%) are not in the sellers table.** All 3,095 sellers have >=1 order_items row (the seller table only lists sellers present in the order sample).
- 775 orders (0.78%) have no order_items (mostly non-delivered statuses).
- customer_id is per order (99,441); customer_unique_id = 96,096 distinct people.
- 1,278 orders have items from more than one seller; 2,961 orders have multiple payment rows; max 21 items per order (mean 1.14).
- The lead table has **no SDR column** -> SDR-level lead conversion is not computable. closed_deals has 32 distinct sdr_id and 22 sr_id; median 7 deals per SDR (max 140), so most SDRs have few deals.
- closed_deals: 33 business_segment values, 8 lead_type values.

## 3. Funnel join-coverage waterfall (distinct keys)
| Stage | Count |
|---|---|
| All leads | 8,000 |
| Closed deals (distinct mql_id = distinct seller_id) | 842 (10.5% of leads) |
| ...seller present in `sellers` and in `order_items` | 380 (45.1% of deals) |
| ...with >= 1 delivered order | 376 |
| ...with >= 1 delivered order on/after won_date | 376 |
| Distinct delivered orders from those sellers | 4,457 (4.62% of all delivered orders) |
| Item GMV (price only) of those orders | about R$664.9k |
| **Naive leads x deals x order_items join** | **12,664 rows (fan-out vs 8,000 leads)** |

By origin (n = leads; deals; deal sellers with a delivered order):
| origin | leads | deals | lead->deal % | deal sellers with delivered order | % of deals |
|---|---|---|---|---|---|
| organic_search | 2,296 | 271 | 11.80 | 111 | 40.96 |
| paid_search | 1,586 | 195 | 12.30 | 100 | 51.28 |
| social | 1,350 | 75 | 5.56 | 31 | 41.33 |
| unknown | 1,099 | 179 | 16.29 | 80 | 44.69 |
| direct_traffic | 499 | 56 | 11.22 | 31 | 55.36 |
| email | 493 | 15 | 3.04 | 6 | 40.00 |
| referral | 284 | 24 | 8.45 | 9 | 37.50 |
| other | 150 | 4 | 2.67 | 2 | 50.00 |
| display | 118 | 6 | 5.08 | 2 | 33.33 |
| other_publicities | 65 | 3 | 4.62 | 0 | 0.00 |
| (missing) | 60 | 14 | 23.33 | 4 | 28.57 |

Counts below about 30 are not interpretable. These are descriptive; no significance has been tested.

## 4. Dates
| Column | Min | Max |
|---|---|---|
| orders.order_purchase_timestamp | 2016-09-04 | 2018-10-17 |
| orders.order_delivered_customer_date | 2016-10-11 | 2018-10-17 |
| orders.order_estimated_delivery_date | 2016-09-30 | 2018-11-12 |
| reviews.review_creation_date | 2016-10-02 | 2018-08-31 |
| leads.first_contact_date | 2017-06-14 | 2018-05-31 |
| closed_deals.won_date | 2017-12-05 | 2018-11-14 |
| order_items.shipping_limit_date | 2016-09-19 | **2020-04-09 (outlier)** |

- 17 of 842 deals were won after the last order in the data (2018-10-17).
- Deals with >= 90 days of order data after won_date: 746; >= 180 days: 460. Among the 380 linked deals: 372 and 238.
- **0 of 380 linked sellers have a first order before won_date.** Gap from won_date to first order: min 3, median 44, p90 about 102, max 220 days. (This removes the pre-existing-seller worry for linked sellers; it does not tell us why 462 deal sellers are absent.)
- Lead first contact ends 2018-05-31, while orders run to 2018-10, so leads contacted late may not have had time to close: use matured cohorts only.

## 5. Timestamp and quality checks
- Order status: delivered 96,478; shipped 1,107; canceled 625; unavailable 609; invoiced 314; processing 301; created 5; approved 2.
- Delivered orders with null customer delivery date: 8 (exclude from delivery KPIs); with null carrier date: 2; null approved date: 14. Non-delivered orders with a customer delivery date: 6.
- carrier date before purchase: 166; carrier before approval: 1,359; customer delivery before carrier date: 23. No approval-before-purchase or estimate-before-purchase cases.
- Reviews created before the delivery date: 8,320 (reviews on non-delivered orders: 2,863).
- Payment total equals items price + freight (within 0.01) for 98,284 of 98,665 orders (99.61%).
- Price <= 0 or freight < 0: none. Products with null category: 610; categories missing from translation: 2 distinct values (`pc_gamer`, `portateis_cozinha_e_preparadores_de_alimentos`), 13 product rows.
- closed_deals null rates: has_company 92.5%, has_gtin 92.4%, average_stock 92.2%, declared_product_catalog_size 91.8%, lead_behaviour_profile 21.0%, business_type 1.2%, lead_type 0.7%, business_segment 0.1%. The four sparse columns are unusable for analysis.

## 6. Ad hoc sanity signals (NOT analysis results; to be formally tested in Phase B)
> **SUPERSEDED (D-011, D-012, F-000):** The ad hoc figures below are superseded by the pipeline SQL and statistics results (in-window late rate 6.79%, reviews 2.27 vs 4.29, 1-star 53.8% vs 6.6%; see docs/decision_log.md F-000 and docs/07_PROGRESS_REPORT.md).

Using the latest review per delivered order: late orders (delivered after the estimated date) were about 8.1% of delivered orders with a delivery date; average review about 2.6 for late vs 4.3 for on-time orders; share of 1-star reviews about 46% vs 7%. About 66% of reviews written before the delivery date belong to late orders. These numbers only indicate H1 is plausible. Phase B must reproduce them in SQL with definitions, CIs, effect sizes and confounder checks.

## 7. Public-figure verification
| Public claim | Result |
|---|---|
| 99,441 orders; 112,650 items; 103,886 payments; 99,224 reviews; 3,095 sellers; 32,951 products | CONFIRMED |
| 8,000 leads; 842 deals | CONFIRMED |
| About 380 deal sellers appear in order data | CONFIRMED (380; 376 with a delivered order) |
| Orders 2016-09 to 2018-10; deals won 2017-12 to 2018-11 | CONFIRMED (deals can extend past last order) |
| Naive join fan-out 8,000 -> 12,664 | CONFIRMED |
| Seller table only contains sellers with orders | CONFIRMED (all 3,095 have >= 1 item row) |
| Geolocation about 1,000,163 rows | NOT VERIFIED (file not audited) |
