# 08. WP5: Pre-flight, GitHub repo, Streamlit Cloud deploy
**Written:** 2026-10-16 (Claude) | **Applies to commit:** 7a46403 (page 6 Action Plan, executive memo) | **Replaces:** the one-line WP5 entry in `07_PROGRESS_REPORT.md` section 7.
**Read order for Antigravity:** `AGENTS.md` -> this file -> `docs/decision_log.md` (tail) -> `README.md`.

## 0. State at hand-over (from the saved files, not from a run)
- Phases A-C are built and committed (8 local commits, last 7a46403). The app has Home + 6 pages. `docs/findings.md`, `docs/executive_memo.md`, robustness tables, README and screenshots (5) exist.
- **No git remote exists** (`.git/config` has none). Nothing has been pushed. This is the last cheap moment to decide whether to rewrite history (see Part B, step 0).
- The app reads only from `outputs/` and `sql/` (SQL shown in expanders) and `docs/erd.png`. `data/raw/` and `*.sqlite` are git-ignored, so the cloud build needs neither.
- Not verified by Claude: current `git status`, the latest `pytest` result (progress report says 53 tests, 19 on real data), pages 1-3.

## 1. What is left (in order)
| # | Owner | Task | Size |
|---|---|---|---|
| A | AG | Pre-flight fixes + clean-clone rehearsal (Part A) | 30-60 min |
| B | YOU | Create the GitHub repo and push (Part B) | 10 min |
| C | YOU | Deploy on Streamlit Community Cloud (Part C) | 10 min |
| D | AG | Post-deploy check, README URL, page-6 screenshot (Part D) | 20 min |
| E | Claude | WP6 resume bullets from verified numbers | 15 min |
| Opt | decide | Reviews page and what-if slider (Part F) | 1-2 h |

## Part A. Pre-flight (Antigravity). Do NOT change any analysis definition, SQL or output file.
1. **Streamlit config location.** Streamlit reads `.streamlit/config.toml` from the folder it is launched from. Cloud and the README both launch `streamlit run app/Home.py` from the repo root, so `app/.streamlit/config.toml` is not picked up. Move it to `<root>/.streamlit/config.toml` (`git mv`). Check the orange theme appears when launched from the root.
2. **Case-sensitivity.** Cloud runs Linux; Windows git here has `core.ignorecase = true`. List `git ls-files` and check that every file name the app, `src/` and `sql/` open (e.g. `app_orders.csv.gz`, `stat_*.csv`, `robustness_*.csv`, `docs/erd.png`, `01_load_clean.sql`) matches the committed name exactly, character for character. Fix the code side, not the file side.
3. **Hard-coded paths.** Search `app/` and the files it imports (`src/stats.py`, `src/simulator.py`) for `C:`, backslashes and `OneDrive`. There must be none (tests and `run_pipeline.py` may keep `C:\work`).
4. **What gets pushed.** Paste: `git status --short`; `git ls-files | findstr /i "raw sqlite .env"` (must print nothing); the 10 largest tracked files with sizes; total size of tracked files. Expected: well under 50 MB, `outputs/app_orders.csv.gz` about 6.6 MB the largest.
5. **Docs hygiene.**
   - `docs/decision_log.md` has two entries numbered D-031 (simulator range, and Streamlit `width="stretch"`). Renumber the second to D-032 and fix any reference.
   - `docs/07_PROGRESS_REPORT.md` section 1 still says "5-page app (Home + pages 1-5)". Update it to Home + 6 pages (Action Plan, commit 7a46403) and the real remaining work (this file). Fix the "pages 1-5" docstring in `app/Home.py`.
   - Take the missing screenshot `screenshots/06_action_plan.png` and add it to the README.
6. **README.** Add at the top, under the title: a "Live app" line with the placeholder `LIVE_URL_PENDING` (Part D fills it) and a **Quick start (no raw data needed)**: `pip install -r requirements.txt` then `streamlit run app/Home.py` (the app runs from the committed `outputs/`). Keep "How to run" for the full rebuild and say it needs the Kaggle CSVs in `data/raw/`.
7. **LICENSE.** Add `LICENSE` (MIT, copyright holder = the git user name) covering the code, and one README sentence: derived data in `outputs/` comes from the Olist datasets under CC BY-NC-SA 4.0; non-commercial portfolio use; attribution to Olist. Do not remove the existing attribution.
8. **Empty-filter smoke test** (spec item from WP4 that is still open). Add one test to `tests/test_app_smoke.py` that sets an empty-result filter (a month and a state with no orders, via `at.session_state`) and asserts no exception on pages 1 and 4. If an exception appears, fix the page with `empty_state_guard`; do not skip the test.
9. **Clean-clone rehearsal** (this simulates the cloud build). PowerShell:
   ```
   cd C:\work
   Remove-Item -Recurse -Force .\rehearsal -ErrorAction SilentlyContinue
   git clone C:\Users\amit0\OneDrive\Desktop\EcommerceRCA rehearsal
   cd rehearsal
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   $env:OLIST_DB="C:\no\such.sqlite"
   pytest
   streamlit run app/Home.py
   ```
   Paste the full `pytest` output (skips must each state a reason; zero failures). Open all 6 pages; confirm no red exception box, theme loads, sidebar filters work, the "Show SQL" expander prints SQL, and the Data Trust page shows the ERD. Then `Remove-Item Env:OLIST_DB`.
10. Commit on top (do not amend): `chore: deploy pre-flight (config location, license, README quick start, empty-filter test)`. Paste `git log --oneline -3` and `git status --short` (must be clean).
**Report back:** items 1-10 each with the pasted evidence; anything not done and why. Then STOP.

## Part B. GitHub repo (YOU)
0. **Optional, before the first push only.** Commit history contains your gmail address and, in some messages, a `Claude-Session` URL and a `Co-Authored-By` line. A public repo shows all of it. If you mind, either leave history as is (simplest) or ask AG for a one-time squash into a single commit with your GitHub no-reply address (`git config user.email "<id>+<username>@users.noreply.github.com"`). After the push, never rewrite history.
1. github.com -> New repository. Name: `olist-seller-delivery-diagnostics`. **Public.** Do NOT tick "Add a README", ".gitignore" or "license" (the repo already has them; ticking creates a conflicting first commit). Description: "Olist marketplace analytics: seller acquisition funnel, delivery RCA, Streamlit app (SQL star schema, tests)."
2. PowerShell in `C:\Users\amit0\OneDrive\Desktop\EcommerceRCA`:
   ```
   git status
   git remote add origin https://github.com/<your-username>/olist-seller-delivery-diagnostics.git
   git branch -M main
   git push -u origin main
   ```
   `git status` must say "nothing to commit, working tree clean" first. A browser sign-in window from Git Credential Manager is normal.
3. Refresh the repo page and check: README renders with screenshots; `outputs/`, `sql/`, `app/`, `docs/` present; **no `data/raw`, no `.sqlite`**. Add topics (streamlit, sql, data-analysis, ecommerce, sqlite).
Note: the project folder sits in OneDrive. Git works there, but if OneDrive reports a sync conflict on `.git`, pause sync before pushing.

## Part C. Streamlit Community Cloud (YOU)
1. share.streamlit.io -> sign in with GitHub, allow access to the repo.
2. Create app -> "Deploy a public app from GitHub". Repository: `<you>/olist-seller-delivery-diagnostics`. Branch: `main`. **Main file path: `app/Home.py`.**
3. Advanced settings: **Python 3.12** (matches the machine where the tests passed). No secrets needed.
4. Pick a short app URL, click Deploy. First build takes a few minutes. A failure shows in the log pane on the right: copy the full log to Claude.
5. Later pushes to `main` redeploy automatically. Free apps go to sleep after a period of inactivity; open the link yourself shortly before an interview or before sending it to a recruiter.

## Part D. Post-deploy (YOU open, AG edits)
Open the live URL and check these against `outputs/analysis_summary.json` and the README: 96,203 delivered orders; late rate 6.79%; lead-to-deal 10.52%; adjusted OR 4.16 (CI 3.70-4.66); 380 of 842 deal sellers in order data. All 6 pages load, filters reset works, no exception boxes, mobile width readable. Then AG replaces `LIVE_URL_PENDING` in README with the URL (and in `docs/07_PROGRESS_REPORT.md`), commits, pushes, and the app redeploys.

## Part E. WP6 (Claude)
3-5 resume bullets using only numbers quoted in `docs/findings.md` and present in the live app. Retired values (4.38, 199, 132/197, 62% at dispatch) never appear.

## Part F. Optional scope gap (decide after the deploy)
`docs/04_STREAMLIT_SPEC.md` asked for a Reviews RCA page (delay-band chart, Mann-Whitney effect size, the survey-timing split beside the crude gap) and a What-If simulator with sliders. The built app has no dedicated page for either (Claude has not opened pages 1-3, so part of this may sit on the Executive Summary). The review question is in the original brief, so a page 7 "Reviews & What-If" is the one addition that closes a real hole. It only reads existing `stat_review_band.csv`, `out_review_timing.csv`, `stat_simulator.csv` and `src/simulator.py`. Do it after the first deploy; pushing it redeploys the app.

## Pitfalls
| Pitfall | Guard |
|---|---|
| Theme missing on cloud | Part A step 1 |
| Works on Windows, fails on Linux (file-name case) | Part A step 2 |
| Cloud picks a different Python | set 3.12 in Advanced settings |
| README repo ticked on GitHub, push rejected | create the repo empty |
| Raw data or database pushed | Part A step 4 and Part B step 3 |
| App asleep when a recruiter opens it | open it yourself first |
| Numbers on cloud differ from local | cannot happen if only `outputs/` is read; if it does, stop and report |

## Antigravity prompt (paste)
```
You are the implementation agent (Antigravity) in a Claude (architect) / Antigravity (executor) workflow.
Read AGENTS.md, then docs/08_WP5_DEPLOY.md, then the tail of docs/decision_log.md.
Execute Part A of docs/08_WP5_DEPLOY.md ONLY (items 1 to 10). Do not change analysis definitions, SQL, outputs/ files or existing tests (you may ADD the one empty-filter test). Do not push to GitHub and do not create a remote; the owner does Parts B and C.
If a test fails, paste the full pytest output; never skip, loosen or delete a test to get green.
Finish with the report listed under Part A, real output pasted, then STOP and wait for Claude's verdict.
```
