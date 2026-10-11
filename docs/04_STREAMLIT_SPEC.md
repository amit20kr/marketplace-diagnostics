# 04. Streamlit App Spec (updated; supersedes the earlier DuckDB/parquet version)

Work packages 3a-3d, rules and acceptance criteria are in `docs/07_PROGRESS_REPORT.md` section 7 (WP3). This file is the design reference.

## Data layer
- The app reads ONLY `outputs/` (CSV, `.csv.gz`, JSON). Never `data/raw/` or the SQLite database. No DuckDB, no parquet.
- Inputs: `app_orders.csv.gz`, `app_funnel.csv`, `analysis_summary.json`, `kpi_*.csv`, `funnel_*.csv`, `cohort_*.csv`, `stat_*.csv`.
- Loaders in `app/data.py` with `st.cache_data`. Filters run in pandas on `app_orders`.
- Reuse `src/stats.py` and `src/simulator.py`. Do not rewrite statistics.

## Pages (via `st.navigation`, entry `app/Home.py`)
1. **Executive Summary:** KPI cards, 3 key findings, 3 recommendations, limitations box.
2. **Acquisition Funnel:** waterfall, conversion by origin and landing page with Wilson CIs and n, days-to-close, SDR table with min-n flag. Lead/seller data, so order filters do not apply (say so on the page).
3. **Seller Cohorts:** monthly retention heatmap with masked cells; acquired vs non-funnel comparison with an "insufficient sample" state and a selection-effect caveat. (No quarterly toggle, D-022.)
4. **Delivery Diagnostics:** monthly late-rate trend, stage decomposition (transit vs dispatch), state -> lane -> category drill-down with min-n slider, seller Pareto.
5. **Reviews RCA:** delay-band chart with CIs, Mann-Whitney effect size and bootstrap CI recomputed on filtered data, the survey-timing split shown NEXT TO the crude gap, plain-English interpretation box.
6. **What-If & Actions:** simulator sliders, formula shown, label "association-based scenario, not a forecast"; recommendation table with KPI to monitor.
7. **Data Trust:** join-coverage waterfall, limitations (from decision log), KPI definitions, data dictionary, ERD, sampling/censoring notes, Olist attribution and license.

## Engineering features ("industry level")
- Global sidebar filters (month range, customer state, category) in `st.session_state` with a reset button.
- Every chart: takeaway title, n shown, caveat badge for small n, and a "Show SQL / method" expander that displays the relevant `sql/*.sql` snippet.
- Precomputed `stat_*.csv` files are unfiltered: label "full window (filters not applied)" or recompute from `app_orders`.
- Custom theme in `app/.streamlit/config.toml`; one consistent palette; follow the `dataviz` colour/accessibility basics.
- `st.download_button`: filtered tables (CSV) and an auto-generated executive brief (Markdown) reflecting current filters.
- Graceful states: empty filters, small-n segments, missing files show a message, never a traceback.
- Quality: `AppTest` smoke tests per page (default and empty-result filter); numbers test against `analysis_summary.json`.
- Deployment: Streamlit Community Cloud, entry `app/Home.py`, public URL for README and resume.

## Wording rules in the UI
"associated with", never "caused by"; "observed-selling rate", never "activation rate"; no claim of significance without a computed test; n beside every rate.

## Deliberately excluded
LLM "ask the data" chat, live APIs, auth, predictive ML, Power BI.
