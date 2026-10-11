-- 01_load_clean.sql
-- raw_* (all TEXT, loaded by run_pipeline.py) -> typed clean_* tables.
-- Raw tables are never altered. Every cleaning rule is logged in out_clean_log.
-- Timestamps stay as 'YYYY-MM-DD HH:MM:SS' text (SQLite date functions work on them).

DROP TABLE IF EXISTS clean_orders;
CREATE TABLE clean_orders AS
SELECT order_id, customer_id, order_status,
       order_purchase_timestamp       AS purchase_ts,
       order_approved_at              AS approved_ts,
       order_delivered_carrier_date   AS carrier_ts,
       order_delivered_customer_date  AS delivered_ts,
       order_estimated_delivery_date  AS estimated_ts
FROM raw_orders;

DROP TABLE IF EXISTS clean_order_items;
CREATE TABLE clean_order_items AS
SELECT order_id, CAST(order_item_id AS INTEGER) AS order_item_id, product_id, seller_id,
       shipping_limit_date, CAST(price AS REAL) AS price, CAST(freight_value AS REAL) AS freight_value
FROM raw_order_items;

-- D-003: one review per order = latest by answer timestamp (tie-break creation date, then review_id)
DROP TABLE IF EXISTS clean_reviews;
CREATE TABLE clean_reviews AS
SELECT order_id, review_id, CAST(review_score AS INTEGER) AS review_score,
       review_creation_date, review_answer_timestamp
FROM (SELECT r.*, ROW_NUMBER() OVER (
              PARTITION BY order_id
              ORDER BY review_answer_timestamp DESC, review_creation_date DESC, review_id DESC) AS rn
      FROM raw_reviews r)
WHERE rn = 1;

DROP TABLE IF EXISTS clean_customers;
CREATE TABLE clean_customers AS
SELECT customer_id, customer_unique_id, customer_state FROM raw_customers;

DROP TABLE IF EXISTS clean_sellers;
CREATE TABLE clean_sellers AS
SELECT seller_id, seller_city, seller_state FROM raw_sellers;

-- D-019 uses the category of item 1; English name where a translation exists
DROP TABLE IF EXISTS clean_products;
CREATE TABLE clean_products AS
SELECT p.product_id,
       COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category_en
FROM raw_products p
LEFT JOIN raw_category_translation t ON t.product_category_name = p.product_category_name;

DROP TABLE IF EXISTS clean_leads;
CREATE TABLE clean_leads AS
SELECT mql_id, first_contact_date, COALESCE(landing_page_id, '(missing)') AS landing_page_id,
       COALESCE(origin, '(missing)') AS origin
FROM raw_leads;

DROP TABLE IF EXISTS clean_closed_deals;
CREATE TABLE clean_closed_deals AS
SELECT mql_id, seller_id, sdr_id, sr_id,
       won_date AS won_ts, date(won_date) AS won_date,
       business_segment, lead_type, lead_behaviour_profile, business_type
FROM raw_closed_deals;

DROP TABLE IF EXISTS out_clean_log;
CREATE TABLE out_clean_log AS
SELECT 'reviews_raw_rows' AS item, COUNT(*) AS value FROM raw_reviews
UNION ALL SELECT 'reviews_clean_rows', COUNT(*) FROM clean_reviews
UNION ALL SELECT 'reviews_dropped_by_dedup', (SELECT COUNT(*) FROM raw_reviews) - (SELECT COUNT(*) FROM clean_reviews)
UNION ALL SELECT 'shipping_limit_outliers_ge_2019', COUNT(*) FROM clean_order_items WHERE shipping_limit_date >= '2019-01-01'
UNION ALL SELECT 'delivered_without_delivery_date', COUNT(*) FROM clean_orders WHERE order_status = 'delivered' AND delivered_ts IS NULL
UNION ALL SELECT 'orders_without_items', COUNT(*) FROM clean_orders WHERE order_id NOT IN (SELECT order_id FROM clean_order_items);
