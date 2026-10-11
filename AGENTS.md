# AGENTS.md: START HERE (implementation agent)

You are the **implementation agent (Antigravity)** in a two-agent workflow. **Claude** is the architect and reviewer; the **owner** is an IIT BHU Mining Engineering student building a side-resume portfolio project for Business / Strategy / Product-Analytics / Finance-Analytics roles. You have not seen this project before. This file gives you everything you need to begin.

## 1. The project in five lines
- **Title:** Olist Seller Acquisition & Delivery Diagnostics.
- **Data:** Olist Brazilian E-Commerce (9 CSVs) + Olist Marketing Funnel (2 CSVs), joined on `seller_id`. Raw files: `data/raw/EcommercePub dataset/` and `data/raw/Marketing funnel/` (folder names contain spaces; scripts find files recursively by name).
- **Chain to demonstrate:** business data -> SQL/star schema -> KPIs -> funnel & cohorts -> root-cause analysis -> business decision -> Streamlit story.
- **Final deliverable:** a 7-page, industry-level **Streamlit** app + README + findings, deployed on Streamlit Community Cloud.
- **Not in scope:** Power BI, ML, LLM chat, profitability/CAC, repeat purchase. Keep it simple; do not add libraries or features that are not in the docs.

## 2. Stack (final; older wording elsewhere is wrong)
SQLite (Python stdlib `sqlite3`) for SQL | pandas, numpy, scipy | plotly | Streamlit | pytest.
**There is no DuckDB and no parquet.** The app reads CSV / `.csv.gz` / JSON from `outputs/` only.
Environment: Windows. Keep the SQLite database **outside OneDrive** (e.g. `C:\work\olist.sqlite`) because OneDrive sync can lock the file.

## 3. Source-of-truth order (when documents disagree)
1. `docs/decision_log.md` (decisions D-xxx, validated facts V-xxx, limitations L-xxx). **Wins over everything.**
2. `sql/*.sql` and `src/*.py` (the actual definitions; the code is the spec of what is computed).
3. `docs/07_PROGRESS_REPORT.md` (status, work packages, expected values to reproduce).
4. `docs/03_KPI_AND_ANALYSIS_SPEC.md`, `docs/04_STREAMLIT_SPEC.md`, `docs/01_ARCHITECTURE.md`, `docs/00_PROJECT_BRIEF.md`.
5. `docs/audit.md` (Phase A notes; its section 6 is **superseded**).
If you find a conflict, do not guess: log it in `docs/decision_log.md` and ask Claude in your report.

## 4. Read order
`AGENTS.md` -> `docs/07_PROGRESS_REPORT.md` (find your work package) -> `docs/decision_log.md` -> `docs/05_AGENT_PLAYBOOK.md` -> the spec for your task (`03` for analysis, `04` for app) -> the SQL/Python you will touch.

## 5. Current state (as of the hand-over)
- Phase A (audit, cleaning, star schema) and Phase B (KPIs, funnel, cohorts, statistics) are **written and tested on synthetic data only**. They have **not yet been run on the real CSVs in this repo**. That is Work Package 0.
- Numbers in the progress report are **preliminary** until WP0 reproduces them. Never present them as final.
- The code arrives as `olist_code_bundle.zip`; the owner extracts it into the project root. If `sql/` and `src/` are empty, stop and tell the owner.

## 6. How the pipeline works
`python src/run_pipeline.py --raw data/raw --db <path>.sqlite --out outputs` loads the 10 analysed CSVs as TEXT into `raw_*` tables (geolocation is not loaded, D-014; the audit script still profiles it), runs `sql/01..06` in order (clean -> star schema -> KPIs -> funnel -> cohorts -> delivery/reviews), exports every `out_*` table to `outputs/*.csv`, writes `app_orders.csv.gz` and `app_funnel.csv`, then runs `src/analysis.py` (statistics -> `outputs/stat_*.csv`, `analysis_summary.json`). Tests: `pytest -q` (override paths with env vars `OLIST_RAW`, `OLIST_DB`, `OLIST_OUT`).

## 7. Key definitions you must not change without Claude's approval
- **Window:** orders 2017-01-01 to 2018-08-31 (D-011); effective data end 2018-08-31 (D-013). Anything after is right-censored / masked.
- **Delivered-valid order:** status `delivered` with a delivery date (D-002). **Stage-valid:** purchase <= carrier handoff <= delivered.
- **Lateness is date-level** (estimated dates have no time of day, D-012): delay_days = delivered date - estimated date; late if > 0. Timestamp-level gives 8.13% vs 6.79% date-level; the robustness work reports both.
- **Dispatch time** = carrier handoff - purchase timestamp (D-004). Carrier transit = delivered - carrier handoff.
- **Reviews:** one per order, latest by answer timestamp (D-003). About 74.5% of late orders' reviews were written *before* delivery, so the crude late-vs-on-time review gap is inflated; always show the post-delivery split next to it.
- **Seller-level KPIs** use single-seller orders only (D-018). **"Observed-selling rate"**, never "activation rate" (D-006). Funnel conversion uses matured cohorts / 90-day windows (D-007).
- **Min-n:** origin 100, SDR deals 10, seller orders 10 (D-016). Small segments are flagged, not ranked.
- **Fan-out trap:** a naive leads x deals x order_items join turns 8,000 leads into 12,664 rows. Always count DISTINCT keys at the right grain.

## 8. Honesty rules (non-negotiable)
1. Every number comes from a saved SQL file or script. No hand-typed results.
2. Never hardcode or tune toward an expected finding. If results contradict a hypothesis or the progress report, report the contradiction.
3. Say "associated with", never "caused by". Simulator output is an association-based scenario, not a forecast.
4. Do not claim significance before it is calculated. Show n beside every rate.
5. Never hide join loss: report coverage (e.g. only 380 of 842 deal sellers appear in the order data).
6. Never edit `data/raw/`. Never change SQL definitions or the star schema silently: log any bug fix in `docs/decision_log.md` with the reason.
7. Keep it simple. No new libraries, models or features beyond the specs.

## 9. Workflow and reporting
Work on **one work package at a time** (listed in `docs/07_PROGRESS_REPORT.md` section 7). Finish with a report in the template of `docs/05_AGENT_PLAYBOOK.md`, with **real tables pasted** (not file names), then **stop and wait for Claude's verdict**. If blocked, say what is blocked and what you tried; do not work around the problem by relaxing a check.

## 10. Known things not to be fooled by
- "62% of delays happen at seller dispatch" is **not supported** (earlier run: dispatch about 13% of extra time, carrier transit about 87%). Do not reintroduce it.
- "Reallocate SDR effort from paid to organic" is **not supported** by the data.
- `docs/06_PHASE_A_HANDOFF.md`, if you ever see it, is obsolete (DuckDB-based). Ignore it.
- Dataset license is believed to be CC BY-NC-SA 4.0 (verify on Kaggle); credit Olist; do not commit raw data.
