# Curriculum OCR Audit — Progress and Handoff

## 1. GOAL AND RULES

- Audit the real DSBA, IT, and BIT OCR + RAG system against the P2 rubric, fix failures, and re-measure with reproducible evidence.
- Rubric: DB/RAG 20, OCR 20, measured accuracy 20, LLM answers with correct page/section citations 30, working app/docs 10; bonus is capped at +10.
- Accuracy thresholds are strict: above 91% = full band, 80–90% = partial band, below 80% = low band.
- Work only on `audit/curriculum-challenge`; never commit or push to `main`.
- Phase A changes are limited to audit/test tooling. Product fixes begin only after the Phase A baseline is recorded.
- Before Phase B, make and verify a recoverable backup of every database that may be changed; never delete curriculum source data.
- Preserve the existing `POST /api/ask` request and response field names and existing correct behavior.
- Never hard-code answers to evaluation questions. Keep the hold-out set untouched during fixes and report it separately.
- Every result claim must link to raw JSON/CSV/screenshots or an inspected PDF page. Unknown or unmeasured values remain `n/a`.

## 2. CURRENT STATUS

- Phase: **A0 — baseline execution and evidence capture**.
- Done: located the real repository; confirmed it was clean on `week9` at `0b4a33a`; created feature branch `audit/curriculum-challenge`; inventoried the committed architecture in `docs/results/architecture_inventory.json`.
- In progress: creating the documented Python 3.11 `venv` and installing committed requirements. The first command attempts failed because a fresh clone has no local environment; this is recorded in `docs/results/baseline_environment.json` and is not yet counted as a product defect.
- Important: substantial version-support work exists in the separate working folder `C:/Users/thana/OneDrive/เอกสาร/ocr_final`; it has not yet been copied into this repository and must not be treated as the Phase A baseline.
- **NEXT ACTION:** run `py -3.11 -m venv venv`, install `ocr_final/requirements.txt`, then rerun tests, Lab 7 readiness, `run_lab8b.py --program all`, and web startup; save the post-setup results under `docs/results/`.

## 3. DONE LOG

- 2026-10-01 — Created `audit/curriculum-challenge` from clean `week9` commit `0b4a33a`; added this initial `docs/PROGRESS.md` handoff file.
- 2026-10-01 — Completed A0 architecture inventory at `docs/results/architecture_inventory.json`: committed baseline has five 2565/current profiles, but no BIT/2560 profiles, API, frontend, PDFs, or SQLite DBs; `clean_curriculum_db.py` is absent.
- 2026-10-01 — Captured fresh-clone environment checkpoint in `docs/results/baseline_environment.json`: repository-local `venv` did not exist; Python 3.11 is available and the documented setup can proceed.

## 4. FINDINGS AND PROBLEMS

1. **Rubric 5 / working app — open, critical.** The committed baseline contains no API or frontend files, so the required real-web-UI audit cannot run from the repository. Evidence: `docs/results/architecture_inventory.json`. Fix commit: n/a.
2. **Rubric 4 + L4 bonus / versions — open, critical.** The committed orchestrator supports only AI plus DSBA/IT current profiles; BIT and every 2560 profile are absent, and the schema has no version metadata. Evidence: `ocr_final/run_lab8b.py`, `ocr_final/scr/ocr_system/lab8b_curriculum_db.py`, inventory JSON. Fix commit: n/a.
3. **Rubric 2–3 / reproducibility — open, critical.** PDFs and `curriculum.db` files are not committed, so the documented `--program all` command cannot reproduce current reports from a fresh clone. Evidence: inventory JSON. Fix commit: n/a.
4. **Rubric 1 / DB design — open.** Lab8B has normalized tables and useful credit views, but `prerequisite` lacks declared foreign keys, only two plan indexes exist, version/plan metadata is missing, and the default legacy FTS5 tokenizer is unsuitable evidence for Thai word retrieval. Evidence: committed DDL. Fix commit: n/a.
5. **Potential source/repo divergence / all rubric items — open.** A separate working folder contains newer implementation and results; the Git baseline must be measured before selected changes are ported. Fix commit: n/a.

## 5. DECISIONS AND REASONS

- Use a new branch from `week9` so audit tooling and later fixes cannot affect `main` and the existing submitted branch remains recoverable.
- Treat the committed repository as the Phase A baseline. The separate `ocr_final` working folder is evidence/reference only until specific changes are reviewed and intentionally ported.
- Store raw machine-readable evidence under `docs/results/` and screenshots under `docs/results/screenshots/`; reports will reference those paths.
- Do not invent a `clean_curriculum_db.py`; record its absence and use the actual active Lab7/Lab8 pipeline.

## 6. HOW TO RERUN

Repository and branch:

```powershell
Set-Location 'C:\Users\thana\OneDrive\เอกสาร\isd-2026-cooltone'
git switch audit/curriculum-challenge
git status --short
```

Current known application commands (must be verified during A0 before relying on them):

```powershell
.\venv\Scripts\python.exe -m uvicorn lab10_fastapi.curriculum_app.main:app --host 127.0.0.1 --port 8000
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

- Expected generated database paths: `ocr_final/work/lab8b_<profile>/curriculum.db`; none are committed at the baseline.
- Backup path(s): not created yet; required before Phase B.
- OCR/ingest, evaluation, UI automation, and latency commands: pending A0 discovery and audit-tool implementation.

## 7. OPEN QUESTIONS / THINGS NOT VERIFIED

- `clean_curriculum_db.py` was not found anywhere in the repository; whether an instructor expected a separate script remains unknown.
- No committed database files exist; the JSON reports cannot by themselves prove a fresh-clone run.
- The committed app does not include the version-aware FastAPI/frontend implementation shown in the separate working folder.
- Independent PDF-derived ground truth for at least 30 rows per program-version has not been created.
- Real-browser L1–L4 evaluation, cold/warm latency, citation accuracy, and hold-out performance are not yet measured.
- No database backup has been created yet because Phase B has not started.
