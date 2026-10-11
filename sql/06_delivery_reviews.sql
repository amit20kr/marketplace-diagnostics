-- 06_delivery_reviews.sql: delivery diagnostics + review tables. Window orders, delivered-valid, date-level lateness.

DROP TABLE IF EXISTS out_delay_stage_monthly;
CREATE TABLE out_delay_stage_monthly AS
SELECT purchase_month AS month, COUNT(*) AS stage_valid_orders,
       ROUND(AVG(dispatch_days), 4) AS avg_dispatch_days, ROUND(AVG(transit_days), 4) AS avg_transit_days,
       ROUND(AVG(promised_days), 4) AS avg_promised_days, ROUND(AVG(delay_days), 4) AS avg_delay_days
FROM fact_orders WHERE in_window = 1 AND delivered_valid = 1 AND stage_valid = 1
GROUP BY purchase_month ORDER BY purchase_month;

DROP TABLE IF EXISTS out_late_month_state;
CREATE TABLE out_late_month_state AS
SELECT purchase_month AS month, customer_state, COUNT(*) AS orders, SUM(is_late) AS late_orders
FROM fact_orders WHERE in_window = 1 AND delivered_valid = 1
GROUP BY purchase_month, customer_state;

DROP TABLE IF EXISTS out_late_state;
CREATE TABLE out_late_state AS
SELECT customer_state, COUNT(*) AS orders, SUM(is_late) AS late_orders,
       ROUND(1.0 * SUM(is_late) / COUNT(*), 6) AS late_rate, ROUND(AVG(review_score), 4) AS avg_review
FROM fact_orders WHERE in_window = 1 AND delivered_valid = 1
GROUP BY customer_state ORDER BY late_orders DESC;

-- lanes = seller state -> customer state (single-seller orders only, D-018)
DROP TABLE IF EXISTS out_late_lane;
CREATE TABLE out_late_lane AS
SELECT seller_state, customer_state, COUNT(*) AS orders, SUM(is_late) AS late_orders,
       ROUND(1.0 * SUM(is_late) / COUNT(*), 6) AS late_rate
FROM fact_orders WHERE in_window = 1 AND delivered_valid = 1 AND seller_id IS NOT NULL
GROUP BY seller_state, customer_state ORDER BY late_orders DESC;

DROP TABLE IF EXISTS out_late_category;
CREATE TABLE out_late_category AS
SELECT category, COUNT(*) AS orders, SUM(is_late) AS late_orders,
       ROUND(1.0 * SUM(is_late) / COUNT(*), 6) AS late_rate, ROUND(AVG(review_score), 4) AS avg_review
FROM fact_orders WHERE in_window = 1 AND delivered_valid = 1
GROUP BY category ORDER BY orders DESC;

DROP TABLE IF EXISTS out_review_band;
CREATE TABLE out_review_band AS
SELECT delay_band, COUNT(review_score) AS reviewed, ROUND(AVG(review_score), 4) AS avg_review,
       SUM(CASE WHEN review_score = 1 THEN 1 ELSE 0 END) AS one_star_n,
       ROUND(1.0 * SUM(CASE WHEN review_score = 1 THEN 1 ELSE 0 END) / COUNT(review_score), 6) AS one_star_share
FROM fact_orders WHERE in_window = 1 AND delivered_valid = 1 AND review_score IS NOT NULL
GROUP BY delay_band;

-- survey-timing split (L-009): reviews written before vs on/after the delivery date
DROP TABLE IF EXISTS out_review_timing;
CREATE TABLE out_review_timing AS
SELECT is_late, review_pre_delivery, COUNT(*) AS reviewed, ROUND(AVG(review_score), 4) AS avg_review,
       SUM(CASE WHEN review_score = 1 THEN 1 ELSE 0 END) AS one_star_n,
       ROUND(1.0 * SUM(CASE WHEN review_score = 1 THEN 1 ELSE 0 END) / COUNT(*), 6) AS one_star_share
FROM fact_orders WHERE in_window = 1 AND delivered_valid = 1 AND review_score IS NOT NULL
GROUP BY is_late, review_pre_delivery;

DROP TABLE IF EXISTS out_dispatch_compliance;
CREATE TABLE out_dispatch_compliance AS
SELECT dispatch_compliant, COUNT(*) AS orders, SUM(is_late) AS late_orders,
       ROUND(1.0 * SUM(is_late) / COUNT(*), 6) AS late_rate
FROM fact_orders WHERE in_window = 1 AND delivered_valid = 1 AND dispatch_compliant IS NOT NULL
GROUP BY dispatch_compliant;

DROP TABLE IF EXISTS out_freight_band;
CREATE TABLE out_freight_band AS
SELECT CASE WHEN freight_ratio < 0.10 THEN 'a <0.10' WHEN freight_ratio < 0.20 THEN 'b 0.10-0.20'
            WHEN freight_ratio < 0.40 THEN 'c 0.20-0.40' ELSE 'd >=0.40' END AS freight_to_price_band,
       COUNT(*) AS orders, SUM(is_late) AS late_orders, ROUND(1.0 * SUM(is_late) / COUNT(*), 6) AS late_rate,
       ROUND(AVG(review_score), 4) AS avg_review
FROM fact_orders WHERE in_window = 1 AND delivered_valid = 1 AND freight_ratio IS NOT NULL
GROUP BY 1 ORDER BY 1;

DROP TABLE IF EXISTS out_price_band;
CREATE TABLE out_price_band AS
SELECT CASE WHEN item_value < 50 THEN 'a <50' WHEN item_value < 100 THEN 'b 50-100'
            WHEN item_value < 200 THEN 'c 100-200' ELSE 'd >=200' END AS price_band,
       COUNT(*) AS orders, SUM(is_late) AS late_orders, ROUND(1.0 * SUM(is_late) / COUNT(*), 6) AS late_rate,
       ROUND(AVG(review_score), 4) AS avg_review
FROM fact_orders WHERE in_window = 1 AND delivered_valid = 1 AND item_value IS NOT NULL
GROUP BY 1 ORDER BY 1;

-- D-012 sensitivity: date-level vs timestamp-level lateness
DROP TABLE IF EXISTS out_late_sensitivity;
CREATE TABLE out_late_sensitivity AS
SELECT 'date_level' AS definition, COUNT(*) AS orders, SUM(is_late) AS late_orders,
       ROUND(1.0 * SUM(is_late) / COUNT(*), 6) AS late_rate
FROM fact_orders WHERE in_window = 1 AND delivered_valid = 1
UNION ALL
SELECT 'timestamp_level', COUNT(*), SUM(late_ts), ROUND(1.0 * SUM(late_ts) / COUNT(*), 6)
FROM fact_orders WHERE in_window = 1 AND delivered_valid = 1;

-- slim order-level file for the Streamlit app (delivered-valid, in window)
DROP TABLE IF EXISTS out_app_orders;
CREATE TABLE out_app_orders AS
SELECT order_id, purchase_month, customer_state, seller_id, seller_state, category, n_sellers,
       delay_days, is_late, delay_band, dispatch_days, transit_days, promised_days, stage_valid,
       dispatch_compliant, review_score, review_pre_delivery,
       ROUND(item_value, 2) AS item_value, ROUND(freight_value, 2) AS freight_value, ROUND(freight_ratio, 4) AS freight_ratio
FROM fact_orders WHERE in_window = 1 AND delivered_valid = 1;
