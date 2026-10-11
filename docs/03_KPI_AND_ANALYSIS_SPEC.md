# 03. KPI Definitions and Analysis Spec

## KPI definitions (delivered orders unless stated; distinct-order grain)
| KPI | Definition |
|---|---|
| On-time rate | delivered_customer_date <= estimated_delivery_date |
| Delay days | delivered_customer_date - estimated_delivery_date (positive = late) |
| Seller dispatch time | delivered_carrier_date - order_purchase_timestamp |
| Carrier transit time | delivered_customer_date - delivered_carrier_date |
| Dispatch compliance | carrier handoff <= shipping_limit_date |
| Review score, % 1-2 star | one review per order (CSAT proxy) |
| GMV proxy, AOV | item price (+ freight reported separately), distinct orders |
| Freight-to-price ratio | freight_value / price, item and order level |
| Lead -> deal conversion | closed deals / leads, by origin, segment, landing page, month (mature cohorts only) |
| Days to close | won_date - first_contact_date |
| Seller observed-selling rate | closed-deal sellers with >= 1 delivered order / closed-deal sellers |
| Seller retention | % of a first-sale cohort with >= 1 delivered order in month k (cells beyond data end masked) |

## Analyses
**A. Funnel.** Waterfall: leads -> closed deals -> sellers in sellers table -> sellers in order_items -> sellers with a delivered order. Conversion by origin / segment / landing page with Wilson 95% CIs and n. Days-to-close distribution. SDR table: deals closed and median days-to-close per SDR (min-n). **SDR conversion rate is not computable** because the lead table has no SDR column (verify in Phase A).

**B. Seller cohorts.** First-sale-month cohorts, retention heatmap (monthly/quarterly toggle), masked incomplete cells, minimum cohort size. Acquired vs other sellers on dispatch time, on-time rate, review score, retention; show "insufficient sample" when n is too small. Exclude or flag closed-deal sellers whose first order precedes won_date.

**C. Delivery RCA.** Baseline and monthly trend, worst months. Stage decomposition of late orders (approval / seller dispatch / carrier transit). Concentration by state, lane (seller state -> customer state), category, seller (min-n); Pareto of late orders by seller. Optionally mix-vs-rate (shift-share) decomposition of the change between a good and a bad period.

**D. Reviews.** % 1-star and mean score by delay band (on time, 1-3, 4-7, 8+ days late). Mann-Whitney U (late vs on-time) with rank-biserial effect size; bootstrap CI for the 1-star-rate gap. Caveats: reviews can predate delivery; some low scores reflect non-delivery or wrong item.

**E. Decisions.** 3 recommendations, each: Finding -> Evidence (n, effect) -> Opportunity (scenario) -> Trade-off -> KPI to monitor. Only actions the data supports.

## Simulator (`src/simulator.py`, deterministic, no ML)
Input: X% of worst sellers (by late-order count, min orders) brought to the median dispatch time.
For their orders: delay_new = delay - max(0, dispatch_time - median_dispatch). Count orders flipping late -> on-time.
Estimated 1-star avoided = flipped orders x (1-star rate among late - 1-star rate among on-time).
The app must show this formula and label the result an association-based scenario, not a causal forecast.

## Statistical rules
- Check assumptions before any test; with ~100k rows p-values are nearly always tiny, so effect sizes and CIs carry the story.
- Do not claim significance before it is calculated. Do not claim causation.
- Minimum n for any segment shown as a ranking (default 30 orders / 10 sellers; configurable).
