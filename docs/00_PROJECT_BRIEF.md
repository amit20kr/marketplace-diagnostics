# 00. Project Brief: Olist Seller Acquisition & Delivery Diagnostics

## Purpose
A side-resume project (Business / Strategy / Product Analytics roles) that demonstrates:
real business data -> SQL/data model -> KPIs -> funnel & cohorts -> root-cause analysis -> business decisions -> Streamlit story.

It fills the portfolio gap: **customer/business behaviour -> why a KPI changed (RCA) -> what the company should do next.**

## Owner context
IIT BHU Mining Engineering, graduating 2027, placements 2026-27. Primary resumes: DS/AI-ML and Data/Business Analyst. This project feeds a third resume (Business Mgmt, Strategy & Ops, Product Analytics/Ops, Growth/Category Analytics, Consulting, Finance/BFSI Analytics).

## Roles
- **Claude** = architect and reviewer. Plans each phase, reviews reports, gives a verdict.
- **Antigravity** = implementation agent. Builds, runs, tests, and reports.
- **Owner** = downloads data, pastes reports to Claude, one-time deploy login.

## Datasets (Kaggle, `olistbr`)
1. Brazilian E-Commerce Public Dataset (9 CSVs).
2. Marketing Funnel by Olist (2 CSVs: leads, closed deals).
Bridge key: `seller_id` (closed_deals -> sellers -> order_items).

## Business questions
1. **Funnel:** how many leads become closed deals, how fast, which origin/segment converts better; how many closed-deal sellers are *observed* selling in the order data?
2. **Delivery:** what share of orders is late, and where (stage, lane, state, category, seller) does lateness come from?
3. **Satisfaction:** do late orders get lower reviews, and how large is the effect?
4. **Decision:** which 3 actions should management take, how big is the opportunity, which KPI tracks it?

Out of scope on purpose: profitability, CAC/SDR cost, freight policy costing, take-rates, repeat purchase, ML, LLM chat.

## Honesty rules (non-negotiable)
1. Every number comes from a saved SQL query or script. No hand-typed results.
2. Count distinct sellers/orders, never joined rows (lead-to-order joins fan out).
3. Show n beside every rate; flag or hide segments below a minimum n.
4. Say "associated with", never "caused by". Scenarios are scenarios, not forecasts.
5. No result is decided in advance. *Hypothesis* items are tested and reported as found.
6. The order data is a sample: "not in orders" means "not observed selling in this dataset".

## Hypotheses (to test, never to hardcode)
- H1: delivery delay is strongly associated with 1-2 star reviews.
- H2: in late orders, seller dispatch (not carrier transit) is the larger share of lost time.
- H3: lead origin and business segment are associated with deal conversion and seller activity.
- H4: sellers acquired via the funnel perform similarly to other sellers (null expected; report honestly).
- Candidate actions (recommend only if evidence supports): seller dispatch-compliance incentives, SDR/channel reallocation, regional fulfilment pilots, delivery-promise recalibration on specific lanes.

## 7-step story coverage
| Step | Where delivered |
|---|---|
| 1 Real business data | Both Olist datasets |
| 2 SQL & data model | `sql/` + DuckDB star schema (see 01_ARCHITECTURE) |
| 3 KPI analysis | `sql/03_kpis.sql`, see 03_KPI_AND_ANALYSIS_SPEC |
| 4 Segmentation & cohorts | funnel by origin/segment, seller retention cohorts |
| 5 RCA | delay decomposition, concentration, review-by-delay-band, Mann-Whitney + effect size |
| 6 Decisions | 3 recommendations + what-if simulator |
| 7 Dashboard & story | 7-page Streamlit app (see 04_STREAMLIT_SPEC) |
