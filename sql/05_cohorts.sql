-- 05_cohorts.sql: seller retention cohorts.
-- Cohort = month of a seller's first delivered order in the window (observed first sale, D-025, L-010).
-- Retention at k = seller has >= 1 delivered order in month (cohort + k). Cells beyond the data end are flagged observable = 0.
-- Group: acquired = seller in closed_deals; non_funnel = all other sellers (D-008).

DROP TABLE IF EXISTS tmp_seller_month;
CREATE TABLE tmp_seller_month AS
SELECT DISTINCT i.seller_id, o.purchase_month AS month,
       CAST(substr(o.purchase_month, 1, 4) AS INTEGER) * 12 + CAST(substr(o.purchase_month, 6, 2) AS INTEGER) AS mi
FROM fact_order_items i
JOIN fact_orders o ON o.order_id = i.order_id
WHERE o.in_window = 1 AND o.delivered_valid = 1 AND i.seller_id IS NOT NULL;

DROP TABLE IF EXISTS tmp_cohort;
CREATE TABLE tmp_cohort AS
SELECT m.seller_id, MIN(m.month) AS cohort_month, MIN(m.mi) AS cohort_mi, s.is_deal_seller
FROM tmp_seller_month m JOIN dim_seller s ON s.seller_id = m.seller_id
GROUP BY m.seller_id, s.is_deal_seller;

DROP TABLE IF EXISTS out_cohort_retention;
CREATE TABLE out_cohort_retention AS
WITH RECURSIVE ks(k) AS (SELECT 0 UNION ALL SELECT k + 1 FROM ks WHERE k < 19),
sizes AS (SELECT cohort_month, cohort_mi, is_deal_seller, COUNT(*) AS cohort_size
          FROM tmp_cohort GROUP BY cohort_month, cohort_mi, is_deal_seller),
act AS (SELECT c.cohort_month, c.is_deal_seller, m.mi - c.cohort_mi AS k, COUNT(DISTINCT m.seller_id) AS active_n
        FROM tmp_cohort c JOIN tmp_seller_month m ON m.seller_id = c.seller_id
        GROUP BY c.cohort_month, c.is_deal_seller, m.mi - c.cohort_mi),
endm AS (SELECT CAST(substr(data_end_effective, 1, 4) AS INTEGER) * 12 + CAST(substr(data_end_effective, 6, 2) AS INTEGER) AS end_mi
         FROM params)
SELECT s.cohort_month,
       CASE WHEN s.is_deal_seller = 1 THEN 'acquired' ELSE 'non_funnel' END AS grp,
       ks.k, s.cohort_size, COALESCE(a.active_n, 0) AS active_n,
       CASE WHEN s.cohort_mi + ks.k <= e.end_mi THEN 1 ELSE 0 END AS observable
FROM sizes s CROSS JOIN ks CROSS JOIN endm e
LEFT JOIN act a ON a.cohort_month = s.cohort_month AND a.is_deal_seller = s.is_deal_seller AND a.k = ks.k
ORDER BY grp, s.cohort_month, ks.k;
