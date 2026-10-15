# Findings and Recommendations: Olist Seller Acquisition & Delivery Diagnostics

**Status:** DRAFT v1, 2026-10-15 (Claude, WP2). Written from the saved pipeline outputs of commit `4292cbf` only (`outputs/analysis_summary.json` and `outputs/stat_*.csv`, `out_*.csv`). Every figure carries its source file. Robustness checks (WP1: bad-month threshold, timestamp-level lateness, date-level first sale, adjusted-OR strata, simulator min-n) are not yet in; the places they could change a statement are marked **[WP1]**.
**Scope of the data:** Olist public sample, orders purchased 2017-01-01 to 2018-08-31 (D-011), 96,203 delivered-valid orders, R$13.18 M item GMV, plus the marketing funnel (8,000 leads, 842 closed deals). It is a sample: "not observed" never means "did not sell" (L-001).

**How to read the claims.** All relationships below are *associations in observational data*. Nothing here is a causal estimate, and the simulator is an arithmetic scenario, not a forecast (honesty rule 3). There is no cost, margin or CAC data, so no recommendation is costed (L-004).

---

## 1. The story in five lines

1. About **6.8%** of delivered orders arrive late (6,531 of 96,203; 95% CI 6.63% to 6.95%).
2. Late delivery is **mostly a carrier-transit problem, not a seller-dispatch problem**: carrier transit is about 87% of the extra time of late orders, dispatch about 13%.
3. Lateness is **concentrated by destination** (RJ and BA run at about 12% vs 4.5% in SP) and **surges within the same states in peak months** (Nov 2017, Feb and Mar 2018), a rate effect, not a change in the order mix.
4. Late orders are **strongly associated with 1-star reviews**, but a large part of the crude gap is survey timing: the gap falls from 47 pp (crude) to 12 pp when only reviews written after delivery are used.
5. Sellers brought in through the funnel **look better than other sellers** (on-time, dispatch, reviews, month-2 retention), with a selection caveat; channel conversion differs, and the data does **not** support moving effort away from paid search.

---

## 2. Findings with evidence

### F1. Late delivery is a carrier-transit problem first
- **Baseline:** 6,531 late of 96,203 delivered-valid orders = 6.79% (CI 6.63 to 6.95). `analysis_summary.json` `kpi`.
- **Where the extra time is:** late orders take on average +3.04 days more dispatch and +19.91 days more carrier transit than on-time orders: dispatch 13.25%, transit 86.75% of the extra time. Late orders: dispatch 6.04 d, transit 27.90 d; on-time: 3.00 d, 7.99 d. `analysis_summary.json` `delivery`.
- **Bad months vs normal months** (late rate over 10%: 2017-11, 2018-02, 2018-03): late rate 15.15% vs 4.48%. Average carrier transit 12.44 d vs 8.49 d (+3.96 d) and dispatch 3.66 d vs 3.08 d (+0.58 d), so about 87% of the extra time is again transit (arithmetic on the two rows of `stat_stage_bad_vs_normal.csv`). The promised delivery window was *not* longer in the bad months (23.6 vs 24.5 days).
- **Rate effect, not mix:** the late-rate change of +10.67 pp splits into a mix effect of -0.01 pp and a rate effect of +10.68 pp. The surge happened *inside* states, not because the order mix moved to harder states. `stat_shift_share_state.csv`. The largest contributions are RJ +3.25 pp, SP +1.78 pp, MG +1.17 pp, RS +0.65 pp.
- **Concentration by destination:** RJ 12.14% late (1,495 of 12,310 orders; CI 11.58 to 12.73) and BA 12.17% (396 of 3,253) vs SP 4.50% (1,817 of 40,399) and MG 4.59%. SP, RJ and MG together hold 58.7% of all late orders; SP and RJ alone 50.7%. `stat_late_state.csv`.
- **Worst lane:** SP to RJ, 14.28% late (1,147 of 8,031 orders; CI 13.53 to 15.06), 17.6% of all late orders on 8.3% of orders (arithmetic on the lane row), against 4.71% for SP to SP. `stat_late_lane.csv`.
- **What it means:** the largest lever is the carrier leg to specific destinations and the peak-season capacity of that leg. The earlier idea "62% of delays happen at seller dispatch" is not supported (R-001, H2).
- **Caveats:** the data shows where delay appears, not why (no carrier id, no weather or strike data). Peak months coincide with Black Friday / Carnival season, which is context, not something this data tests. **[WP1]** will show how the bad-month list moves at 8% and 12% (D-017 chose 10% after seeing the series) and the timestamp-level late rate (8.13%, `out_late_sensitivity.csv`).

### F2. Seller dispatch is a real but secondary lever
- **Dispatch compliance:** 94.3% of orders were handed to the carrier by the shipping limit date. For the 5,412 that missed it, the late rate is 26.9% vs 5.65% for the 89,517 that met it: risk ratio 4.76, and missed-dispatch orders are 22.3% of all late orders. `analysis_summary.json` `delivery`.
- **Seller concentration (sellers with at least 20 orders: 787):** the worst 10% of them (79 sellers) have a late rate of 8.23% vs 5.77% for the other 90%. They account for 45.8% of all late orders; among the sellers in the Pareto table they hold 52.6% of late orders on 43.7% of orders. They are large sellers, so their share of lateness is only moderately above their share of volume: this is not a "few bad sellers cause most lateness" story. `analysis_summary.json` `seller.seller_concentration`; `stat_seller_pareto.csv`.
- **Scenario (simulator, D-024):** if the worst X% of eligible sellers (611 sellers with at least 30 orders; ranked by late-order **count**, so large sellers rank first) were brought to the median seller-average dispatch time of 2.56 days:

| Worst sellers fixed | Sellers | Late orders avoided | Share of all late orders | One-star avoided (range) |
|---|---|---|---|---|
| 5% | 31 | 359 | 5.5% | 44 to 169 |
| 10% | 61 | 542 | 8.3% | 66 to 256 |
| 20% | 122 | 764 | 11.7% | 93 to 360 |

  The one-star range runs from flipped orders x the post-delivery gap (12.14 pp) up to flipped orders x the crude gap (47.16 pp); the crude figure is an upper bound because many reviews predate delivery (L-009). `stat_simulator.csv`.
- **What it means:** a seller scorecard and a dispatch target aimed at the sellers who miss the shipping limit date would remove roughly 6 to 12% of late orders (scenario, not forecast). It does not fix F1.
- **Caveats:** association-based; assumes the dispatch time of the worst sellers could actually move to the median without side effects. **[WP1]** will show sensitivity to the eligibility threshold (min orders).

### F3. Late delivery is associated with bad reviews, and survey timing inflates the crude gap
- **By delay band:** share of 1-star reviews 6.60% on time (n = 89,182), 25.12% for 1-3 days late (n = 1,851), 58.58% for 4-7 days (n = 1,748), 69.81% for 8+ days (n = 2,779). Mean score 4.29 / 3.29 / 2.10 / 1.70. `stat_review_band.csv`.
- **Late vs on time:** mean 2.27 vs 4.29; 1-star 53.76% vs 6.60%; gap 47.17 pp (CI 45.97 to 48.35). Mann-Whitney rank-biserial r = -0.64 (large; p below 1e-300, which with 96k orders mostly says the sample is large). `analysis_summary.json` `reviews`.
- **Survey timing (L-009):** most late orders' reviews were written before the delivery date. Using only reviews written after delivery: 1-star 18.72% (n = 1,629 late) vs 6.58% (n = 88,961 on time), a gap of **12.14 pp**, one quarter of the crude gap.
- **Adjusted:** Mantel-Haenszel odds ratio over review timing x customer state: 4.16 (bootstrap 95% CI 3.70 to 4.66, 47 of 54 strata used) vs crude 16.46 (D-023). The earlier 4.38 is retired.
- **What it means:** being late is associated with markedly worse reviews even after allowing for timing and state, but the headline "late orders get 54% one-star" should always be shown beside the 12.1 pp post-delivery gap.
- **Caveats:** reviews of undelivered or wrong-item orders are also in the 1-star pool (L-006); the review is voluntary. **[WP1]** adds the timestamp-level lateness variant.

### F4. Sellers acquired through the funnel look better, with a selection caveat
- **Funnel:** 8,000 leads, 842 closed deals = 10.52% (CI 9.87 to 11.22). Median 14 days to close; 65.9% within 30 days; 82.2% within 90. `analysis_summary.json` `funnel`; `stat_days_to_close.csv`.
- **Coverage (stated plainly):** only 380 of the 842 deal sellers appear in the order data (376 with a delivered order). Everything downstream rests on those sellers (L-002). 667 deals have 90 days of data after the deal; 288 of them (43.2%) made a first sale within 90 days. `out_funnel_waterfall.csv`.
- **Acquired vs other sellers, 2018 (109 acquired vs 783 non-funnel sellers, single-seller orders):** median on-time rate 97.3% vs 93.2% (r = +0.31); median dispatch 1.88 vs 2.46 days (r = -0.31); median review 4.42 vs 4.21 (r = +0.29). `analysis_summary.json` `seller.seller_compare_2018`.
- **Retention (Jan-May 2018 cohorts, 197 acquired vs 533 non-funnel sellers):** active in month 2: 67.0% vs 49.2%, difference +17.85 pp (CI 10.03 to 25.67). Month 3: +14.43 pp (CI 6.49 to 22.36). Month 1: +5.03 pp, CI -2.93 to 12.99, so **no clear difference in month 1**. `stat_cohort_compare.csv`.
- **Caveats:** observational with selection (L-010): acquired sellers are seen only if they appear in the order data, and cohorts start at the first *observed* sale. The funnel may recruit stronger sellers, or the sellers may have been strong anyway. Not evidence that the funnel *makes* sellers better.

### F5. Channel conversion differs; the data does not support moving effort away from paid search
- **Lead to deal by origin** (chi-square 128.3, 8 dof, Cramer's V 0.13): organic search 11.80% (271 of 2,296), paid search 12.30% (195 of 1,586), direct 11.22%, **social 5.56% (CI 4.45 to 6.91)**, **email 3.04% (CI 1.85 to 4.96)**, unknown 16.29%. By landing page, V = 0.19. `stat_funnel_origin.csv`, `stat_funnel_landing.csv`.
- **Downstream (first sale within 90 days of the deal):** paid search 54.8% (80 of 146) vs organic 38.9% (81 of 208): +15.85 pp (CI 5.41 to 26.29). Across all origins the test gives chi-square 9.67, p = 0.046, which is **boundary-sensitive** (an earlier run with a two-deal difference gave p = 0.065, V-012). **Exploratory** (L-011: no multiple-comparison correction). `stat_downstream_origin.csv`.
- **What it means:** paid search converts at least as well as organic and its deals were at least as likely to sell soon after, so the proposal "move SDR effort from paid to organic" is not supported (R-004). Social and email convert at about half the rate of search or less, with clear CI separation, but the numbers are small (75 and 15 deals).
- **Caveats:** no cost or CAC data, so "converts better" says nothing about return on spend (L-004). Segment, lead type and SDR exist only for closed deals, so they cannot explain conversion (L-008). SDR table: 32 SDRs, 15 with at least 10 deals; the top 3 closed 295 of 842 deals (35.0%); lead-level SDR conversion is not computable. **[WP1]** adds the date-level first-sale variant for the p = 0.046 result.

---

## 3. Recommendations

Each: Finding -> Evidence -> Opportunity (scenario) -> Trade-off -> KPI to monitor.

### R1. Make the carrier leg to the slow destinations the first delivery priority
- **Finding:** about 87% of extra time on late orders is carrier transit; RJ and BA run near 12% late vs 4.5% in SP; the SP to RJ lane alone is 17.6% of all late orders; the peak-month surge is a within-state rate effect (+10.68 pp).
- **Evidence:** F1 (n = 96,203; lane n = 8,031).
- **Opportunity:** if SP to RJ were brought to the SP to MG level of 5.35% late (a stand-in for a comparable inland lane), about 730 late orders would not occur (8,031 x (14.28% - 5.35%) = 717 by arithmetic on `stat_late_lane.csv`; round to "roughly 700", about 11% of all late orders). Scenario only; the gap includes distance and carrier effects the data cannot separate.
- **Trade-off:** carrier capacity, a regional hub or a second carrier cost money and the data holds no costs; a longer promised window would lower late rate but may hurt conversion, also unmeasured.
- **KPI:** late rate by destination state and for SP to RJ / SP to BA; average carrier transit days; late rate in Nov, Feb and Mar versus the rest of the year.

### R2. Put the sellers that miss the shipping limit date on a dispatch scorecard
- **Finding:** orders that miss the shipping limit are 4.8 times as likely to be late and make up 22.3% of late orders; the worst 10% of eligible sellers (by late count) run 8.2% late vs 5.8%.
- **Evidence:** F2 (5,412 missed vs 89,517 met; 787 eligible sellers).
- **Opportunity:** the simulator puts it at 542 late orders avoided (8.3% of late) for 61 sellers moved to the median dispatch time, and 66 to 256 fewer one-star reviews (range, D-024).
- **Trade-off:** it will not move the transit problem; requires seller onboarding and enforcement effort; large sellers who are asked to speed up may raise cost or reduce volume.
- **KPI:** share of orders handed to the carrier by the shipping limit date (94.3% now); average dispatch days of the 10% largest-late-count sellers; share of late orders with a missed dispatch.

### R3. Keep funnel investment, test the weak channels, and track new sellers on the same scorecard
- **Finding:** acquired sellers outperform other sellers on on-time rate, dispatch, reviews and month-2 retention (selection caveat); social and email leads convert at roughly half or less of search; paid search is not worse than organic.
- **Evidence:** F4 and F5 (109 vs 783 sellers; social 75 deals of 1,350 leads; email 15 of 493).
- **Opportunity:** do not shift SDR effort from paid to organic. Run a short test on social and email follow-up (is a lower close rate worth the SDR time?) once cost per lead is known. If acquired sellers keep their month-2 retention gap in newer cohorts, the funnel is worth protecting.
- **Trade-off:** the effect on seller quality may be selection; the funnel covers only 380 of 842 deal sellers in the order data, so decisions should be revisited with a complete seller feed.
- **KPI:** lead-to-deal rate by origin with n; share of matured deals with a first sale in 90 days (43.2% now); month-2 seller retention for acquired vs non-funnel cohorts; median days to close (14 now).

---

## 4. What this analysis does NOT claim
- No causal effect of delay on reviews, of the funnel on seller quality, or of any recommendation on outcomes.
- No profitability, CAC, margin or ROI statement; no costed plan (L-004).
- Not that dispatch is the main cause of delay (it is not, F1), nor that sellers acquired by the funnel are better *because* of it (F4).
- The origin and paid-vs-organic downstream results are exploratory (L-011); p = 0.046 is not a finding on its own.
- The 4.38 adjusted OR, the 62% dispatch share, 575 late orders avoided and 199 one-star avoided are retired and appear nowhere in this document.

## 5. Open items before this goes final
1. Fill in the **[WP1]** robustness tables; revise any statement whose conclusion moves.
2. Check that the app and README quote the same numbers (a test compares the app to `analysis_summary.json`).
3. Verify the CC BY-NC-SA licence wording on Kaggle and credit Olist in the README.

## 6. Where each number lives
| Figure | File |
|---|---|
| Headline KPIs, late rate, dispatch share, compliance, review gaps, adjusted OR, concentration, funnel summary, cohort and seller comparison, simulator | `outputs/analysis_summary.json` |
| Origin and landing conversion, downstream by origin | `outputs/stat_funnel_origin.csv`, `stat_funnel_landing.csv`, `stat_downstream_origin.csv` |
| Days to close, SDR table | `outputs/stat_days_to_close.csv`, `stat_sdr.csv` |
| Funnel waterfall and join coverage | `outputs/out_funnel_waterfall.csv` |
| Shift-share by state, stage times bad vs normal | `outputs/stat_shift_share_state.csv`, `stat_stage_bad_vs_normal.csv` |
| Late rate by state and lane, Pareto, timestamp vs date-level | `outputs/stat_late_state.csv`, `stat_late_lane.csv`, `stat_seller_pareto.csv`, `out_late_sensitivity.csv` |
| Reviews by delay band | `outputs/stat_review_band.csv` |
| Cohort retention and differences | `outputs/stat_cohort_compare.csv` |
| Simulator | `outputs/stat_simulator.csv` |
