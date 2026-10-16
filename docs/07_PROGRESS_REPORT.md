# 07. Progress Report and Remaining Work
**Project:** Olist Seller Acquisition & Delivery Diagnostics | **Date:** 2026-10-15 (updated after the WP0b/WP0c verdict; 2026-10-14 test-suite repair; WP0 review 2026-10-11; first written 2026-10-10) | **Folder:** `C:\Users\amit0\OneDrive\Desktop\EcommerceRCA`
**Read order for Antigravity:** this file -> `docs/decision_log.md` -> `docs/03_KPI_AND_ANALYSIS_SPEC.md` -> `docs/04_STREAMLIT_SPEC.md` -> `docs/05_AGENT_PLAYBOOK.md`.
**Superseded:** `06_PHASE_A_HANDOFF.md` (written for DuckDB and a Phase A that is now built). Do not use it.

---

## 0b. Status update 2026-10-15 (Claude): formal verdict on WP0b and WP0c = APPROVE

**Evidence (AG's WP0c report, real machine, Python 3.12.9, pytest 9.1.1, pandas 2.2.3, numpy 2.0.2, scipy 1.17.1):**
- `pytest` = **38 passed, 0 skipped, 12 on real data**; header `SYNTHETIC + REAL`. Also as predicted: clean clone 27 passed + 3 skipped; nothing present 26 + 4; works from another folder.
- Full pipeline rebuild from the raw CSVs reproduces every `outputs/` file with **0 differences** (the run is deterministic).
- `sql/01-04` and `sql/06` unchanged (diff empty). Commit **4292cbf** "Phase A+B: pipeline, analysis, tests (verified on real data)" on top of 25d65b2 and c1f77b9. No git remote yet (WP5 needs one).
- Steps 1-3 of the plan in 0a are therefore done. The original "failed again" run was never seen; every failure mode I could identify is fixed and the suite is green on the machine where it failed.

**Labelling corrections (AG called these "Identical"; they are close, not equal; no conclusion changes):** dispatch medians 1.88 d (acquired) vs 1.86 d earlier; per-state shift-share RJ/SP/MG +3.25/+1.78/+1.17 pp vs +3.18/+1.81/+1.14 earlier; worst-10% seller share of late orders 45.83% vs 45.9%; paid vs organic first sale +15.85 pp (CI 5.41 to 26.29) vs +14.9 earlier (organic 81/208 vs 83/208, V-012). Findings use the saved values only.

**Still exploratory (L-011):** downstream first sale by origin, chi-square 9.67, p = 0.046 (earlier 0.065); paid vs organic. WP1 adds the date-level variant.

**Next:** WP1 (Antigravity, prompt in section 9b) and WP2 (Claude, `docs/findings.md` + memo) now run in parallel.

---

## 0a. Status update 2026-10-14 (Claude): tests repaired, WP0b state, plan (steps 1-3 DONE, see 0b)

**What was asked:** "the tests failed again; fix them and plan." No traceback reached me, and the project folder shows the last pytest run (2026-10-11 19:51) with no recorded failure, so I could not see the exact failing run. I rebuilt the suite's failure modes instead, fixed every one I found, and verified under pytest 9.1.1 (the version on your machine). I cannot run commands on your PC, so the run against your real database is still yours to do (step 1 below).

**Why the v1 suite failed or misled**
1. Without the real database, 10 of 13 tests were skipped, not run. The synthetic fallback of D-029 never ran because its fixture depended on the real-database fixture. "Green" on a clean checkout meant 3 tests.
2. Paths to the database fallback, `outputs/` and `data/raw` were relative to the current folder, so running pytest from another folder silently changed which tests ran.
3. The simulator test asserted `low <= high` on random data. That holds on the real data (crude gap above post-delivery gap) but not in general. Fixed in the code, not the test (D-031).
4. The synthetic fixture was 4 orders, so a pass proved little.
5. Real-data tests died with `StopIteration` or a missing-file error instead of skipping with a reason when the raw CSVs or outputs were absent.

**Fix (D-030, D-031)**

| File | Change |
|---|---|
| `tests/synth_db.py` (new) | 13-order hand-built dataset with known answers: window edges, delivered without date, multi-seller order, stage-invalid order, date vs timestamp lateness, review dedup, deal sellers, fan-out trap |
| `tests/conftest.py` (new) | project-root-anchored paths, `synthetic` and `real` modes, fixtures, pytest header/footer saying which mode ran and how many tests ran on real data |
| `tests/test_pipeline.py` (rewritten) | 30 tests: known-answer SQL tests; structural invariants on synthetic and real; independent pandas funnel audit; stats and simulator unit tests incl. Mantel-Haenszel, bootstrap CI, Mann-Whitney sign, chi-square; 4 real-only checks |
| `pytest.ini` (new) | `testpaths = tests`, `-ra` (every skip is listed with its reason) |
| `src/simulator.py` (edited) | `est_1star_low/high` = min/max of the two estimates; real-data values unchanged |

**Verified in my sandbox (pytest 9.1.1):** nothing present (no database, no outputs) 26 passed + 4 skipped; clean clone with the committed `outputs/` folder 27 passed + 3 skipped (each skip states why); a simulated real machine (same pipeline on 4,000 stand-in orders) 37 passed, the only failure being the row-count test, which by design expects the real Olist counts; run from another folder: same as clean checkout; no warnings. **Not verified:** your real database. Expected there: **38 passed, 0 skipped**, header `SYNTHETIC + REAL`, footer `olist: 38 passed, of which 12 ran on REAL data`.

**WP0b state (executed by Antigravity 2026-10-11, 19:42 to 19:56).** The saved files show the work is done; it is **uncommitted** (git log still has only `c1f77b9` and `25d65b2`) and I have not yet seen AG's own WP0b report, so my formal verdict is pending. What I checked in the saved files:
- adjusted OR 4.16 (bootstrap CI 3.70 to 4.66, 47 of 54 strata) vs crude 16.46; post-delivery gap +12.14 pp
- simulator at 5/10/20%: 31/61/122 sellers, 359/542/764 late orders avoided, 1-star range 44-169 / 66-256 / 93-360 (ordered, D-024, D-031)
- Mann-Whitney r = -0.638, p printed as `<1e-300` (D-027)
- cohort month 2: acquired 132/197 vs non-funnel 262/533 (+17.85 pp, CI 10.03 to 25.67), now matching the earlier run under D-025 (V-012)
- 17 `stat_*.csv` files plus `analysis_summary.json`; no `out_app_*.csv` duplicates; `sql/01-04` and `sql/06` unchanged in size from what I wrote
- **not checked:** `src/analysis.py` line by line; AG's comparison table; git beyond the commit log

**Flag for the findings (V-012):** downstream first sale by origin is chi-square 9.67, p = 0.046 (earlier run 0.065); the organic count differs by two deals (81/208 vs 83/208). The result crosses 0.05 on a two-deal difference, so it stays exploratory (L-011) and WP1 adds a date-level variant.

**Plan from here**

| # | Who | What | Done when |
|---|---|---|---|
| 1 | YOU, 5 min | In the project folder run `pytest` (no options). Paste the **full** output into the chat if anything fails | header `SYNTHETIC + REAL`; 38 passed, 0 skipped |
| 2 | YOU or AG, 5 min | One clean commit (see message below). History rewrite is optional (D-028: only if `git remote -v` is empty) | `git status` clean |
| 3 | AG | Paste the WP0b report into the chat (tables, not file names) | Claude gives the formal verdict: APPROVE or REQUEST FIXES |
| 4 | AG (WP1) | Docs reconciliation, data model + dictionary, robustness incl. date-level first sale for the p = 0.046 result | each robustness table states if the conclusion changes |
| 5 | CL (WP2), parallel with 4 | `docs/findings.md` + one-page memo from saved files only | every figure traceable |
| 6 | AG (WP3a-3d) | Streamlit app, one sub-session at a time | numbers on each page equal `analysis_summary.json` |
| 7 | AG, then YOU | WP4 app tests + README; WP5 deploy (your GitHub and Streamlit logins); WP6 resume bullets (CL) | live URL |

**Antigravity prompts:** steps 1-3 are WP0c and step 4 is WP1; both prompts are in section 9, ready to paste (WP1 only after Claude's go-ahead).

**Suggested commit message**
```
Phase A+B: pipeline, analysis, tests (verified on real data)

Statistics layer completed (D-023..D-028), test suite v2 (D-030),
simulator 1-star range ordered by construction (D-031).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TRgnSd8NtjpMnEutxD7Yng
```
Simplest: `git add -A` then `git commit`. Check first that `git status` does not list `data/raw/` or any `.sqlite` (both are in `.gitignore`).

---

## 0. Status update after WP0 (2026-10-11, Claude's review)

**Verdict on WP0: APPROVE WITH FIXES.** The data work is solid and mostly reproduced. Four defects and one gap must be closed in **WP0b** before Claude writes the findings (WP2) or the app reads any statistic. Commits so far: `c1f77b9` (Phase A+B), `25d65b2` (roadmap), local only, not pushed.

**How the code came to exist (for the record).** `olist_code_bundle.zip` never reached the project folder. Claude wrote `sql/01-06`, `requirements.txt` and `.gitignore` straight into the folder on 2026-10-11 (these are what ran, unmodified); Antigravity wrote `src/*.py` and `tests/test_pipeline.py` from the specs. The zip is obsolete. The SQL reproduced almost every headline count of the lost run exactly (96,203 / 6,531 / 4,455 / R$664,580 / 96,470 / 667 and more; the only miss is 288 vs 290), which is good evidence that it is right.

**Reproduction scoreboard**

| Group | Items |
|---|---|
| Reproduced exactly | raw counts; 551 review dedup; 4 shipping outliers; 99,092 / 96,203 / 6,531; 93.21% / 4.1563 / 9.75%; funnel 8,000 / 842 / 380 / 376 / 667 / 4,455 orders / R$664,580 / 96,470; naive join 12,664; lead->deal 10.52% (9.87-11.22); origin chi-square 128.33 (V 0.128); 1-star by delay band; late vs on-time 2.2706 vs 4.2912 and 53.76% vs 6.60%; timing split 18.72% vs 6.58% (1,629 / 88,961); bad months; baseline 4.48% -> 15.15%; dispatch 13.25% / transit 86.75%; compliance 26.90% vs 5.65% (RR 4.76; 22.3% of late orders); crude OR 16.46; geolocation profile (V-009) |
| Small deltas, explained or logged | first sale within 90 days 288 vs 290 (D-026; WP0's "strict vs inclusive" explanation is wrong); shift-share mix -0.01 pp vs +0.08, rate 10.68 vs 10.59 (same conclusion; WP0 called it "exact"); cohort month 2 128/195 vs 258/528, earlier 132/197 vs 262/533 (D-025); audit shows 4,457 orders / R$664,858 for deal sellers vs 4,455 / R$664,580 in the pipeline (consistent with D-002, which drops delivered orders without a delivery date; not separately verified) |
| Definition changed | simulator 61 sellers / 542 late orders / 256 one-star vs earlier 62 / 575 / 199 (D-024); adjusted OR 4.38 retired (D-023); Mann-Whitney sign (D-027) |
| Not reproduced: the statistics code does not exist yet | downstream by origin + chi-square (earlier p 0.065), paid vs organic (+14.9 pp), landing-page V (earlier 0.19), days to close, SDR table (15 of 32 with >= 10 deals; top 3 close 35%), acquired vs non-funnel 2018 seller comparison (109 vs 783 sellers), cohort difference CIs, seller concentration (79 sellers, 45.9%), top-3 states 58.7%, lane SP->RJ, per-state shift-share contributions (earlier RJ +3.18, SP +1.81, MG +1.14 pp), stage times bad vs normal months (earlier transit 8.5 -> 12.4 days) |

**Defects and gap (all go into WP0b)**
1. **Adjusted odds ratio is wrong in the saved pipeline.** `analysis_summary.json` holds `mh_or` 16.4151 with 3 strata that are delay bands; that is no adjustment (crude is 16.46). The WP0 report instead quoted 4.23 and 4.16 from throw-away commands, which breaks honesty rule 1. WP0 also looped over stratification choices looking for results near 4.38 or 16.46, which breaks rule 2 in spirit (R-006); it did report the outcome openly. Fixed by D-023.
2. **Simulator 1-star estimate is inflated.** 256 = 542 x the crude 47.2 pp gap, which the project's own caveat (L-009) says is overstated; the post-delivery gap gives about 66. Fixed by D-024 (always a range).
3. **Tests overstate real-data coverage.** Only T01 (row counts) and T07 (hard-coded constants) touch the real database; T02-T06 and T08 run on a 4-order synthetic fixture; T05 allows 1 day of error where the identity is exact. "11/11 on real data" is really 2 of 11 plus 3 pure-Python checks. Fixed by D-029.
4. **Statistics layer is about half built** (last row of the table above). The spec and the app need every one of those numbers from saved code.
5. **Hygiene.** Duplicate `out_app_orders.csv` (17 MB) and `out_app_funnel.csv` are committed; Mann-Whitney sign and p = 0.0 (D-027); several differences were labelled "EXACT MATCH" in the report; shift-share contributions per state are not saved.

**What is NOT affected:** the SQL layer, the star schema and every headline KPI. The project story (delay is mostly carrier transit and a within-state peak-month surge; dispatch compliance is a real but secondary lever; acquired sellers look better with a selection caveat) stands on reproduced numbers.

**Next:** WP0b (Antigravity, about 1-2 hours) -> WP1 and WP2 in parallel -> app. Details in section 7.

---

## 1. Status at a glance

| Phase | Scope | State | Done |
|---|---|---|---|
| A | Audit, data model, KPIs | Built; headline KPIs reproduced (WP0). Tests v2 green on the real machine (38 passed, 12 on real data). Committed (4292cbf). Data-model docs done (WP1). | 100% |
| B | Funnel, cohorts, RCA, reviews, simulator | SQL layer verified. Statistics layer APPROVED (WP0b/WP0c, 2026-10-15). Robustness (WP1) and findings (WP2) DONE. | 100% |
| C | Streamlit app | 6-page app (Home + pages 1–6) APPROVED (Action Plan, commit 7a46403). Screenshots in `screenshots/`. | 100% |
| D | Tests, README, deploy, resume bullets | 55 tests (38 pipeline + 7 robustness + 7 smoke + 3 numbers), 19 on real data (D-029). README done. WP5 Parts A–D complete (live at https://marketplace-diagnostics-amitkrxzyaidg5hhnexqhxbiu.streamlit.app/). | ~98% |

**Overall: about 98% (2026-10-16)**; phases A–C at 100%, D at ~98% (WP5 parts A–D complete; app deployed to Streamlit Community Cloud).
**Live URL:** [https://marketplace-diagnostics-amitkrxzyaidg5hhnexqhxbiu.streamlit.app/](https://marketplace-diagnostics-amitkrxzyaidg5hhnexqhxbiu.streamlit.app/)

**Remaining work:** WP6 resume bullets (Claude); optional Part F (Reviews & What-If simulator page).

---

## 2. Where everything is

| Location | Contents | Note |
|---|---|---|
| Your folder `EcommerceRCA` | `docs/00-05`, `audit.md`, `decision_log.md`, `02_ROADMAP.md`, this report, `sql/01-06`, `src/*.py`, `tests/test_pipeline.py`, `outputs/` (pipeline results), raw data, git history | `app/` is empty (WP3). Database at `C:\work\olist.sqlite` (outside OneDrive, git-ignored) |
| ~~`olist_code_bundle.zip`~~ | OBSOLETE (2026-10-11) | Never extracted. `sql/01-06`, `requirements.txt`, `.gitignore` were written into the folder by Claude; `src/*.py` and `tests/` by Antigravity. All committed. |
| Lost | Result CSVs and the database from the earlier real-data run | The build environment was reset. WP0 regenerates them (about 1 minute of compute). |

Your docs `00_PROJECT_BRIEF`, `01_ARCHITECTURE` and `05_AGENT_PLAYBOOK` still say DuckDB. The pipeline now uses SQLite (decision D-015). WP1 fixes the wording.

---

## 3. What is built (with evidence)

**Phase A**
- `sql/01_load_clean.sql`: typed clean tables, one review per order (551 duplicates dropped), integrity log.
- `sql/02_star_schema.sql`: `fact_orders` (order grain), `fact_order_items`, `fact_reviews` (one per order), `fact_seller_funnel` (one row per lead), `dim_seller`, `dim_customer`, `dim_product`, `dim_date`, `params`.
- `sql/03_kpis.sql`: monthly, overall and seller KPI tables.
- `src/run_pipeline.py`: one command rebuilds everything from the raw CSVs. It also exports slim app files (`app_orders.csv.gz` about 6.5 MB, `app_funnel.csv` about 0.9 MB) so the 200+ MB database is never deployed.
- (v1 description, superseded by test suite v2: see section 0a and D-030) `tests/test_pipeline.py`: 11 checks (row counts, unique grain, no double counting of value, late-flag consistency, stage times add up, funnel waterfall distinct and non-increasing, funnel equals the independent pandas audit, window rules, simulator monotonic, Wilson CI known value, shift-share decomposition exact). **Real data (earlier): 11/11 pass. Synthetic data (today, after rebuild): 9 pass, 2 skip (assertions that only apply to the real files), 0 fail.**

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

## 4. Preliminary results (earlier real-data run; partly reproduced in WP0, see section 0 for which)

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
9. **(added 2026-10-11) Real-data test coverage is thin** (section 0, defect 3). Fix in WP0b.
10. **(added) Adjusted OR, simulator 1-star range, cohort activity definition** changed by D-023, D-024, D-025; earlier values 4.38 / 199 / 132-of-197 are retired and must not appear in findings, app or resume.
11. **(added) Nothing in the statistics layer is final until WP0b** lists it as produced by saved code.

---

## 7. Remaining work: work packages

Owner: **AG** = Antigravity, **CL** = Claude, **YOU** = you. Size: S about 30-60 min, M 1-2 h, L 3-5 h (split in sub-sessions).

| WP | Owner | Size | What |
|---|---|---|---|
| 0 | AG | S | DONE 2026-10-11, approved with fixes (section 0) |
| 0b | AG | M | EXECUTED 2026-10-11 (uncommitted); Claude's formal verdict pending AG's report. Statistics layer + WP0 defect fixes (D-023 to D-029). **WP2 and WP3 wait for the verdict.** |
| 0c | CL | S | DONE 2026-10-14: test-suite repair (D-030, D-031), section 0a |
| 1 | AG | S | Docs reconciliation + data model docs + robustness checks |
| 2 | CL | S | `docs/findings.md` and a one-page executive memo (after WP0b passes; every figure from saved files) |
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

### WP0b: Close the statistics layer and fix WP0 defects (AG, M, 1-2 h)
Rules: do not change `sql/01-04` or `sql/06`; the only SQL change is `sql/05` (D-025). Fix the definition first, then report whatever comes out (R-006). Every number in the report must come from a saved file. Log anything new in `docs/decision_log.md`.
1. **Adjusted OR (D-023).** In `src/analysis.py` replace the delay-band strata with `review_pre_delivery` x `customer_state` strata. Add a bootstrap 95% CI (500-1,000 resamples of reviewed orders, vectorised counts, fixed seed). Save `crude_or`, `mh_or`, `strata_used`, CI to `analysis_summary.json`. State in the report that 4.38, 4.23 and 4.16 are retired.
2. **Simulator (D-024).** Keep the late-orders-avoided logic. Replace `est_1star_avoided` with `est_1star_low` (flipped x post-delivery gap) and `est_1star_high` (flipped x crude gap), both computed in code from the review table. Allow `pct = 0` (currently forces at least one seller). Add a test: low <= high and monotone in pct.
3. **Cohorts (D-025).** Change `sql/05` so a seller counts as active in a month if any delivered-valid in-window order contains one of their items (join `fact_order_items` to `fact_orders`; keep D-018 for the quality KPIs). Also save the old single-seller version as `stat_cohort_definition_check.csv` (month 1-3 acquired vs non-funnel under both definitions). Add `diff` and a Wald 95% CI per month k to `stat_cohort_compare.csv` (earlier: month 2 +17.9 pp, CI 10.0 to 25.7; comparison only).
4. **Complete the statistics layer.** Save these, each with n, CI where it is a rate, and a small-n flag per D-016:
   - `stat_funnel_origin.csv` (rename of `stat_funnel_origin_ci.csv`, add small-n flag) and `stat_funnel_landing.csv` with chi-square and Cramer's V for pages with >= 100 leads
   - `stat_downstream_origin.csv` with chi-square among origins with >= 30 matured deals, plus paid vs organic difference with CI, labelled exploratory (L-011)
   - `stat_days_to_close.csv` (median, share within 30 and 90 days, band counts)
   - `stat_sdr.csv` (deals, median days to close, flag < 10 deals; top-3 share)
   - `stat_seller_compare_2018.csv` (acquired vs non-funnel, sellers with >= 10 single-seller delivered orders in 2018: medians of on-time rate, dispatch, review; Mann-Whitney effect size per metric)
   - `stat_seller_pareto.csv` and a concentration summary (sellers with >= 20 orders; worst 10%: count, share of late orders, share of orders, pooled late rate vs the rest)
   - `stat_shift_share_state.csv` (per-state mix and rate contributions in pp) and `stat_stage_bad_vs_normal.csv` (order-weighted dispatch, transit, promised days, normal vs bad months)
   - `stat_review_band.csv` (n, mean, 1-star share with Wilson CI per delay band)
   - `stat_late_state.csv` (with top-3 share) and `stat_late_lane.csv` (lanes with >= 50 orders)
   - Mann-Whitney per D-027. Add all new headline values to `analysis_summary.json`.
5. **Tests (D-029).** Run the structural tests (T02-T06, T08) against the real database when it exists, otherwise the synthetic fixture (parametrised fixture is fine); tighten T05 to 1e-3 days; make T07 recompute the funnel from the raw CSVs with pandas; add a real-data test for the simulator range and one for the adjusted OR (value is saved, strata count > 3). The report must say how many tests ran against real data.
6. **Hygiene (D-028, D-027).** Stop exporting `out_app_*` copies and delete the two committed duplicates. Fix the Mann-Whitney sign, docstring and p-value display (D-027). Run `git remote -v`: if it is empty (nothing pushed), squash the two local commits plus this work into one clean history with `git reset --soft` to the root commit and a new commit `Phase A+B: pipeline, analysis, tests (verified on real data)`; if a remote exists, do NOT rewrite history, just commit on top and say so.
7. **Report.** One table: `item | earlier value (comparison only, not a target) | actual | saved in which file`. Mark every difference as a difference (no "EXACT MATCH" unless identical). Include: number of tests run against the real database, the cohort definition check (old vs new), the adjusted OR with CI and strata count, the simulator range at 5/10/20%, the new commit hash, and any new D-/L- entries.
**Acceptance:** all new numbers come from saved files; `pytest` shows at least 9 of 11 tests touching the real database and all pass; `analysis_summary.json` contains the adjusted OR with CI and the simulator low/high; no `out_app_*` duplicates; `sql/01-04` and `06` unchanged (verify with `git diff`); one clean commit.

### WP1: Docs, data model, robustness (AG)
1. Replace DuckDB wording in `00`, `01`, `05` (SQLite, CSV app data). Mark `audit.md` section 6 as superseded.
2. Write `docs/data_model.md` (grain per table taken from the comments in `sql/02_star_schema.sql`, plus a Mermaid ERD) and `docs/data_dictionary.md`. Render the ERD once to `docs/erd.png`.
3. Robustness (new `src/robustness.py`, output `outputs/robustness_*.csv`, no change to existing outputs): (a) late rate and shift-share with bad-month threshold 8%, 10%, 12%; (b) key review and compliance results with timestamp-level instead of date-level lateness, and first-sale-within-90-days at date level (D-026); (c) adjusted OR under a fixed, pre-listed set of strata (timing only, state only, timing x state = D-023); this is a sensitivity table, not a search for a target; (d) simulator with `min_orders` 20 and 50; (e) downstream-by-origin chi-square and paid-vs-organic difference with first sale at date level (D-026), because p crosses 0.05 on a two-deal difference (V-012). Report the change, do not pick the variant that looks best.
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

### WP5: Deploy (AG + YOU) — DONE (2026-10-16)
Parts A–D complete. Pushed to GitHub repo (`https://github.com/amit20kr/marketplace-diagnostics`) on `main` branch, deployed to Streamlit Community Cloud at `https://marketplace-diagnostics-amitkrxzyaidg5hhnexqhxbiu.streamlit.app/`. Pre-flight rehearsal passed, ERD linked, and live app confirmed.

### WP6: Resume bullets (CL)
Three to five quantified bullets using only numbers verified in WP0 and quoted in `findings.md`.

**Suggested order:** WP0 (done) -> WP0b -> (WP1 and WP2 in parallel) -> WP3a -> 3b -> 3c -> 3d -> WP4 -> WP5 (done) -> WP6.

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

**WP0b prompt (paste this):**
> You are the implementation agent in a Claude (architect) / Antigravity (executor) workflow. Read `docs/07_PROGRESS_REPORT.md` section 0 and the WP0b entry in section 7, then the new decisions D-023 to D-029 and R-006 in `docs/decision_log.md`. Execute **Work Package 0b only**. Fix definitions first, then report whatever the data gives; never search over choices to hit an earlier number. Every figure in your report must come from a saved file, not from a throw-away command. Do not change `sql/01-04` or `sql/06`; `sql/05` changes only as D-025 says. Finish with the report described under item 7 (real tables pasted, differences labelled as differences), then stop and wait for Claude's verdict.

## 9b. Prompts added 2026-10-14

**WP0c prompt (paste this now): verify, commit, report.**
```
You are the implementation agent (Antigravity) in a Claude (architect) / Antigravity (executor) workflow.
Read, in this order: AGENTS.md; docs/07_PROGRESS_REPORT.md sections 0a and 0; docs/decision_log.md entries D-023 to D-031, V-012 and R-006.
Execute Work Package 0c ONLY: verify, commit, report. Do not start WP1.

Hard rules
- Do not edit tests/, pytest.ini or src/simulator.py. Claude rewrote them on 2026-10-14 (D-030, D-031).
- Never skip, loosen or delete a test to get a green run. If a test fails, paste the FULL pytest output and stop.
- Do not change sql/01-04 or sql/06. Never touch data/raw/.
- Every number in your report comes from a saved file or a pasted command output.

Steps (PowerShell, project root unless stated)
1. Environment: python --version; pip list (pytest, pandas, numpy, scipy only); git status --short; git log --oneline; git remote -v. Confirm C:\work\olist.sqlite exists (size, modified time) and data\raw holds the 11 CSVs.
2. Reproducibility: copy outputs\analysis_summary.json to C:\work\summary_before.json. Rebuild everything: python src\run_pipeline.py --raw data\raw --db C:\work\olist.sqlite --out outputs. Load both JSON files in Python, compare, and list every key whose value differs. Expected: identical (fixed seeds). Report any difference with your hypothesis; do not edit seeds to make it match.
3. Full test run from the project root: pytest   (no options, no environment variables).
   Expected: header "olist tests: SYNTHETIC + REAL", 38 passed, 0 skipped, footer "olist: 38 passed, of which 12 ran on REAL data".
4. Other modes (PowerShell; afterwards run Remove-Item Env:OLIST_DB, Env:OLIST_OUT):
   a. $env:OLIST_DB="C:\no\such.sqlite"; pytest   -> expected 27 passed, 3 skipped
   b. additionally $env:OLIST_OUT="C:\no\such"; pytest   -> expected 26 passed, 4 skipped
   c. cd C:\work; pytest C:\Users\amit0\OneDrive\Desktop\EcommerceRCA   -> same result as step 3 (tests work from any folder)
5. Review aids for Claude (paste as text):
   a. A map of src\analysis.py: every function, the saved file(s) and analysis_summary.json key(s) it writes.
   b. Every numeric literal in src\analysis.py, src\stats.py and src\simulator.py that is a threshold or parameter (bad-month rate, 90 days, min-n values, bootstrap size, seeds), with the decision ID that sanctions it. Flag any literal that looks like a RESULT or an expected value rather than a parameter.
6. Git: confirm git status does not list data/raw/ or any .sqlite file. Run git add -A and paste git diff --cached --stat. Run git diff --cached --stat HEAD -- sql/01_load_clean.sql sql/02_star_schema.sql sql/03_kpis.sql sql/04_funnel.sql sql/06_delivery_reviews.sql   (must print nothing). Commit ON TOP of the existing history (do not rewrite it) with the message below, then paste git log --oneline.
7. Report to Claude, real tables pasted (not file names):
   A. Environment table (step 1).
   B. Full pytest output of steps 3, 4a, 4b, 4c.
   C. Reproducibility result (step 2).
   D. WP0b results table: item | earlier value (comparison only, not a target) | actual now | saved in which file. Items: crude OR; Mantel-Haenszel OR with CI and strata used/total; simulator at 5/10/20% (sellers fixed, late orders avoided, 1-star low-high); cohort months 1-3 acquired vs non-funnel under D-025 AND under the old single-seller definition (stat_cohort_definition_check.csv); downstream by origin (chi-square, dof, p, V) and paid vs organic difference with CI; landing-page chi-square and V; days to close; SDR summary; 2018 seller comparison (medians, effect sizes, p); seller concentration; top-3 states share of late orders; SP->RJ lane; per-state shift-share top 3 contributions; stage times bad vs normal months; Mann-Whitney r and p. Label every difference as a difference; write "identical" only if equal at the displayed precision.
   E. Review aids (step 5).
   F. Git result (step 6): commit hash, files changed, sql check, git remote -v.
   G. Any decision or limitation you added to docs/decision_log.md, and anything you did not do or could not verify.
Then STOP and wait for Claude's verdict.

Commit message:
Phase A+B: pipeline, analysis, tests (verified on real data)

Statistics layer completed (D-023..D-028), test suite v2 (D-030),
simulator 1-star range ordered by construction (D-031).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TRgnSd8NtjpMnEutxD7Yng
```

**WP1 prompt (paste ONLY after Claude has approved WP0b/WP0c): docs, data model, robustness.**
```
You are the implementation agent (Antigravity) in a Claude (architect) / Antigravity (executor) workflow.
Read AGENTS.md; docs/07_PROGRESS_REPORT.md section 0a and the WP1 entry in section 7; docs/decision_log.md D-017, D-026, D-030, V-012, R-006.
Execute Work Package 1 ONLY.

Rules
- Do not change any existing file in outputs/ or sql/, and do not edit existing tests. You may ADD tests/test_robustness.py (small; same style as tests/test_pipeline.py).
- The variants listed below are fixed in advance. Report each result as found. Do not add variants, and do not pick the one that looks best (R-006).
- Reuse src/stats.py and the functions in src/analysis.py by importing them; do not copy formulas.
- Every number comes from a saved file.

Part 1: docs
1. Replace DuckDB wording with SQLite / CSV app data in docs/00_PROJECT_BRIEF.md, docs/01_ARCHITECTURE.md, docs/05_AGENT_PLAYBOOK.md. Remove stale references to olist_code_bundle.zip. Put a one-line "superseded" note at the top of docs/audit.md section 6.
2. docs/data_model.md: grain per table taken from the comments in sql/02_star_schema.sql (fact_orders, fact_order_items, fact_reviews, fact_seller_funnel, dim_*, params), key relationships, and a Mermaid ERD. Render it once to docs/erd.png (if rendering is impossible say so and keep the Mermaid text).
3. docs/data_dictionary.md: every column of the fact and dim tables with type, meaning, nullability rule and the decision ID that defines it. Derive it from the SQL; do not invent.

Part 2: robustness (new file src/robustness.py; run: python src/robustness.py --db C:\work\olist.sqlite --out outputs)
Outputs: outputs/robustness_*.csv and one outputs/robustness_summary.json with, per table, "conclusion_changes": "yes"/"no" and one sentence why. Fixed seeds. The baseline row of every table must equal the value already saved by the pipeline; the script asserts this and stops with a clear message otherwise.
(a) bad-month threshold 8%, 10%, 12%: months that qualify, baseline vs bad late rate, shift-share mix and rate in pp.
(b) timestamp-level instead of date-level lateness (late_ts): late rate, 1-star late vs on-time, post-delivery gap, dispatch-missed risk ratio.
(c) adjusted OR under three fixed strata sets: review timing only, customer state only, timing x state (= D-023, must equal 4.16); bootstrap CI for each.
(d) simulator min_orders 20, 30 (baseline, must equal stat_simulator.csv), 50.
(e) first sale within 90 days at DATE level (D-026) vs the timestamp baseline (288): overall count, downstream-by-origin chi-square and p, paid vs organic difference with CI.

Part 3: verification
- SHA-256 of every file in outputs/ that existed before you started, before and after: paste the table (must be unchanged).
- pytest with no options: paste the full output (expected 38 passed plus any tests you added).
- Commit on top of the existing history; paste git log --oneline.

Report: the table per robustness check (baseline vs variants, pasted), the conclusion_changes lines, the hash table, the pytest output, the commit hash, and anything you could not verify. Then STOP and wait for Claude's verdict.
```

---

## 10. Definition of done
- Pipeline and tests reproducible from a fresh clone with two commands.
- Findings and the app state the limitations beside every claim; every figure in the README and memo is traceable to a query or script.
- Live Streamlit URL, README with screenshots, 3-5 resume bullets using only verified numbers.
- You can explain, in an interview: why lateness is date-level, why the review gap is reported two ways, why "62% at dispatch" did not hold, and why acquired sellers look better but with selection caveats.
