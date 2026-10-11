-- 04_funnel.sql: acquisition funnel. All counts are DISTINCT keys at the stated grain (never joined rows).
-- Funnel scope is NOT windowed (deal sellers' delivered-valid orders over the whole file) -- see the NAIVE row.

DROP TABLE IF EXISTS out_funnel_waterfall;
CREATE TABLE out_funnel_waterfall AS
SELECT 1 AS ord, 'all_leads' AS stage, COUNT(DISTINCT mql_id) AS value FROM clean_leads
UNION ALL SELECT 2, 'closed_deals', COUNT(DISTINCT mql_id) FROM clean_closed_deals
UNION ALL SELECT 3, 'deal_sellers_in_sellers_table', COUNT(DISTINCT d.seller_id)
  FROM clean_closed_deals d JOIN clean_sellers s ON s.seller_id = d.seller_id
UNION ALL SELECT 4, 'deal_sellers_in_order_items', COUNT(DISTINCT d.seller_id)
  FROM clean_closed_deals d JOIN fact_order_items i ON i.seller_id = d.seller_id
UNION ALL SELECT 5, 'deal_sellers_with_delivered_order', COUNT(DISTINCT d.seller_id)
  FROM clean_closed_deals d JOIN fact_order_items i ON i.seller_id = d.seller_id
  JOIN fact_orders o ON o.order_id = i.order_id AND o.delivered_valid = 1
UNION ALL SELECT 6, 'deals_matured_90d', SUM(matured_90) FROM fact_seller_funnel
UNION ALL SELECT 7, 'matured_deals_first_sale_within_90d', SUM(CASE WHEN matured_90 = 1 AND first_sale_90 = 1 THEN 1 ELSE 0 END)
  FROM fact_seller_funnel
UNION ALL SELECT 8, 'delivered_orders_from_deal_sellers', COUNT(DISTINCT i.order_id)
  FROM fact_order_items i JOIN clean_closed_deals d ON d.seller_id = i.seller_id
  JOIN fact_orders o ON o.order_id = i.order_id AND o.delivered_valid = 1
UNION ALL SELECT 9, 'item_gmv_deal_sellers', ROUND(SUM(i.price), 2)
  FROM fact_order_items i JOIN clean_closed_deals d ON d.seller_id = i.seller_id
  JOIN fact_orders o ON o.order_id = i.order_id AND o.delivered_valid = 1
UNION ALL SELECT 10, 'delivered_orders_all', COUNT(*) FROM fact_orders WHERE delivered_valid = 1
UNION ALL SELECT 11, 'NAIVE_join_rows_leads_x_deals_x_items', COUNT(*)
  FROM clean_leads l LEFT JOIN clean_closed_deals d ON d.mql_id = l.mql_id
  LEFT JOIN fact_order_items i ON i.seller_id = d.seller_id;

DROP TABLE IF EXISTS out_funnel_origin;
CREATE TABLE out_funnel_origin AS
SELECT origin, COUNT(*) AS leads, SUM(is_deal) AS deals, SUM(seller_in_orders) AS deal_sellers_in_orders,
       SUM(matured_90) AS matured_deals, SUM(CASE WHEN matured_90 = 1 THEN first_sale_90 ELSE 0 END) AS first_sale_90_n
FROM fact_seller_funnel GROUP BY origin ORDER BY leads DESC;

DROP TABLE IF EXISTS out_funnel_landing;
CREATE TABLE out_funnel_landing AS
SELECT landing_page_id, COUNT(*) AS leads, SUM(is_deal) AS deals
FROM fact_seller_funnel GROUP BY landing_page_id ORDER BY leads DESC;

DROP TABLE IF EXISTS out_funnel_month;
CREATE TABLE out_funnel_month AS
SELECT contact_month, COUNT(*) AS leads, SUM(is_deal) AS deals
FROM fact_seller_funnel GROUP BY contact_month ORDER BY contact_month;

-- L-008: segment / lead_type / SDR exist only for closed deals -> downstream view only, not conversion
DROP TABLE IF EXISTS out_funnel_segment;
CREATE TABLE out_funnel_segment AS
SELECT COALESCE(business_segment, '(missing)') AS business_segment, COUNT(*) AS deals,
       SUM(seller_in_orders) AS deal_sellers_in_orders, SUM(matured_90) AS matured_deals,
       SUM(CASE WHEN matured_90 = 1 THEN first_sale_90 ELSE 0 END) AS first_sale_90_n
FROM fact_seller_funnel WHERE is_deal = 1 GROUP BY 1 ORDER BY deals DESC;

DROP TABLE IF EXISTS out_funnel_leadtype;
CREATE TABLE out_funnel_leadtype AS
SELECT COALESCE(lead_type, '(missing)') AS lead_type, COUNT(*) AS deals, SUM(matured_90) AS matured_deals,
       SUM(CASE WHEN matured_90 = 1 THEN first_sale_90 ELSE 0 END) AS first_sale_90_n
FROM fact_seller_funnel WHERE is_deal = 1 GROUP BY 1 ORDER BY deals DESC;

DROP TABLE IF EXISTS out_app_funnel;
CREATE TABLE out_app_funnel AS SELECT * FROM fact_seller_funnel;
