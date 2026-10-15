# 02. Roadmap (status as of 2026-10-14, after the test-suite repair)

Status key: [x] done and verified | [r] built, awaiting Claude's review | [~] done but needs fixes (named) | [ ] not started
Full detail, scoreboard, work packages and kickoff prompts: docs/07_PROGRESS_REPORT.md (sections 0a and 0 are the latest status)

## Phase A: Audit, data model, KPIs  (~95%)
- [x] A1 Repo skeleton, docs 00-05, .gitignore, requirements
- [x] A2 File inventory + profiling (src/audit.py ran on all 11 files; geolocation profiled, V-009)
- [x] A3 sql/01_load_clean.sql (raw -> typed clean tables, cleaning log)
- [x] A4 sql/02_star_schema.sql (facts + dims, grain stated)
- [x] A5 sql/03_kpis.sql (monthly, overall, seller KPIs); headline KPIs reproduced on real data
- [x] A6 src/run_pipeline.py (one command rebuild); duplicate out_app_* exports removed (D-028)
- [x] A7 tests v2 (D-030): known-answer SQL tests on a 13-order dataset, structural checks on synthetic and real data, independent pandas funnel audit, real-only checks with stated skip reasons. 27 passed + 3 skipped on a clean clone (committed outputs/, no database); 38 passed with the real database
- [ ] A8 docs/data_model.md (grain table + ERD) and docs/data_dictionary.md (WP1)
- [~] A9 Commit: only the two early commits exist (c1f77b9, 25d65b2); all WP0b work and test suite v2 are uncommitted. One clean commit pending (D-028)

## Phase B: Analysis  (~80%)
- [x] B1a SQL for funnel, cohorts, delivery, reviews (sql/04-06) verified on real data
- [r] B1 Funnel statistics: lead->deal, origin and landing chi-square, downstream by origin (chi-square 9.67, p = 0.046, boundary-sensitive, V-012), paid vs organic (exploratory), days to close, SDR table saved
- [r] B2 Seller cohorts: D-025 activity definition in sql/05; month-2 retention 132/197 vs 262/533 reproduced (V-012); difference CIs and 2018 seller comparison saved
- [r] B3 Delivery RCA: shift-share per state, stage bad vs normal, dispatch compliance, concentration, state and lane tables saved
- [r] B4 Reviews: adjusted OR 4.16 (CI 3.70-4.66, 47 strata), crude 16.46, post-delivery gap +12.1 pp, Mann-Whitney r -0.64 (D-027)
- [r] B5 Simulator: 1-star effect is a range, ordered by construction (D-024, D-031); 10%: 542 late orders avoided, about 66 to 256 one-star
- [ ] B6 Robustness checks (bad-month threshold 8/10/12%, timestamp vs date-level lateness, first-sale date-level, adjusted-OR strata sensitivity, simulator min_orders) (WP1)
- [ ] B7 docs/findings.md: 3 recommendations (Finding -> Evidence -> Impact -> Recommendation -> Trade-off -> KPI) + 1-page executive memo (Claude writes after the WP0b verdict)

## Phase C: Streamlit app  (~5%; app-ready data files are produced by the pipeline)
- [ ] C1 Theme, navigation, cached data layer, global filters
- [ ] C2 Pages 1-7 (docs/04_STREAMLIT_SPEC.md, with the simplifications in docs/07_PROGRESS_REPORT.md section 7)
- [ ] C3 Show-SQL/method expanders, n badges, caveat badges, CSV + brief downloads
Starts after the WP0b verdict and the clean commit: the app must only read statistics produced by saved, reviewed code.

## Phase D: Tests, deploy, polish  (~15%)
- [ ] D1 Streamlit AppTest smoke test + "app numbers equal analysis_summary.json" test
- [ ] D2 README (story first, ERD, screenshots, how to run, limitations, dataset attribution/license)
- [ ] D3 Fresh-clone reproducibility test (the pipeline tests already pass on a clean checkout in synthetic mode)
- [ ] D4 Deploy to Streamlit Community Cloud (owner login needed)
- [ ] D5 Resume bullets (Claude, verified numbers only)

## Next steps in order
1. YOU + AG (10 minutes): run `pytest`, paste the full output; make the one clean commit (D-028) with the message in docs/07_PROGRESS_REPORT.md section 0a; paste AG's WP0b report so Claude can give the formal verdict.
2. WP1 (Antigravity) and WP2 (Claude) in parallel.
3. WP3a-3d app, WP4 app tests and README, WP5 deploy, WP6 resume bullets.

## Review protocol
Antigravity executes a work package -> pastes the report (tables and full test output, not file names) -> Claude verdict (APPROVE / REQUEST FIXES / REVISE PLAN) -> next package. See 05_AGENT_PLAYBOOK.md.
