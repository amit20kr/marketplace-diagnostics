-- 02_star_schema.sql
-- Facts: fact_orders (grain: 1 row per order_id), fact_order_items (order_id + order_item_id),
--        fact_reviews (1 row per order_id, latest review), fact_seller_funnel (1 row per lead / mql_id).
-- Dims:  dim_seller (seller_id), dim_customer (customer_id), dim_product (product_id), dim_date (date).
-- params holds the analysis window (D-011) and the effective data end (D-013).
-- Money is summed at item grain, never over a joined fan-out (see out_funnel_waterfall NAIVE row).

DROP TABLE IF EXISTS params;
CREATE TABLE params AS
SELECT '2017-01-01' AS window_start, '2018-09-01' AS window_end_excl, '2018-08-31' AS data_end_effective;

DROP TABLE IF EXISTS dim_customer;
CREATE TABLE dim_customer AS SELECT customer_id, customer_unique_id, customer_state FROM clean_customers;

-- D-008: is_deal_seller = seller appears in closed_deals. Sellers come from the sellers table (order sample).
DROP TABLE IF EXISTS dim_seller;
CREATE TABLE dim_seller AS
SELECT s.seller_id, s.seller_state, s.seller_city,
       CASE WHEN d.seller_id IS NOT NULL THEN 1 ELSE 0 END AS is_deal_seller,
       d.mql_id, d.won_ts, d.business_segment, l.origin
FROM clean_sellers s
LEFT JOIN clean_closed_deals d ON d.seller_id = s.seller_id
LEFT JOIN clean_leads l ON l.mql_id = d.mql_id;

DROP TABLE IF EXISTS dim_product;
CREATE TABLE dim_product AS SELECT product_id, category_en FROM clean_products;

DROP TABLE IF EXISTS dim_date;
CREATE TABLE dim_date AS
WITH RECURSIVE d(dt) AS (SELECT '2017-01-01' UNION ALL SELECT date(dt, '+1 day') FROM d WHERE dt < '2018-08-31')
SELECT dt AS date, substr(dt, 1, 7) AS month, CAST(strftime('%Y', dt) AS INTEGER) AS year,
       CAST(strftime('%w', dt) AS INTEGER) AS dow
FROM d;

-- D-005: shipping_limit_date >= 2019-01-01 is an outlier (4 items in the real data)
DROP TABLE IF EXISTS fact_order_items;
CREATE TABLE fact_order_items AS
SELECT order_id, order_item_id, product_id, seller_id, shipping_limit_date,
       CASE WHEN shipping_limit_date >= '2019-01-01' THEN 1 ELSE 0 END AS shipping_limit_outlier,
       price, freight_value
FROM clean_order_items;

DROP TABLE IF EXISTS fact_reviews;
CREATE TABLE fact_reviews AS
SELECT order_id, review_id, review_score, date(review_creation_date) AS review_created_date,
       review_answer_timestamp
FROM clean_reviews;

DROP TABLE IF EXISTS tmp_order_agg;
CREATE TABLE tmp_order_agg AS
SELECT order_id,
       COUNT(*) AS n_items,
       COUNT(DISTINCT seller_id) AS n_sellers,
       CASE WHEN COUNT(DISTINCT seller_id) = 1 THEN MIN(seller_id) END AS single_seller_id,  -- D-018
       SUM(price) AS item_value,
       SUM(freight_value) AS freight_value,
       MIN(CASE WHEN shipping_limit_outlier = 0 THEN shipping_limit_date END) AS min_shipping_limit,  -- D-020
       MIN(CASE WHEN order_item_id = 1 THEN product_id END) AS primary_product_id                    -- D-019
FROM fact_order_items
GROUP BY order_id;

DROP TABLE IF EXISTS tmp_orders_base;
CREATE TABLE tmp_orders_base AS
SELECT o.order_id, o.customer_id, o.order_status, o.purchase_ts, o.carrier_ts, o.delivered_ts, o.estimated_ts,
       CASE WHEN o.purchase_ts >= p.window_start AND o.purchase_ts < p.window_end_excl THEN 1 ELSE 0 END AS in_window,
       CASE WHEN o.order_status = 'delivered' AND o.delivered_ts IS NOT NULL THEN 1 ELSE 0 END AS delivered_valid  -- D-002
FROM clean_orders o CROSS JOIN params p;

-- Lateness is date-level (D-012): delivered DATE vs estimated DATE. late_ts is the timestamp-level robustness flag.
-- Stage times only for stage-valid orders (D-004): purchase <= carrier handoff <= delivered.
DROP TABLE IF EXISTS fact_orders;
CREATE TABLE fact_orders AS
SELECT b.order_id, b.customer_id, b.order_status, b.purchase_ts, substr(b.purchase_ts, 1, 7) AS purchase_month,
       b.carrier_ts, b.delivered_ts, date(b.estimated_ts) AS est_date,
       b.in_window, b.delivered_valid,
       CASE WHEN b.delivered_valid = 1 THEN julianday(date(b.delivered_ts)) - julianday(date(b.estimated_ts)) END AS delay_days,
       CASE WHEN b.delivered_valid = 1 THEN
            CASE WHEN julianday(date(b.delivered_ts)) - julianday(date(b.estimated_ts)) > 0 THEN 1 ELSE 0 END END AS is_late,
       CASE WHEN b.delivered_valid = 1 THEN
            CASE WHEN b.delivered_ts > b.estimated_ts THEN 1 ELSE 0 END END AS late_ts,
       CASE WHEN b.delivered_valid = 1 THEN
            CASE WHEN julianday(date(b.delivered_ts)) - julianday(date(b.estimated_ts)) <= 0 THEN 'on_time'
                 WHEN julianday(date(b.delivered_ts)) - julianday(date(b.estimated_ts)) <= 3 THEN '1-3'
                 WHEN julianday(date(b.delivered_ts)) - julianday(date(b.estimated_ts)) <= 7 THEN '4-7'
                 ELSE '8+' END END AS delay_band,
       CASE WHEN b.delivered_valid = 1 AND b.carrier_ts IS NOT NULL AND b.purchase_ts <= b.carrier_ts
                 AND b.carrier_ts <= b.delivered_ts THEN 1 ELSE 0 END AS stage_valid,
       CASE WHEN b.delivered_valid = 1 AND b.carrier_ts IS NOT NULL AND b.purchase_ts <= b.carrier_ts
                 AND b.carrier_ts <= b.delivered_ts THEN julianday(b.carrier_ts) - julianday(b.purchase_ts) END AS dispatch_days,
       CASE WHEN b.delivered_valid = 1 AND b.carrier_ts IS NOT NULL AND b.purchase_ts <= b.carrier_ts
                 AND b.carrier_ts <= b.delivered_ts THEN julianday(b.delivered_ts) - julianday(b.carrier_ts) END AS transit_days,
       julianday(date(b.estimated_ts)) - julianday(date(b.purchase_ts)) AS promised_days,
       a.n_items, a.n_sellers, a.single_seller_id AS seller_id, a.item_value, a.freight_value,
       CASE WHEN a.item_value > 0 THEN a.freight_value / a.item_value END AS freight_ratio,
       CASE WHEN b.delivered_valid = 1 AND a.n_sellers = 1 AND b.carrier_ts IS NOT NULL
                 AND a.min_shipping_limit IS NOT NULL THEN
            CASE WHEN date(b.carrier_ts) <= date(a.min_shipping_limit) THEN 1 ELSE 0 END END AS dispatch_compliant,  -- D-020
       c.customer_state, s.seller_state, COALESCE(pr.category_en, 'unknown') AS category,
       r.review_score,
       CASE WHEN b.delivered_valid = 1 AND r.review_score IS NOT NULL THEN
            CASE WHEN r.review_created_date < date(b.delivered_ts) THEN 1 ELSE 0 END END AS review_pre_delivery  -- D-021
FROM tmp_orders_base b
LEFT JOIN tmp_order_agg a ON a.order_id = b.order_id
LEFT JOIN dim_customer c ON c.customer_id = b.customer_id
LEFT JOIN dim_seller s ON s.seller_id = a.single_seller_id
LEFT JOIN dim_product pr ON pr.product_id = a.primary_product_id
LEFT JOIN fact_reviews r ON r.order_id = b.order_id;

DROP TABLE IF EXISTS tmp_seller_first;
CREATE TABLE tmp_seller_first AS
SELECT i.seller_id, MIN(o.purchase_ts) AS first_sale_ts
FROM fact_order_items i JOIN fact_orders o ON o.order_id = i.order_id
WHERE o.delivered_valid = 1
GROUP BY i.seller_id;

-- One row per lead. matured_90: deal won at least 90 days before the effective data end (D-007).
-- first_sale_90: first delivered order from the deal seller on/after won_ts and within 90 days of it.
DROP TABLE IF EXISTS fact_seller_funnel;
CREATE TABLE fact_seller_funnel AS
SELECT l.mql_id, l.first_contact_date, substr(l.first_contact_date, 1, 7) AS contact_month,
       l.landing_page_id, l.origin,
       CASE WHEN d.mql_id IS NOT NULL THEN 1 ELSE 0 END AS is_deal,
       d.seller_id, d.won_ts, d.won_date, d.sdr_id, d.business_segment, d.lead_type,
       CASE WHEN d.mql_id IS NOT NULL THEN julianday(d.won_date) - julianday(l.first_contact_date) END AS days_to_close,
       CASE WHEN d.seller_id IN (SELECT seller_id FROM fact_order_items) THEN 1 ELSE 0 END AS seller_in_orders,
       f.first_sale_ts,
       CASE WHEN d.mql_id IS NOT NULL AND julianday(p.data_end_effective) - julianday(d.won_date) >= 90 THEN 1 ELSE 0 END AS matured_90,
       CASE WHEN d.mql_id IS NOT NULL AND f.first_sale_ts IS NOT NULL AND f.first_sale_ts >= d.won_ts
                 AND julianday(f.first_sale_ts) - julianday(d.won_ts) <= 90 THEN 1 ELSE 0 END AS first_sale_90
FROM clean_leads l
LEFT JOIN clean_closed_deals d ON d.mql_id = l.mql_id
LEFT JOIN tmp_seller_first f ON f.seller_id = d.seller_id
CROSS JOIN params p;

CREATE INDEX IF NOT EXISTS ix_fo_order ON fact_orders(order_id);
CREATE INDEX IF NOT EXISTS ix_fo_seller ON fact_orders(seller_id);
CREATE INDEX IF NOT EXISTS ix_foi_seller ON fact_order_items(seller_id);
CREATE INDEX IF NOT EXISTS ix_foi_order ON fact_order_items(order_id);
