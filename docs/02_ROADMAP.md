# 02. Roadmap (status as of 2026-10-10)

Status key: [x] done and verified | [b] built and tested on synthetic data (and earlier on real data) but needs re-verification on real data (WP0) | [ ] not started
Full detail, work packages and kickoff prompts: docs/07_PROGRESS_REPORT.md

## Phase A: Audit, data model, KPIs  (~95%)
- [x] A1 Repo skeleton, docs 00-05, .gitignore, requirements
- [x] A2 File inventory + profiling (src/audit.py ran on 11 files; geolocation profiled)
- [x] A3 sql/01_load_clean.sql (raw -> typed clean tables, cleaning log)
- [x] A4 sql/02_star_schema.sql (facts + dims, grain stated)
- [x] A5 sql/03_kpis.sql (monthly, overall, seller KPIs)
- [x] A6 src/run_pipeline.py (one command rebuild)
- [x] A7 tests/test_pipeline.py (11/11 passed on real data)
- [ ] A8 docs/data_model.md (grain table + ERD) and docs/data_dictionary.md
- [x] A9 Commit "Phase A+B: pipeline, analysis, tests" (c1f77b9)

## Phase B: Analysis  (~85%)
- [x] B1 Funnel: waterfall, origin/landing page with Wilson CIs, days to close, SDR table, segment view (sql/04, src/analysis.py)
- [x] B2 Seller cohorts + acquired vs non-funnel comparison (sql/05, src/analysis.py)
- [x] B3 Delivery RCA: monthly trend, shift-share, stage decomposition, concentration, dispatch compliance
- [x] B4 Reviews: delay bands, Mann-Whitney + effect size, bootstrap CI, survey-timing split, Mantel-Haenszel
- [x] B5 Simulator (src/simulator.py) + unit test
- [ ] B6 Robustness checks (bad-month threshold 8/10/12%, timestamp-level vs date-level lateness, bootstrap CI for adjusted OR)
- [ ] B7 docs/findings.md: 3 recommendations (Finding -> Evidence -> Impact -> Recommendation -> Trade-off -> KPI) + 1-page executive memo (Claude writes after WP0 passes)

## Phase C: Streamlit app  (~5%; app-ready data files are produced by the pipeline)
- [ ] C1 Theme, navigation, cached data layer, global filters
- [ ] C2 Pages 1-7 (docs/04_STREAMLIT_SPEC.md, with the simplifications in docs/07_PROGRESS_REPORT.md section 7)
- [ ] C3 Show-SQL/method expanders, n badges, caveat badges, CSV + brief downloads

## Phase D: Tests, deploy, polish  (~10%)
- [ ] D1 Streamlit AppTest smoke test + "app numbers equal analysis_summary.json" test
- [ ] D2 README (story first, ERD, screenshots, how to run, limitations, dataset attribution/license)
- [ ] D3 Fresh-clone reproducibility test
- [ ] D4 Deploy to Streamlit Community Cloud (owner login needed)
- [ ] D5 Resume bullets (Claude, verified numbers only)

## Review protocol
Antigravity executes a work package -> pastes the report (tables, not file names) -> Claude verdict (APPROVE / REQUEST FIXES / REVISE PLAN) -> next package. See 05_AGENT_PLAYBOOK.md.
