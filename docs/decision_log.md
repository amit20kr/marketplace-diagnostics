# Project Decision Log

Format: ID | status | statement | evidence. Prefixes: V validated fact, D decision, L limitation, R rejected approach, H hypothesis status.
Last updated: 2026-10-10. Items marked (earlier run) come from a real-data run made before the build sandbox was reset; they are NOT final until reproduced in Work Package 0 (see docs/07_PROGRESS_REPORT.md).

## Validated facts (Phase A audit; see docs/audit.md)
- V-001 | confirmed | Row counts match public figures for 10 audited tables; leads 8,000, closed deals 842. | audit.py
- V-002 | confirmed | 380 of 842 deal sellers (45.1%) are in the sellers/order data; 376 have a delivered order; 462 are absent. | funnel waterfall
- V-003 | confirmed | 0 of 380 linked sellers had an order before won_date; median 44 days from won_date to first order. | date checks
- V-004 | confirmed | Naive leads x deals x order_items join produces 12,664 rows from 8,000 leads. | funnel waterfall
- V-005 | confirmed | Lead table has no SDR column; SDR conversion rate is not computable. | cardinalities
- V-006 | confirmed | Orders 2016-09-04 to 2018-10-17; deals won 2017-12-05 to 2018-11-14 (17 deals after last order). | date ranges
- V-007 | confirmed | reviews.order_id is not unique (547 orders with >1 review; 551 rows dropped by the dedup rule). | key uniqueness, clean_log
- V-008 | confirmed | Order volume is sparse outside 2017-01..2018-08: 329 orders in 2016-09..12, 16 in 2018-09, 4 in 2018-10. | monthly counts

## Decisions
- D-001 | Stack: SQLite (Python stdlib) + pandas/scipy + Streamlit. No Power BI, no PostgreSQL, no ML. Reason: side-target project, minimal owner effort. (Amended by D-015: DuckDB was the original plan.)
- D-002 | Delivery KPIs use `order_status = 'delivered'` AND non-null delivered date (excludes 8 delivered orders with no delivery date).
- D-003 | One review per order: keep the latest by `review_answer_timestamp` (tie-break `review_creation_date`, then review_id); 551 rows dropped.
- D-004 | "Seller dispatch time" = carrier handoff - purchase timestamp (avoids negative approval-to-carrier gaps in 1,359 orders). Stage metrics (dispatch/transit) use only orders where purchase <= carrier <= delivered ("stage-valid").
- D-005 | `shipping_limit_date` values >= 2019-01-01 (4 items; max 2020-04-09) are outliers, excluded from dispatch-compliance KPIs.
- D-006 | Metric naming: "observed-selling rate", not "activation rate", because the order data is a sample.
- D-007 | Funnel downstream metrics use only deals with >= 90 days of order data after won_date (667 deals).
- D-008 | Acquired vs other sellers: acquired = deal sellers observed in order data; comparison group = "non-funnel" sellers (may include sellers from leads outside the closed-deal set or sellers who joined independently).
- D-009 | GMV proxy = sum of item price at distinct-order grain; freight reported separately; payments table only for reconciliation (99.61% match).
- D-010 | Raw folders keep their names with spaces (`EcommercePub dataset`, `Marketing funnel`); scripts locate files recursively by file name.
- D-011 | Analysis window: orders purchased 2017-01-01 to 2018-08-31 (2016 is sparse; 2018-09/10 are truncated).
- D-012 | Lateness is date-level: delivered date vs estimated date compared as calendar dates, because estimated dates carry no time of day. Timestamp-level comparison would also flag same-day deliveries as late (8.13% vs 6.79% in the window). Report both only in the robustness section.
- D-013 | Effective data end for observation windows: 2018-08-31.
- D-014 | Geolocation file is not loaded; no dim_geo; no map analysis (state-level only). It is still to be profiled by audit.py (L-007).
- D-015 | SQLite replaces DuckDB (DuckDB could not be installed in the build environment; SQLite needs no install and supports the CTE/window-function SQL used). The app reads CSV files with pandas; no parquet or DuckDB at runtime.
- D-016 | Minimum-n rules: origin / landing page >= 100 leads; SDR >= 10 deals; downstream-by-origin chi-square >= 30 deals with window; seller group comparison >= 10 orders per seller; seller Pareto >= 20 orders; simulator-eligible sellers >= 30 orders; lanes >= 50 orders; categories >= 100 orders.
- D-017 | "Bad months" for the shift-share = months with late rate > 10% (2017-11, 2018-02, 2018-03 in the earlier run). The threshold is a round number chosen AFTER viewing the monthly series; sensitivity (8% / 12%) must be checked in the robustness package.
- D-018 | Seller-level KPIs use single-seller delivered orders only; the 1,274 multi-seller orders stay in order-level KPIs.
- D-019 | Order primary category = category of item 1 of the order.
- D-020 | Dispatch compliance = carrier handoff date <= earliest non-outlier shipping limit date of the order; single-seller orders only; date-level.
- D-021 | "Review created before delivery" flag is date-level (review_creation_date has no time of day).
- D-022 | Quarterly cohort toggle dropped; monthly retention heatmap only (keeps scope lean).

## Limitations
- L-001 | Order data is a sample: absent from orders means "not observed", not "never sold".
- L-002 | 462 deal sellers cannot be analysed downstream; downstream funnel metrics rest on 376-380 sellers.
- L-003 | Lost vs still-open leads are indistinguishable (no outcome flag for non-closed leads).
- L-004 | No cost, margin, CAC or SDR-cost data; no costed recommendation is possible.
- L-005 | Four closed_deals columns are >90% null and unusable.
- L-006 | Reviews are observational; some precede delivery or relate to non-delivered orders; causal claims are not allowed.
- L-007 | Geolocation file not yet profiled.
- L-008 | business_segment, lead_type and SDR exist only for closed deals, so they cannot explain lead->deal conversion; they support only downstream/onboarding views.
- L-009 | Survey timing: about three quarters of late orders' reviews were written before the delivery date (earlier run: 74.5%), so the crude late-vs-on-time review gap overstates the effect of delay on post-delivery satisfaction. Report crude and timing-split figures together.
- L-010 | Acquired-vs-non-funnel comparison is observational with selection effects (acquired sellers are observed only if they appear in orders; cohorts are defined by first observed sale).
- L-011 | Origin-level and paid-vs-organic tests are exploratory; no multiple-comparison correction.
- L-012 | The Mantel-Haenszel adjusted odds ratio is a point estimate without a confidence interval.

## Hypothesis status (earlier real-data run; reproduce before relying on it)
- H1 delay -> low reviews: SUPPORTED as an association. Crude 1-star 53.8% (late) vs 6.6% (on time); effect shrinks to +12.1 pp when only post-delivery reviews are used; Mantel-Haenszel adjusted OR 4.38 vs crude 16.46.
- H2 "62% of delay is seller dispatch": NOT SUPPORTED. Dispatch accounts for about 13% of the extra time of late orders (carrier transit about 87%); by larger excess stage: 16.6% dispatch vs 83.4% transit.
- H3 origin/landing page associated with conversion: SUPPORTED for lead->deal (Cramer's V 0.13 origin, 0.19 landing page). Downstream (90-day first sale) by origin: not significant at 5% (p = 0.065).
- H4 acquired sellers perform like others: REFUTED in this data (acquired look better on on-time rate, dispatch, reviews, month-2/3 retention), with selection caveat L-010.

## Rejected / unsupported ideas
- R-001 | Pre-baked results from earlier planning notes ("62% at dispatch", "p < 0.001") are not used as inputs; they were tested (see H1, H2).
- R-002 | Seller take-rate analysis (no data); regional-hub or freight-subsidy costing (no cost data); repeat-purchase analysis (about 3.4% fewer distinct people than customer_ids; thin).
- R-003 | Power BI, ML, LLM features.
- R-004 | "Reallocate SDR capacity from paid to organic" is not supported: paid search converts at least as well as organic (12.3% vs 11.8%) and its sellers were more likely to make a first sale within 90 days (54.8% vs 39.9%, exploratory).
- R-005 | "Freight subsidy to improve satisfaction" has no support: late rate and review score barely vary across freight-to-price bands (late 6.6-7.2%; review 4.21 -> 4.11).

## Superseded
- F-000 (old ad hoc signal: 8.1% late, reviews 2.6 vs 4.3, 1-star 46% vs 7%) used timestamp-level lateness, no window and a different review rule. The authoritative figures come from the pipeline (late 6.79% date-level in window; average review 2.27 vs 4.29; 1-star 53.8% vs 6.6%; earlier run).
