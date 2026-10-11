-- 03_kpis.sql: headline KPI tables (window 2017-01..2018-08, delivered-valid orders unless stated)

DROP TABLE IF EXISTS out_kpi_monthly;
CREATE TABLE out_kpi_monthly AS
SELECT purchase_month AS month,
       COUNT(*) AS orders_delivered,
       SUM(is_late) AS late_orders,
       ROUND(1.0 * SUM(is_late) / COUNT(*), 6) AS late_rate,
       COUNT(review_score) AS orders_reviewed,
       ROUND(AVG(review_score), 4) AS avg_review,
       ROUND(1.0 * SUM(CASE WHEN review_score = 1 THEN 1 ELSE 0 END) / COUNT(review_score), 6) AS one_star_share,
       ROUND(AVG(dispatch_days), 4) AS avg_dispatch_days,
       ROUND(AVG(transit_days), 4) AS avg_transit_days,
       ROUND(AVG(promised_days), 4) AS avg_promised_days,
       ROUND(SUM(item_value), 2) AS gmv_items,
       ROUND(SUM(item_value) / COUNT(*), 4) AS aov
FROM fact_orders
WHERE in_window = 1 AND delivered_valid = 1
GROUP BY purchase_month
ORDER BY purchase_month;

DROP TABLE IF EXISTS out_kpi_overall;
CREATE TABLE out_kpi_overall AS
SELECT (SELECT COUNT(*) FROM fact_orders WHERE in_window = 1) AS orders_in_window,
       COUNT(*) AS delivered_valid_orders,
       SUM(is_late) AS late_orders,
       ROUND(1.0 * SUM(is_late) / COUNT(*), 6) AS late_rate,
       ROUND(1.0 * SUM(late_ts) / COUNT(*), 6) AS late_rate_timestamp_level,
       COUNT(review_score) AS orders_reviewed,
       ROUND(AVG(review_score), 4) AS avg_review,
       ROUND(1.0 * SUM(CASE WHEN review_score = 1 THEN 1 ELSE 0 END) / COUNT(review_score), 6) AS one_star_share,
       ROUND(AVG(dispatch_days), 4) AS avg_dispatch_days,
       ROUND(AVG(transit_days), 4) AS avg_transit_days,
       ROUND(1.0 * SUM(dispatch_compliant) / COUNT(dispatch_compliant), 6) AS dispatch_compliance,
       SUM(CASE WHEN n_sellers = 1 THEN 1 ELSE 0 END) AS single_seller_orders,
       SUM(CASE WHEN n_sellers > 1 THEN 1 ELSE 0 END) AS multi_seller_orders,
       ROUND(SUM(item_value), 2) AS gmv_items,
       ROUND(SUM(item_value) / COUNT(*), 4) AS aov,
       ROUND(SUM(freight_value) / SUM(item_value), 6) AS freight_to_item_value
FROM fact_orders
WHERE in_window = 1 AND delivered_valid = 1;

-- D-018: seller KPIs use single-seller delivered-valid orders only
DROP TABLE IF EXISTS out_kpi_seller;
CREATE TABLE out_kpi_seller AS
SELECT o.seller_id, s.seller_state, s.is_deal_seller,
       COUNT(*) AS orders,
       SUM(o.is_late) AS late_orders,
       ROUND(1.0 * SUM(1 - o.is_late) / COUNT(*), 6) AS on_time_rate,
       ROUND(AVG(o.dispatch_days), 4) AS avg_dispatch_days,
       COUNT(o.review_score) AS orders_reviewed,
       ROUND(AVG(o.review_score), 4) AS avg_review,
       ROUND(SUM(o.item_value), 2) AS gmv_items,
       COUNT(o.dispatch_compliant) AS compliance_orders,
       SUM(o.dispatch_compliant) AS compliant_orders,
       MIN(o.purchase_month) AS first_month, MAX(o.purchase_month) AS last_month
FROM fact_orders o JOIN dim_seller s ON s.seller_id = o.seller_id
WHERE o.in_window = 1 AND o.delivered_valid = 1 AND o.seller_id IS NOT NULL
GROUP BY o.seller_id, s.seller_state, s.is_deal_seller;
