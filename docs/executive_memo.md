# Executive Memo: Cutting Late Deliveries and Strengthening Seller Acquisition at a Brazilian Marketplace

**For:** operations and seller-growth leads · **Basis:** Olist public sample, orders purchased 2017-01 to 2018-08 (96,203 delivered orders), plus 8,000 marketing leads and 842 closed deals · **Evidence:** `docs/findings.md`, `outputs/`

## The answer

Treat late delivery as a **carrier-leg problem first and a seller-dispatch problem second**. Start a seller dispatch scorecard now (quick to run, about 540 late orders, 8% of all late), open a second-carrier pilot on the slowest lane (about 700 late orders, 11%), keep the seller funnel, and test two weak lead channels before spending more. These two delivery figures overlap and must not be added. Each action is a scenario drawn from observational data, so each needs a controlled pilot before commitment.

## Why it matters

- **6.8% of orders arrive late** (6,531 of 96,203). Late orders receive a 1-star review 53.8% of the time against 6.6% for on-time orders.
- **Part of that gap is survey timing.** Many reviews on late orders were written before the parcel arrived. Counting only reviews written after delivery, the gap is **7.7 to 12.1 percentage points**, depending on how lateness is defined, and the adjusted odds ratio is 4.2 (95% CI 3.7 to 4.7). Late delivery is still clearly associated with worse reviews.

## What we found

1. **Most of the extra time is in transit.** About 87% of the additional days on late orders are carrier transit, 13% seller dispatch. The "62% of delay is at the seller" hypothesis we started with was tested and rejected.
2. **It is concentrated and seasonal.** RJ and BA run about 12% late against 4.5% in SP. The SP-to-RJ lane alone is 17.6% of all late orders on 8.3% of volume. In the three worst months (Nov 2017, Feb and Mar 2018) the late rate rose from 4.5% to 15.2%, and the rise happened inside the same states, not because the order mix shifted. The same three months qualify at any threshold between 8% and 12%.
3. **Dispatch matters, but less.** Orders that miss the shipping limit are late 26.9% of the time against 5.7% (4.8 times as likely) and make up 22.3% of late orders.
4. **Acquired sellers look stronger, with a caveat.** On-time rate 97.3% against 93.2% and month-2 retention 17.9 points higher (CI 10.0 to 25.7), but the funnel may simply have recruited stronger sellers.
5. **Channels differ.** Lead-to-deal conversion is 10.5% overall; social (5.6%) and email (3.0%) convert at half the rate of search or less. Paid search converts as well as organic, so moving effort away from it is not supported.

## Recommendations

| # | Action | Opportunity (scenario) | Trade-off | KPI |
|---|---|---|---|---|
| R2 | Dispatch scorecard for sellers who miss the shipping limit | About 540 late orders avoided (range 400 to 610 by seller cut-off) | Does not touch transit; needs enforcement effort; may push large sellers away | Dispatch compliance (94.3% now); late rate of flagged sellers |
| R1 | Second-carrier pilot on SP to RJ and SP to BA | About 700 late orders if SP-to-RJ matched a comparable lane | Carrier cost unknown; longer promise windows may hurt conversion | Late rate by lane; carrier transit days; peak-month late rate |
| R3 | Keep the funnel; A/B test social and email follow-up | Not sized (no cost data) | Weak channels have few deals, so intervals are wide | Lead-to-deal rate with CI; month-2 seller retention |

Suggested order: R2 and R3 first (lower effort), R1 as the larger programme. Effort ratings are analyst judgement and should be replaced by the business's own estimates.

## How to prove it works

Randomise: orders between carriers (R1), flagged sellers between scorecard and no scorecard (R2), new leads between follow-up cadences (R3). Fix the success threshold and the stop rule before starting. For R1 the dashboard's Action Plan page sizes the pilot; for a 3-point reduction on SP to RJ it needs roughly 1,900 orders per arm (two-proportion test, 5% significance, 80% power).

## Risks and limits

Everything here is an association in a public 2017–2018 sample; nothing is causal. Only 380 of 842 closed-deal sellers appear in the order data, so seller conclusions describe that subset. There is no cost, margin or acquisition-cost data, so no return on investment is claimed and any business case needs those figures first.

## Next steps

1. Agree the pilot thresholds and owners for R2 and R3 with operations and seller growth.
2. Obtain carrier costs for SP to RJ and SP to BA to size R1 properly.
3. Re-run this analysis on current data before committing budget.
