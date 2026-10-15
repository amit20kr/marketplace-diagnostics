# 05. Agent Playbook (Claude <-> Antigravity)

## Stack & Runtime
SQLite (Python stdlib `sqlite3`) for SQL transformations; Streamlit app reads CSV / `.csv.gz` / JSON from `outputs/` only (D-001, D-015). No DuckDB and no parquet. The SQLite database is kept outside OneDrive (e.g. `C:\work\olist.sqlite`).

## Loop
Claude plans ONE phase -> Antigravity executes -> Phase Report -> Claude verdict (APPROVE / REQUEST FIXES / REVISE PLAN) -> next phase. Antigravity never starts the next phase without a verdict.

## Rules for Antigravity
1. Work only on the one work package named in the task (WP list: `docs/07_PROGRESS_REPORT.md` section 7; status: `docs/02_ROADMAP.md`). Start from `AGENTS.md`. Tick roadmap tasks only when finished and verified.
2. Never edit files in `data/raw/`. Raw folder names contain spaces: `data/raw/EcommercePub dataset/` and `data/raw/Marketing funnel/`.
3. Every number in any report must come from a saved SQL file or script in the repo.
4. Count distinct keys at the right grain. Never sum joined rows.
5. Log every assumption, cleaning rule and rejected approach in `docs/decision_log.md`.
6. If results contradict a hypothesis, report the contradiction; do not tune the analysis to fit.
7. Keep it simple. Do not add models, libraries or features not in the spec.
8. Paste actual tables and numbers in reports, not just file names.

## Phase Report template
```
PHASE: <letter>   STATUS: complete / partial / blocked
1. What was built (files, tables, queries)
2. Key numbers (with row counts / n)
3. Data issues found and decisions made (link to decision_log entries)
4. Checks run and results
5. Surprises / results that contradict hypotheses
6. Open questions for Claude
7. Files created + commit hash
```

## Claude review checklist
Correctness | business validity | double counting / grain | SQL correctness | statistical validity | reproducibility | resume value | interview defensibility.
