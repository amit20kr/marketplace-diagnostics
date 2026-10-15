# Data Dictionary

This document defines every column of the fact, dimension, and configuration tables in the star schema (`C:\work\olist.sqlite`). All definitions are derived strictly from `sql/01_load_clean.sql` and `sql/02_star_schema.sql` under governing decisions in `docs/decision_log.md`.

---

## 1. Configuration Table

### `params`
- **Grain:** Singleton (1 row).
- **Purpose:** Stores the global analysis window and observation boundary.

| Column | Type | Meaning / Description | Nullability | Governing Decision |
|---|---|---|---|---|
| `window_start` | TEXT | Analysis window start date (`'2017-01-01'`). Orders purchased before are excluded. | NOT NULL | D-011 |
| `window_end_excl` | TEXT | Exclusive end date of analysis window (`'2018-09-01'`). Orders purchased on or after are excluded. | NOT NULL | D-011 |
| `data_end_effective` | TEXT | Effective observation end date (`'2018-08-31'`) for maturity checks. | NOT NULL | D-013 |

---

## 2. Dimension Tables

### `dim_customer`
- **Grain:** 1 row per customer (`customer_id`).

| Column | Type | Meaning / Description | Nullability | Governing Decision |
|---|---|---|---|---|
| `customer_id` | TEXT | Order-level customer identifier (unique per order transaction). Primary key. | NOT NULL | Star schema spec |
| `customer_unique_id` | TEXT | Natural person customer identifier across multiple orders. | NOT NULL | Star schema spec |
| `customer_state` | TEXT | Two-letter Brazilian federative unit code of customer (e.g. `SP`, `RJ`, `MG`). | NOT NULL | Star schema spec |

### `dim_seller`
- **Grain:** 1 row per seller (`seller_id`).

| Column | Type | Meaning / Description | Nullability | Governing Decision |
|---|---|---|---|---|
| `seller_id` | TEXT | Unique seller identifier. Primary key. | NOT NULL | D-008 |
| `seller_state` | TEXT | Two-letter Brazilian state code where seller is registered. | NULLABLE | D-014 |
| `seller_city` | TEXT | City name where seller is registered. | NULLABLE | D-014 |
| `is_deal_seller` | INTEGER | Flag: `1` if seller joined through Olist marketing funnel (`clean_closed_deals`), else `0`. | NOT NULL | D-008 |
| `mql_id` | TEXT | Marketing qualified lead identifier from `clean_closed_deals`. | NULLABLE | D-008 |
| `won_ts` | TEXT | Timestamp when seller closed deal was won. | NULLABLE | D-008 |
| `business_segment` | TEXT | Self-declared business segment (e.g. `online_medium`, `pet`, `health_beauty`). | NULLABLE | D-008, L-008 |
| `origin` | TEXT | Acquisition marketing channel from lead record (e.g. `paid_search`, `organic_search`). | NULLABLE | D-008 |

### `dim_product`
- **Grain:** 1 row per product (`product_id`).

| Column | Type | Meaning / Description | Nullability | Governing Decision |
|---|---|---|---|---|
| `product_id` | TEXT | Unique product identifier. Primary key. | NOT NULL | Star schema spec |
| `category_en` | TEXT | Product category translated into English; falls back to Portuguese or `'unknown'`. | NOT NULL | D-019 |

### `dim_date`
- **Grain:** 1 row per calendar day (`2017-01-01` to `2018-08-31`).

| Column | Type | Meaning / Description | Nullability | Governing Decision |
|---|---|---|---|---|
| `date` | TEXT | Calendar date formatted as `'YYYY-MM-DD'`. Primary key. | NOT NULL | D-011 |
| `month` | TEXT | Year and month formatted as `'YYYY-MM'`. | NOT NULL | D-011 |
| `year` | INTEGER | Calendar year (2017 or 2018). | NOT NULL | D-011 |
| `dow` | INTEGER | Day of week integer (`0` = Sunday, `1` = Monday, ..., `6` = Saturday). | NOT NULL | D-011 |

---

## 3. Fact Tables

### `fact_orders`
- **Grain:** 1 row per order (`order_id`).

| Column | Type | Meaning / Description | Nullability | Governing Decision |
|---|---|---|---|---|
| `order_id` | TEXT | Unique order identifier. Primary key. | NOT NULL | Star schema spec |
| `customer_id` | TEXT | Foreign key referencing `dim_customer.customer_id`. | NOT NULL | Star schema spec |
| `order_status` | TEXT | Status of the order (`delivered`, `shipped`, `canceled`, etc.). | NOT NULL | D-002 |
| `purchase_ts` | TEXT | Purchase timestamp (`'YYYY-MM-DD HH:MM:SS'`). | NOT NULL | D-011 |
| `purchase_month` | TEXT | Year-month of order purchase (`'YYYY-MM'`). | NOT NULL | D-011 |
| `carrier_ts` | TEXT | Timestamp of handoff to carrier (`order_delivered_carrier_date`). | NULLABLE | D-004 |
| `delivered_ts` | TEXT | Actual delivery timestamp to customer (`order_delivered_customer_date`). | NULLABLE | D-002 |
| `est_date` | TEXT | Estimated delivery date (`date(order_estimated_delivery_date)`). | NOT NULL | D-012 |
| `in_window` | INTEGER | Flag: `1` if `purchase_ts` is in `[2017-01-01, 2018-09-01)`, else `0`. | NOT NULL | D-011 |
| `delivered_valid` | INTEGER | Flag: `1` if `order_status = 'delivered'` and `delivered_ts IS NOT NULL`, else `0`. | NOT NULL | D-002 |
| `delay_days` | REAL | Calendar day difference: `date(delivered_ts) - date(est_date)`. Positive indicates late. | NULLABLE | D-012 |
| `is_late` | INTEGER | Flag: `1` if `delay_days > 0` (date-level lateness), `0` if on-time. | NULLABLE | D-012 |
| `late_ts` | INTEGER | Flag: `1` if `delivered_ts > estimated_ts` (timestamp-level lateness). | NULLABLE | D-012 |
| `delay_band` | TEXT | Delay category: `'on_time'`, `'1-3'`, `'4-7'`, or `'8+'` days late. | NULLABLE | D-012, Analysis spec |
| `stage_valid` | INTEGER | Flag: `1` if order is delivered_valid, carrier_ts is present, and `purchase_ts <= carrier_ts <= delivered_ts`. | NOT NULL | D-004 |
| `dispatch_days` | REAL | Seller dispatch duration in fractional days (`carrier_ts - purchase_ts`). | NULLABLE | D-004 |
| `transit_days` | REAL | Carrier transit duration in fractional days (`delivered_ts - carrier_ts`). | NULLABLE | D-004 |
| `promised_days` | REAL | Promised delivery SLA in days (`date(estimated_ts) - date(purchase_ts)`). | NULLABLE | Analysis spec |
| `n_items` | INTEGER | Total line items in order. | NOT NULL | D-009 |
| `n_sellers` | INTEGER | Count of distinct sellers fulfilling items in this order. | NOT NULL | D-018 |
| `seller_id` | TEXT | Attributed seller identifier if `n_sellers = 1`; `NULL` for multi-seller orders. | NULLABLE | D-018 |
| `item_value` | REAL | Total GMV value of order items in BRL (excludes freight). | NOT NULL | D-009 |
| `freight_value` | REAL | Total freight charge of order items in BRL. | NOT NULL | D-009 |
| `freight_ratio` | REAL | Ratio of freight charges to item value (`freight_value / item_value`). | NULLABLE | KPI spec |
| `dispatch_compliant` | INTEGER | Flag: `1` if carrier handoff date $\le$ earliest non-outlier shipping limit date (single-seller orders only). | NULLABLE | D-020 |
| `customer_state` | TEXT | Two-letter state code of purchasing customer. | NULLABLE | Star schema spec |
| `seller_state` | TEXT | Two-letter state code of seller (single-seller orders). | NULLABLE | D-018 |
| `category` | TEXT | English category of item 1 (`primary_product_id`). | NOT NULL | D-019 |
| `review_score` | INTEGER | Customer review rating (1 to 5) from `fact_reviews`. | NULLABLE | D-003 |
| `review_pre_delivery` | INTEGER | Flag: `1` if review creation date is strictly before delivered date, else `0`. | NULLABLE | D-021, L-009 |

### `fact_order_items`
- **Grain:** 1 row per order item line (`(order_id, order_item_id)`).

| Column | Type | Meaning / Description | Nullability | Governing Decision |
|---|---|---|---|---|
| `order_id` | TEXT | Foreign key referencing `fact_orders.order_id`. Part of compound primary key. | NOT NULL | Star schema spec |
| `order_item_id` | INTEGER | Sequential line item number within order (`1, 2, ...`). Part of primary key. | NOT NULL | Star schema spec |
| `product_id` | TEXT | Foreign key referencing `dim_product.product_id`. | NOT NULL | Star schema spec |
| `seller_id` | TEXT | Foreign key referencing `dim_seller.seller_id`. | NOT NULL | Star schema spec |
| `shipping_limit_date` | TEXT | Seller contractual dispatch limit deadline timestamp. | NOT NULL | D-005, D-020 |
| `shipping_limit_outlier` | INTEGER | Flag: `1` if `shipping_limit_date >= '2019-01-01'` (4 outlier items), else `0`. | NOT NULL | D-005 |
| `price` | REAL | Item selling price in BRL. | NOT NULL | D-009 |
| `freight_value` | REAL | Item freight charge in BRL. | NOT NULL | D-009 |

### `fact_reviews`
- **Grain:** 1 row per order (`order_id`). Latest review deduplicated by answer timestamp.

| Column | Type | Meaning / Description | Nullability | Governing Decision |
|---|---|---|---|---|
| `order_id` | TEXT | Unique order identifier. Primary key. | NOT NULL | D-003 |
| `review_id` | TEXT | Review identifier chosen by latest `review_answer_timestamp` tie-break. | NOT NULL | D-003 |
| `review_score` | INTEGER | Customer review score (integer 1 to 5). | NOT NULL | D-003 |
| `review_created_date` | TEXT | Date survey was generated and sent (`'YYYY-MM-DD'`). | NOT NULL | D-003, D-021 |
| `review_answer_timestamp` | TEXT | Timestamp customer submitted answer. | NOT NULL | D-003 |

### `fact_seller_funnel`
- **Grain:** 1 row per marketing qualified lead (`mql_id`).

| Column | Type | Meaning / Description | Nullability | Governing Decision |
|---|---|---|---|---|
| `mql_id` | TEXT | Marketing qualified lead identifier. Primary key. | NOT NULL | Star schema spec |
| `first_contact_date` | TEXT | Date lead was first contacted by marketing. | NOT NULL | KPI spec |
| `contact_month` | TEXT | Year-month of first contact (`'YYYY-MM'`). | NOT NULL | KPI spec |
| `landing_page_id` | TEXT | Marketing landing page ID (or `'(missing)'`). | NOT NULL | D-016 |
| `origin` | TEXT | Acquisition channel origin (or `'(missing)'`). | NOT NULL | D-016 |
| `is_deal` | INTEGER | Flag: `1` if lead converted into a closed deal, else `0`. | NOT NULL | KPI spec |
| `seller_id` | TEXT | Seller identifier assigned upon deal close. | NULLABLE | D-008 |
| `won_ts` | TEXT | Timestamp when deal was won. | NULLABLE | D-008 |
| `won_date` | TEXT | Calendar date when deal was won (`'YYYY-MM-DD'`). | NULLABLE | D-008 |
| `sdr_id` | TEXT | Sales development representative identifier. | NULLABLE | D-016 |
| `business_segment` | TEXT | Declared seller business segment. | NULLABLE | L-008 |
| `lead_type` | TEXT | Declared lead profile classification. | NULLABLE | L-008 |
| `days_to_close` | REAL | Days from first contact to deal close (`won_date - first_contact_date`). | NULLABLE | KPI spec |
| `seller_in_orders` | INTEGER | Flag: `1` if seller has $\ge 1$ item in `fact_order_items`, else `0`. | NOT NULL | D-006, V-002 |
| `first_sale_ts` | TEXT | Earliest purchase timestamp of a delivered order containing seller's item. | NULLABLE | D-025, D-026 |
| `matured_90` | INTEGER | Flag: `1` if deal was won $\ge 90$ days before `data_end_effective` (`2018-08-31`). | NOT NULL | D-007 |
| `first_sale_90` | INTEGER | Flag: `1` if seller had a delivered order within 90 days of `won_ts` (inclusive). | NOT NULL | D-007, D-026 |
