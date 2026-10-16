# Olist Seller Acquisition & Delivery Diagnostics

## The Question
What drives delivery delays and customer dissatisfaction on Olist, and does acquiring sellers through the marketing funnel improve downstream marketplace performance?

## Key Findings (Associations in Observational Data)
1. **Most of the extra delay time is carrier transit:** ~87% of late orders' extra time is carrier transit (+19.91 d vs +3.04 d dispatch). Late deliveries concentrate by destination (RJ 12.1%, BA 12.2% vs SP 4.5%) and peak months (Nov 2017, Feb–Mar 2018), accounted for by a within-state rate effect (+10.68 pp), not by order mix.
2. **Seller dispatch is a secondary lever:** Missed shipping deadlines are associated with higher lateness (26.9% vs 5.65%, RR 4.76) and represent 22.3% of late orders. In simulation, shifting the worst 10% of sellers to median dispatch avoids 542 late orders (8.3% of all late).
3. **Survey timing inflates review gap:** The crude 1-star gap (53.8% late vs 6.6% on-time, 47.2 pp) drops to 12.1 pp (18.7% vs 6.6%) when restricted to reviews written after delivery. Adjusted odds ratio (timing × state) is 4.16 (95% CI 3.70–4.66).

Full narrative and evidence: `docs/findings.md`; one-page summary for managers: `docs/executive_memo.md`; sensitivity analysis tables: `outputs/robustness_*.csv`.

## Recommendations
1. **Prioritise carrier transit on slow lanes and peak periods:** Address high-delay lanes (e.g., SP→RJ at 14.3% late) and peak-month bottlenecks with logistics partners.
2. **Deploy seller dispatch scorecards:** Focus intervention on the 5.7% of orders missing the shipping limit date and top-volume late sellers.
3. **Preserve funnel acquisition and test weak channels:** Acquired sellers show higher on-time rates (97.3% vs 93.2%) and month-2 retention (+17.9 pp). Paid search converts comparably to organic; evaluate social and email before adjusting spend.

## How to Run
```bash
# 1. Run full pipeline (builds SQLite DB outside OneDrive, executes SQL star schema, runs stats)
python src/run_pipeline.py --raw data/raw --db C:\work\olist.sqlite --out outputs

# 2. Run test suite (synthetic + real data assertions)
pytest

# 3. Launch 6-page Streamlit app
streamlit run app/Home.py
```

## Key Limitations
- **L-001:** Olist public sample; "not observed" selling does not imply "did not sell".
- **L-002:** Coverage gap: only 380 of 842 closed-deal sellers appear in order items.
- **L-009:** Survey timing: 74.5% of late-order reviews were submitted before delivery.
- **L-010:** Observational selection effects: funnel may attract naturally stronger sellers.
- **L-011:** Exploratory channel comparisons lack multiple-testing correction; no cost/CAC data.

## Attribution & License
Dataset: [Olist Brazilian E-Commerce & Marketing Funnel](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) via Kaggle.
License: Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0).
Non-commercial portfolio project.
