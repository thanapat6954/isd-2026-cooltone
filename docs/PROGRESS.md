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

- Phase: **A0 — repository and architecture discovery**.
- Done: located the real repository; confirmed it was clean on `week9` at `0b4a33a`; created feature branch `audit/curriculum-challenge`.
- In progress: documenting the current OCR, database, API, frontend, schema, and run commands before any product-code change.
- Important: substantial version-support work exists in the separate working folder `C:/Users/thana/OneDrive/เอกสาร/ocr_final`; it has not yet been copied into this repository and must not be treated as the Phase A baseline.
- **NEXT ACTION:** inspect `curriculum_ocr.py`, locate or confirm the absence of `clean_curriculum_db.py`, inspect schema/database creation code, API, frontend, existing tests, and the current committed data/work artifacts; record the baseline architecture and gaps here.

## 3. DONE LOG

- 2026-10-01 — Created `audit/curriculum-challenge` from clean `week9` commit `0b4a33a`; added this initial `docs/PROGRESS.md` handoff file.

## 4. FINDINGS AND PROBLEMS

1. **Process integrity / all rubric items — open.** The audit has not yet established a committed baseline by actually running the repository version. Evidence pending. Fix commit: n/a.
2. **Potential source/repo divergence / all rubric items — open.** A separate working folder contains newer uncommitted implementation and result files; the Git repository must be audited independently before deciding what to port. Evidence: repository path and clean status above. Fix commit: n/a.

## 5. DECISIONS AND REASONS

- Use a new branch from `week9` so audit tooling and later fixes cannot affect `main` and the existing submitted branch remains recoverable.
- Treat the committed repository as the Phase A baseline. The separate `ocr_final` working folder is evidence/reference only until specific changes are reviewed and intentionally ported.
- Store raw machine-readable evidence under `docs/results/` and screenshots under `docs/results/screenshots/`; reports will reference those paths.

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

- Database path(s): pending A0 discovery.
- Backup path(s): not created yet; required before Phase B.
- OCR/ingest, evaluation, UI automation, and latency commands: pending A0 discovery and audit-tool implementation.

## 7. OPEN QUESTIONS / THINGS NOT VERIFIED

- Whether `clean_curriculum_db.py` exists under another name or is absent.
- Which committed database files are authoritative and whether they include all 12 program/version/plan profiles.
- Whether the committed app currently exposes the version-aware frontend shown in the separate working folder.
- Independent PDF-derived ground truth for at least 30 rows per program-version has not been created.
- Real-browser L1–L4 evaluation, cold/warm latency, citation accuracy, and hold-out performance are not yet measured.
- No database backup has been created yet because Phase B has not started.
