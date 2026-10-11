# 07. Progress Report and Remaining Work
**Project:** Olist Seller Acquisition & Delivery Diagnostics | **Date:** 2026-10-10 | **Folder:** `C:\Users\amit0\OneDrive\Desktop\EcommerceRCA`
**Read order for Antigravity:** this file -> `docs/decision_log.md` -> `docs/03_KPI_AND_ANALYSIS_SPEC.md` -> `docs/04_STREAMLIT_SPEC.md` -> `docs/05_AGENT_PLAYBOOK.md`.
**Superseded:** `06_PHASE_A_HANDOFF.md` (written for DuckDB and a Phase A that is now built). Do not use it.

---

## 1. Status at a glance

| Phase | Scope | State | Done |
|---|---|---|---|
| A | Audit, data model, KPIs | Built; 11/11 tests passed on real data earlier; code was rebuilt after a build-environment reset and re-tested on synthetic data only. **Real-data re-verification pending (WP0).** | ~90% |
| B | Funnel, cohorts, RCA, reviews, simulator | Code and numbers done (earlier real-data run). Findings write-up, robustness checks pending. | ~75% |
| C | Streamlit app | Spec and empty folders only. App-ready data files are produced by the pipeline. | ~5% |
| D | Tests, README, deploy, resume bullets | Pipeline tests done. Everything else pending. | ~10% |

**Overall: about 36%** (effort weights A 15%, B 25%, C 40%, D 20%). The judgment-heavy part, deciding what the data really supports, is mostly done. The remaining ~64% is mostly build and polish that Antigravity does well.

**Rough remaining effort (my estimate):** 6-9 hours of Antigravity agent time, about 5-7 sessions. Your own time: about 45 minutes in total (extract one zip, paste 5-6 reports back to me, one GitHub + Streamlit Cloud login).

---

## 2. Where everything is

| Location | Contents | Note |
|---|---|---|
| Your folder `EcommerceRCA` | `docs/00-05`, `audit.md`, `decision_log.md` (updated today), `02_ROADMAP.md` (updated today), this report, `src/audit.py`, raw data | `sql/`, `tests/`, `app/`, `outputs/` are empty |
| **`olist_code_bundle.zip`** (sent with this report) | 13 files: `sql/01-06`, `src/run_pipeline.py`, `analysis.py`, `stats.py`, `simulator.py`, `tests/test_pipeline.py`, `requirements.txt`, `.gitignore` | **Extract into the project root first.** This is the exact code I tested. |
| Lost | Result CSVs and the database from the earlier real-data run | The build environment was reset. WP0 regenerates them (about 1 minute of compute). |

Your docs `00_PROJECT_BRIEF`, `01_ARCHITECTURE` and `05_AGENT_PLAYBOOK` still say DuckDB. The pipeline now uses SQLite (decision D-015). WP1 fixes the wording.

---

## 3. What is built (with evidence)

**Phase A**
- `sql/01_load_clean.sql`: typed clean tables, one review per order (551 duplicates dropped), integrity log.
- `sql/02_star_schema.sql`: `fact_orders` (order grain), `fact_order_items`, `fact_reviews` (one per order), `fact_seller_funnel` (one row per lead), `dim_seller`, `dim_customer`, `dim_product`, `dim_date`, `params`.
- `sql/03_kpis.sql`: monthly, overall and seller KPI tables.
- `src/run_pipeline.py`: one command rebuilds everything from the raw CSVs. It also exports slim app files (`app_orders.csv.gz` about 6.5 MB, `app_funnel.csv` about 0.9 MB) so the 200+ MB database is never deployed.
- `tests/test_pipeline.py`: 11 checks (row counts, unique grain, no double counting of value, late-flag consistency, stage times add up, funnel waterfall distinct and non-increasing, funnel equals the independent pandas audit, window rules, simulator monotonic, Wilson CI known value, shift-share decomposition exact). **Real data (earlier): 11/11 pass. Synthetic data (today, after rebuild): 9 pass, 2 skip (assertions that only apply to the real files), 0 fail.**

**Phase B** (`sql/04-06`, `src/analysis.py`, `stats.py`, `simulator.py`): funnel with Wilson CIs, origin and landing-page chi-square, days to close, SDR table, seller retention cohorts, acquired vs non-funnel comparison, monthly delivery trend, shift-share, stage decomposition, dispatch compliance, concentration, review analysis (Mann-Whitney with effect size, bootstrap CI, survey-timing split, Mantel-Haenszel), what-if simulator.

**Honest note on synthetic data:** it only proves the code runs and the checks are wired correctly. It says nothing about Olist.

**Changes from the original spec (all logged in `decision_log.md`)**

| Change | Why |
|---|---|
| SQLite instead of DuckDB (D-015) | DuckDB could not be installed in the build environment; SQLite is zero-install and supports the CTEs and window functions used |
| App reads CSV with pandas, not parquet/DuckDB | Simpler, no extra dependencies |
| Geolocation not loaded, no dim_geo (D-014) | State-level analysis only; no maps |
| Window 2017-01..2018-08 (D-011) | 2016 is sparse; Sep-Oct 2018 truncated |
| Lateness at date level (D-012) | Estimated dates have no time of day; timestamp-level gives 8.13% vs 6.79% |
| Quarterly cohort toggle dropped (D-022) | Keeps scope lean |

---

## 4. Preliminary results (earlier real-data run; NOT yet reproduced)

These are the numbers WP0 must reproduce. Treat any mismatch as something to investigate, never as something to quietly adjust.

**Delivery KPIs (window 2017-01..2018-08)**

| Metric | Value |
|---|---|
| Delivered orders / late orders | 96,203 / 6,531 (late rate 6.79%; on-time 93.21%) |
| Average review / 1-star share | 4.156 / 9.75% |
| Avg dispatch / avg carrier transit | 3.2 days / 9.34 days |
| Dispatch-deadline compliance | 94.3% |
| GMV (items) / AOV / freight-to-item-value | R$13.18M / R$137.0 / 0.166 |

**Funnel**

| Stage | Count |
|---|---|
| Leads -> closed deals | 8,000 -> 842 (10.52%, 95% CI 9.87-11.22) |
| Deal sellers in order data / with a delivered order | 380 / 376 |
| Deals with >= 90 days of data / first sale within 90 days | 667 / 290 (43.5%, CI 39.8-47.3) |
| Delivered orders from deal sellers | 4,455 (4.62% of delivered orders), item GMV R$664,580 |
| Days to close | median 14; 65.9% within 30 days; 82.2% within 90 |

- **Lead -> deal by origin:** unknown 16.3%, paid search 12.3%, organic 11.8%, direct 11.2%, referral 8.5%, social 5.6%, email 3.0%. Chi-square 128.3 (8 dof), Cramer's V 0.13. Landing pages: Cramer's V 0.19.
- **Downstream (first sale within 90 days) by origin:** paid 54.8% (80/146), organic 39.9% (83/208). Overall test p = 0.065 (not significant). Paid vs organic is exploratory: +14.9 pp (CI 4.4 to 25.4), chosen after viewing the data, no multiple-comparison correction.
- **SDRs:** 32 SDRs, 15 with at least 10 deals, top 3 close 35% of deals.

**Seller quality and retention (observational; selection caveat L-010)**
- Retention of first-sale cohorts Jan-May 2018 (197 acquired vs 533 non-funnel sellers): month 1 62.4% vs 57.4% (not distinguishable); month 2 67.0% vs 49.2% (+17.9 pp, CI 10.0 to 25.7); month 3 64.0% vs 49.5% (+14.4 pp, CI 6.5 to 22.4).
- 2018 seller comparison (109 vs 783 sellers with at least 10 orders): median on-time 97.3% vs 93.2%; dispatch 1.86 vs 2.46 days; review 4.42 vs 4.21 (effect sizes about 0.3).

**Delivery RCA**
- **The change to explain:** normal-month late rate 4.48% vs 15.15% in the three months with late rate above 10% (Nov 2017, Feb 2018, Mar 2018). Of the +10.67 pp, mix across states explains +0.08 pp and within-state rate increases explain +10.59 pp. Largest contributors: RJ +3.18 pp, SP +1.81, MG +1.14.
- **Stage view:** average transit 8.5 -> 12.4 days in those months, dispatch 3.1 -> 3.7, while promised days stayed about 23-24.
- **Late vs on-time:** extra time is 87% carrier transit (+19.9 days) and 13% seller dispatch (+3.0 days). By larger-excess stage: 83.4% transit, 16.6% dispatch.
- **Dispatch compliance:** 5.7% of orders missed the seller shipping deadline and have a 26.9% late rate vs 5.65% (risk ratio 4.76); they make up 22.3% of late orders.
- **Where:** SP, RJ, MG hold 58.7% of late orders. Highest rates: AL 21.5%, MA 17.5% (small n), CE 13.8%, BA 12.2%, RJ 12.1% (n = 12,310). Lane SP->RJ: 8,031 orders, 14.3% late.
- **Seller concentration:** 43.5% of sellers have at least one late order; the worst 10% of sellers with at least 20 orders (79 sellers) account for 45.9% of seller-attributed late orders and 38.4% of their orders (only mild concentration).
- **Freight and price:** late rate 6.6-7.2% across freight-to-price bands; avg review 4.21 -> 4.11. Price bands: late 6.0% -> 7.9%.

**Reviews**
- Late vs on-time: average 2.27 vs 4.29; 1-star 53.8% vs 6.6% (gap 47.2 pp, CI 45.9-48.4); Mann-Whitney rank-biserial -0.64.
- By delay band, 1-star share: on time 6.6%, 1-3 days late 25.1%, 4-7 days 58.6%, 8+ days 69.8%.
- **Survey-timing caveat:** 74.5% of late orders' reviews were written before the delivery date. Using only reviews written after delivery, the gap shrinks to 18.7% vs 6.6% (+12.1 pp, CI 10.3-14.0). The adjusted odds ratio is 4.38 vs 16.46 crude.
- Late orders are 6.7% of reviewed orders but 36.8% of 1-star reviews.

**Simulator** (bring the worst X% of sellers to the median dispatch of 2.22 days; 611 eligible sellers)

| Worst sellers fixed | Late orders avoided | Share of all late | Est. 1-star avoided |
|---|---|---|---|
| 5% (31 sellers) | 387 | 5.9% | about 129 |
| 10% (62 sellers) | 575 | 8.8% | about 199 |
| 20% (123 sellers) | 823 | 12.6% | about 292 |

---

## 5. Scorecard: the original narrative vs the evidence

| Claim in the planning notes | Verdict (earlier run) |
|---|---|
| Delay is a primary driver of 1-star reviews | Supported as an association, but the headline gap is inflated by survey timing; report the +12 pp and adjusted OR alongside |
| 62% of delays happen at seller dispatch | **Not supported** (about 13-17% dispatch, 83-87% carrier transit) |
| Reallocate SDR capacity from paid to organic | **Not supported**; the exploratory data point the other way |
| Regional cross-docking hubs outside Sao Paulo | Not testable (no cost data). At most a pilot for RJ and Northeast lanes, since lateness there is a transit problem |
| Freight subsidies tied to dispatch compliance | Not supported as a costed plan; freight ratio barely relates to lateness or reviews. Dispatch compliance itself is worth a pilot |
| Acquired sellers perform the same as others | **Refuted**; acquired look better (with selection caveat) |

**Candidate recommendations the data does support (Claude finalises after WP0):**
1. **Recalibrate delivery promises and carrier escalation for peak periods and high-risk lanes.** Lateness spiked within states during three months and transit time rose while promises did not. KPI: on-time rate and promise-vs-actual gap in peak months.
2. **Pilot a seller dispatch-compliance programme.** Orders that miss the seller deadline carry 22% of late orders; fixing the worst 10% of sellers avoids about 9% of late orders (scenario, not forecast). KPI: dispatch compliance and late rate.
3. **Differentiate seller acquisition by channel and add onboarding support.** Email (3.0%) and social (5.6%) convert far below organic and paid (about 12%); 56.5% of deals show no sale within 90 days. KPI: lead-to-deal rate and 90-day first-sale rate by origin.

---

## 6. Known issues, risks and what I could not verify

1. **Rebuilt code is not yet proven on the real files.** This session the copy of the CSVs into my build environment kept failing, so the rebuilt code ran only on synthetic data. The earlier real-data run (11/11 tests) used the same logic. WP0 closes this.
2. **Stale wording:** `docs/audit.md` section 6 still quotes the old ad hoc signal (8.1% late, 2.6 vs 4.3 stars). It is superseded (decision log, "Superseded"). `00`, `01`, `05` mention DuckDB.
3. **Bad-month rule (D-017):** the 10% threshold was chosen after looking at the monthly series. Check 8% and 12%.
4. **Statistical caveats:** Mantel-Haenszel OR has no CI; origin tests and paid-vs-organic are exploratory with no multiple-comparison correction; acquired-vs-non-funnel is observational with selection effects.
5. **Geolocation file unprofiled** (about 1M rows). It is not used in the analysis (D-014); `audit.py` profiles it.
6. **OneDrive:** the project is under OneDrive Desktop and the SQLite file is about 220 MB. Point `--db` at a folder outside OneDrive (for example `C:\work\olist.sqlite`) so sync does not lock the file.
7. **Dataset license:** Olist data is published on Kaggle under CC BY-NC-SA 4.0 (verify on the Kaggle page). Portfolio use is non-commercial; attribute Olist in the README and the app. Order-level app data uses the dataset's anonymised ids.
8. **Tests encode real-data facts** (99,441 orders; 380/376 sellers). On other data they skip, not fail.

---

## 7. Remaining work: work packages

Owner: **AG** = Antigravity, **CL** = Claude, **YOU** = you. Size: S about 30-60 min, M 1-2 h, L 3-5 h (split in sub-sessions).

| WP | Owner | Size | What |
|---|---|---|---|
| 0 | AG | S | Install, run the pipeline on the real data, run tests, reproduce section 4 |
| 1 | AG | S | Docs reconciliation + data model docs + robustness checks |
| 2 | CL | S | `docs/findings.md` and a one-page executive memo (after WP0 passes) |
| 3 | AG | L | Streamlit app (3a-3d) |
| 4 | AG | M | App tests, README, screenshots |
| 5 | AG + YOU | S | GitHub + Streamlit Community Cloud deploy |
| 6 | CL | S | 3-5 resume bullets from verified numbers |

### WP0: Install, reproduce, verify (AG)
1. Extract `olist_code_bundle.zip` into the project root (paths inside are `sql/`, `src/`, `tests/`, `requirements.txt`, `.gitignore`).
2. Create a venv; `pip install -r requirements.txt`.
3. Run `python src/audit.py --raw data/raw --out outputs/audit` (includes geolocation and SHA-256 hashes).
4. Run `python src/run_pipeline.py --raw data/raw --db C:\work\olist.sqlite --out outputs` (database outside OneDrive).
5. Run `pytest -q` (set `OLIST_DB=C:\work\olist.sqlite` if the database is not at `db/olist.sqlite`). **Expected: 11 passed, 0 skipped.**
6. Compare against section 4 and the table in section 8. List every mismatch with the cause; do not adjust code to force a match.
7. `git init`; commit `Phase A+B: pipeline, analysis, tests`.
**Acceptance:** 11/11 pass; every section 8 value reproduced (or mismatch explained); geolocation profiled; no code changes except bug fixes that are logged in `decision_log.md`.
**Report back:** environment versions, test output, the section 8 table with "expected / actual / match", geolocation profile (rows, duplicates per zip prefix), surprises, commit hash.

### WP1: Docs, data model, robustness (AG)
1. Replace DuckDB wording in `00`, `01`, `05` (SQLite, CSV app data). Mark `audit.md` section 6 as superseded.
2. Write `docs/data_model.md` (grain per table taken from the comments in `sql/02_star_schema.sql`, plus a Mermaid ERD) and `docs/data_dictionary.md`. Render the ERD once to `docs/erd.png`.
3. Robustness (new `src/robustness.py`, output `outputs/robustness_*.csv`, no change to existing outputs): (a) late rate and shift-share with bad-month threshold 8%, 10%, 12%; (b) key review and compliance results with timestamp-level instead of date-level lateness; (c) bootstrap 95% CI for the Mantel-Haenszel odds ratio; (d) simulator with `min_orders` 20 and 50.
**Acceptance:** each robustness table states whether the conclusion changes; nothing in the pipeline outputs changes.

### WP2: Findings (CL)
After WP0, I write `docs/findings.md`: three recommendations in the form Finding -> Evidence -> Business impact -> Recommendation -> Trade-off -> KPI, with the limitations box, and a one-page executive memo.

### WP3: Streamlit app (AG; 4 sub-sessions, each ends with a report to me)
Read inputs only from `outputs/` (never from `data/raw/` or the database). Files: `outputs/app_orders.csv.gz`, `app_funnel.csv`, `analysis_summary.json`, `kpi_*.csv`, `funnel_*.csv`, `cohort_*.csv`, `stat_*.csv`. Reuse `src/stats.py` and `src/simulator.py`; do not rewrite statistics.
- **3a:** `app/Home.py` with `st.navigation`, `.streamlit/config.toml` theme, `data.py` (cached loaders), `ui.py` (KPI card, n badge, caveat badge, takeaway title, "Show SQL / method" expander that displays the relevant `sql/*.sql` snippet). Global sidebar filters (month range, customer state, category) in `st.session_state` with a reset button. Page 1 Executive Summary.
- **3b:** Page 2 Acquisition Funnel (waterfall, conversion by origin and landing page with CIs and n, days-to-close, SDR table with min-n flag) and Page 3 Seller Cohorts (monthly retention heatmap with masked cells, acquired vs non-funnel with "insufficient sample" state).
- **3c:** Page 4 Delivery Diagnostics (monthly late-rate trend, stage decomposition, state -> lane -> category drill-down with min-n slider, seller Pareto) and Page 5 Reviews RCA (delay-band chart with CIs, Mann-Whitney effect size and bootstrap CI recomputed live on filtered data, **and the survey-timing split shown next to the crude gap**, plain-English interpretation box).
- **3d:** Page 6 What-If & Actions (simulator sliders; show the formula and the label "association-based scenario, not a forecast"; recommendation table with KPI to monitor) and Page 7 Data Trust (funnel waterfall, limitations from the decision log, KPI definitions, ERD, sampling notes, Olist attribution). CSV download buttons and an auto-generated executive brief (Markdown) that reflects the current filters.

Rules: precomputed `stat_*.csv` files are unfiltered. Where a page shows them, label "full window (filters not applied)" or recompute from `app_orders`. Funnel and cohort pages use lead and seller data, so the order filters do not apply there; say so on the page. Empty filters and small-n segments must show a message, not an error.
**Acceptance per sub-session:** with filters reset, every number on the page equals the matching value in `analysis_summary.json` or the CSV; all pages load without exceptions; screenshot of each page attached to the report.

### WP4: App tests, README (AG)
1. `tests/test_app_smoke.py` using `streamlit.testing.v1.AppTest`: every page runs without exceptions, with default and with an "empty result" filter.
2. `tests/test_app_numbers.py`: unfiltered headline numbers equal `analysis_summary.json`.
3. README, story first: problem, 3 findings, 3 recommendations, screenshots, architecture and ERD, how to run (two commands), limitations, dataset attribution and license note.
4. Fresh-clone test: new folder, clone, install, run pipeline, run tests, launch the app.
**Acceptance:** all tests pass; fresh clone works without edits.

### WP5: Deploy (AG + YOU)
GitHub repo (no raw data, no database; `outputs/app_*` and the `stat_*`/`kpi_*` files are committed); Streamlit Community Cloud pointing at `app/Home.py`; confirm the live URL loads and shows the same numbers as local. **You:** log in to GitHub and Streamlit Cloud once.

### WP6: Resume bullets (CL)
Three to five quantified bullets using only numbers verified in WP0 and quoted in `findings.md`.

**Suggested order:** WP0 -> (WP1 and WP2 in parallel) -> WP3a -> 3b -> 3c -> 3d -> WP4 -> WP5 -> WP6.

---

## 8. Reproduction checklist for WP0 (expected values from the earlier real-data run)

| Item | Expected |
|---|---|
| Table rows (raw) | orders 99,441; items 112,650; reviews 99,224; customers 99,441; sellers 3,095; leads 8,000; closed deals 842 |
| Review rows dropped by dedup | 551 (98,673 remain) |
| Shipping-limit outliers (>= 2019) | 4 |
| In-window orders / delivered-valid / late | 99,092 / 96,203 / 6,531 |
| On-time rate; avg review; 1-star share | 93.21%; 4.156; 9.75% |
| Single-seller / multi-seller orders (window) | 97,079 / 1,274 |
| Funnel waterfall | 8,000; 842; 380; 376; 667; 290; 4,455 orders; R$664,580; 96,470 delivered |
| Lead -> deal | 10.52% (CI 9.87-11.22) |
| Review by delay band, 1-star % | 6.60; 25.12; 58.58; 69.81 |
| Late vs on-time review average | 2.271 vs 4.291; 1-star 53.76% vs 6.60% |
| Timing split (post-delivery reviews) | 18.72% vs 6.58% (1,629 late / 88,961 on time) |
| Bad months (rate > 10%) | 2017-11, 2018-02, 2018-03 |
| Shift-share | baseline 4.48%; bad 15.15%; change 10.67 pp = mix 0.08 + rate 10.59 |
| Dispatch share of late-order extra time | 13.3% (transit 86.7%) |
| Dispatch-deadline: missed vs met late rate | 26.90% (5,412 orders) vs 5.65% (89,517) |
| Simulator 10% | 62 sellers; 575 late orders avoided; about 199 one-star |
| Cohort month 2 (Jan-May 2018 cohorts) | 132/197 acquired vs 262/533 non-funnel |
| Mantel-Haenszel OR / crude OR | 4.38 / 16.46 (25 strata) |

---

## 9. Kickoff prompts for Antigravity

**WP0 prompt (paste this):**
> You are the implementation agent in a Claude (architect) / Antigravity (executor) workflow. Read `docs/07_PROGRESS_REPORT.md`, `docs/decision_log.md` and `docs/05_AGENT_PLAYBOOK.md` first. Execute **Work Package 0 only** from section 7 of the progress report. Do not change SQL definitions or add features. Never edit `data/raw/`. Use a database path outside OneDrive. If any number differs from section 8, report the difference and a root-cause hypothesis; do not tune code to match. Finish with the report in the format listed under "Report back", with real tables pasted, then stop and wait for Claude's verdict.

**Later work packages:** use the same wording, replacing "Work Package 0" with the package and its acceptance criteria from section 7.

---

## 10. Definition of done
- Pipeline and tests reproducible from a fresh clone with two commands.
- Findings and the app state the limitations beside every claim; every figure in the README and memo is traceable to a query or script.
- Live Streamlit URL, README with screenshots, 3-5 resume bullets using only verified numbers.
- You can explain, in an interview: why lateness is date-level, why the review gap is reported two ways, why "62% at dispatch" did not hold, and why acquired sellers look better but with selection caveats.
