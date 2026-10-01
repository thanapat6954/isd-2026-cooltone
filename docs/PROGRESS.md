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
- Placeholder codes containing `x`/`X` are elective slots, not real courses: preserve printed code/name/type, never expose synthetic IDs, and exclude slots from misleading old-vs-new course diffs and prerequisite chains.
- Preserve printed alternatives (`A or B` and alternative credit patterns) explicitly, and store/display both PDF page number and printed book page number.
- Table fidelity must be checked per semester against the rendered source: row count, row fields, semester total, program total, placeholder/alternative semantics, and page containment must fail loudly on mismatch.

## 2. CURRENT STATUS

- Phase: **B1 — lossless schema/ingest repair for placeholders, alternatives, and page identity**.
- Done: located the real repository; confirmed it was clean on `week9` at `0b4a33a`; created feature branch `audit/curriculum-challenge`; inventoried the committed architecture in `docs/results/architecture_inventory.json`.
- Done: installed the documented Python 3.11 environment; captured post-setup execution results in `docs/results/baseline_execution.json`; wrote preliminary baseline report `docs/AUDIT_PHASE_A.md`.
- Done: copied all six authoritative PDFs into the gitignored input folder and recorded SHA-256 hashes in `docs/results/pdf_manifest.json`; confirmed embedded Thai text is font-corrupted and unsuitable as ground truth.
- Done: froze all 12 prior OCR candidate outputs under `docs/results/a1_candidates/`; added `ocr_final/scripts/build_a1_review_set.py`; generated `docs/results/a1_ground_truth_review.json` with 180 candidate rows (30 per program-version, split 15 coop/15 no-coop). Every row is explicitly `candidate_only`, not ground truth.
- Done: rendered/reused 36 unique plan pages at 180 DPI; checkpoint is `docs/results/a1_render_checkpoint.json`; visually inspected contact sheets for every program-version.
- Done: hardened the course-description locator so prerequisite references cannot be mistaken for course headers. A header now requires an 8-digit code followed by a credit pattern before `PREREQUISITE`, with no intervening course code. The corrected mapping locates 104/180 samples; 76 are not located.
- Done: rendered/reused 43 unique corrected description pages at 180 DPI; checkpoint is `docs/results/a1_description_render_checkpoint.json`.
- Done: extracted auditable prerequisite evidence for all 180 samples: 85 explicit `NONE`, 18 explicit prerequisite-code cases, and 77 not applicable/unlocated (including one combined-code row). Representative visual checks on IT-2565 page 326, DSBA-2560 page 183, and BIT-2560 page 174 agree with the extracted evidence. Every item still requires its own visual approval before it becomes final ground truth.
- Done: added the field-level A1 comparator and tests. It scores only `visually_verified` or `corrected_after_visual_review` rows, derives lecture/lab/self-study hours from the credit pattern, reports per-field/per-program-version metrics, wrong/missing/duplicate rows, and garbled Thai, and emits null accuracy when `n=0`. Current honest result is 0 approved and 180 unapproved rows; tests pass 15/15.
- Done: visually reviewed the first 18 prerequisite-bearing samples against both plan and description renders. Preliminary, deliberately biased batch metrics: code/credits/year/semester/plan/page/hours 100% (18/18), Thai name 72.22% (13/18), English name 88.89% (16/18), prerequisite 0% (0/18). Found two IT-2560 row-name misalignments and three IT-2560 Thai-name header bleed-ins. Category/type remain unverified and `n=0`. Full tests pass 17/17.
- Done: completed all 30 DSBA-2560 candidate decisions (29 approved field rows plus one spurious fragment). DSBA-2560 code and Thai-name accuracy are 96.55% (28/29); English name and credits are 100% (29/29); prerequisite is 52.63% (10/19 verified values). The cooperative alternatives on page 34 are one combined six-credit row, but OCR emitted two candidates. Tests pass 19/19.
- Done: captured the two UI screenshots and added a read-only live-database inspector. It found 13 deployed databases, 93 synthetic placeholder rows, and missing Thai and English names on all 93. Every database lacks the six required fidelity columns (`is_placeholder`, `raw_code`, `code_pattern`, `elective_type`, `alternative_index`, `printed_page_number`). DSBA-2560 no-coop year 4/2 contains exactly the leaked `ELEC-SLOT-043/044` rows; coop contains only `06026130`, proving `06026131` was dropped from storage rather than merely hidden by the UI.
- Important: substantial version-support work exists in the separate working folder `C:/Users/thana/OneDrive/เอกสาร/ocr_final`; it has not yet been copied into this repository and must not be treated as the Phase A baseline.
- In progress: Phase A placeholder/table-fidelity baseline is committed at `cb99fd1`.
- Reconciled 2026-10-02: the separate live application already has lossless slot/credit-option/page metadata and real UI formatting changes, but those changes were not ported into this feature checkout. All 13 pre-migration backups exist under `C:/Users/thana/OneDrive/เอกสาร/ocr_final/work/backups/2026-10-01-before-placeholder-migration`; their SQLite integrity checks pass. Seven profiles migrated; six are blocked by missing printed placeholder codes/table extraction loss. Passing seven structural checks is not proof of PDF table fidelity.
- In progress: removed the converter's credit-deficit filler rows (invented electives are not source evidence). Replacement loads now stage a new SQLite file, integrity-check it, and preserve the existing DB before replacement. These safeguards need regression tests and a repository checkpoint.
- Latest test run: 28/30 live tests pass; two tests expect the old `AI` display identifier but the rebuilt DB has `AI-coop`. Investigate metadata rather than hiding the mismatch.
- Verified now: 33/33 live tests pass after the Windows connection-cleanup fix and AI metadata assertions; the additional rowspan regression also passes (9/9 focused tests). The inspector now recognizes `is_placeholder` because the new view exposes printed wildcard codes.
- BIT-2560 coop rerun correctly blocked: original structured OCR has no year-4/2 rows (114 vs printed 126 program credits). Visually verified all four year-4/2 rows against PDF page 30 / printed page 25; recorded `docs/results/b1_bit2560_coop_page30_review.json`. A hash-guarded tool creates a separate `reviewed_ingest.json`, leaving the original OCR and frozen evaluation candidates unchanged. Conversion of that curated copy passes fidelity checks (38 courses, 42 stored plan alternatives/rows). This is not evidence of improved OCR accuracy.
- Ported live version-aware API, frontend, schema and orchestrator to this feature checkout; installed API dependencies. Repository tests against deployed DBs and schema selftests pass in `docs/results/b1_verified_2026-10-02.json` (before the new reviewed-term tool tests).
- Completed this session: loaded the reviewed BIT-2560 coop copy with staged replacement and an additional recoverable `.before-load-*.bak`; verification passes 7/7, counted program credits 126. Eight of 13 deployed DBs now have fidelity columns; five remain unmigrated. Repository suite passes **44/44**, schema selftests **30/30**, backup integrity **13/13**. Raw evidence: `docs/results/b1_after_reviewed_import_2026-10-02.json` and `docs/results/b1_bit2560_reviewed_import.json`.
- **NEXT ACTION:** inspect the remaining blocked IT-2560 coop PDF pages 36/40, IT-2565 no-coop pages 36/37, IT-2565 coop pages 43/44, BIT-2565 no-coop pages 29/30, and BIT-2565 coop pages 34/35. Use conversion reports plus actual renders to locate lost/misaligned rows; re-extract or apply separately provenance-reviewed corrections without touching frozen OCR/held-out evaluation inputs. Also split the BIT-2560 coop alternative labels from PDF page 30; storage currently retains both codes but their labels still need independent review. Do not rerun A0 or completed DSBA-2560 review.

## 3. DONE LOG

- 2026-10-02 — Reconciled feature branch/log with pending live changes. Confirmed branch `audit/curriculum-challenge`, latest commit `b529188`, and 13 intact pre-migration backups. Live tests: 28/30; two stale AI display-name assertions need investigation. BIT-2560 PDF page 30 visually contains four year-4/2 rows; raw OCR HTML packs their four codes into one rowspan cell, which current recovery does not understand.
- 2026-10-02 — Removed invented credit-deficit filler slots; made replacement SQLite loading staged, backed up, integrity-checked and connection-safe on exceptions. Added lossless roundtrip/failure tests and explicit rowspan-code recovery. Ported reviewed live API/frontend/version-aware importer into feature checkout, without PDFs, DBs, secrets or frozen-evaluation changes.
- 2026-10-02 — Visually reviewed BIT-2560 coop year 4/2, PDF page 30 / printed page 25. A hash-guarded correction preserves all four actual rows and original OCR. Safe load yields 38 courses / 42 plan rows (including two alternatives); all 7 structural checks pass, counted credits 126. Evidence: `docs/results/b1_bit2560_coop_page30_review.json`, `docs/results/b1_bit2560_reviewed_import.json`.
- 2026-10-02 — Verified repository implementation against deployed databases: 44/44 unit/integration tests and 30/30 schema selftests. Read-only after-state: 8/13 DBs migrated; 5 still blocked; all 13 pre-migration backups pass integrity. New measured results are not an OCR field-accuracy rerun.

- 2026-10-01 — Created `audit/curriculum-challenge` from clean `week9` commit `0b4a33a`; added this initial `docs/PROGRESS.md` handoff file.
- 2026-10-01 — Completed A0 architecture inventory at `docs/results/architecture_inventory.json`: committed baseline has five 2565/current profiles, but no BIT/2560 profiles, API, frontend, PDFs, or SQLite DBs; `clean_curriculum_db.py` is absent.
- 2026-10-01 — Captured fresh-clone environment checkpoint in `docs/results/baseline_environment.json`: repository-local `venv` did not exist; Python 3.11 is available and the documented setup can proceed.
- 2026-10-01 — Installed committed requirements in Python 3.11; Lab7 environment passed with `PYTHONUTF8=1`; tests passed 12/12; full pipeline failed on missing PDF; web start failed because API/frontend and Uvicorn are absent. Raw results: `docs/results/baseline_execution.json`; report: `docs/AUDIT_PHASE_A.md`.
- 2026-10-01 — Staged six local source PDFs (gitignored) and recorded authoritative program/version mapping plus SHA-256 hashes in `docs/results/pdf_manifest.json`; all files copied successfully.
- 2026-10-01 — Added resumable A1 sampling/render tooling and generated 180 stratified candidate rows (30 for each of DSBA-2565, DSBA-2560, IT-2565, IT-2560, BIT-2565, BIT-2560). Candidates remain unverified pending page-image review.
- 2026-10-01 — Rendered and visually inspected 36 early/middle/late plan pages. Found fragmented BIT-2565 page 35 rows and split DSBA-2560 cooperative alternatives; determined prerequisite/category audit needs course-description/structure pages.
- 2026-10-01 — Added description-page locator and mapped 128/180 review samples by exact course code plus `PREREQUISITE` heading; 52 rows need explicit unmatched classification.
- 2026-10-01 — Corrected description-page detection to distinguish true course headers from prerequisite references; final mapping is 104/180. Rendered/reused 43 description pages and extracted prerequisite evidence: 85 explicit-none, 18 code-valued, 77 not-applicable/unlocated. Raw results: `docs/results/a1_description_locator.json`, `docs/results/a1_description_render_checkpoint.json`, and `docs/results/a1_prerequisite_ground_truth.json`.
- 2026-10-01 — Added safe field comparator `ocr_final/scripts/compare_a1_field_accuracy.py` with three audit-specific tests. Initial `docs/results/a1_field_metrics.json` correctly reports 0 approved / 180 unapproved and null metrics instead of self-scoring OCR candidates; full test suite passes 15/15.
- 2026-10-01 — Completed visual review batch `a1-prerequisite-rows-2026-10-01` for 18 plan/description pairs. All 18 OCR candidates omitted or denied a real prerequisite; IT-2560 also has two name-row misalignments and three Thai heading bleed-ins. Raw batch and metrics are in `docs/results/a1_review_batch_prerequisite_rows.json` and `docs/results/a1_field_metrics.json`; 17 tests pass.
- 2026-10-01 — Completed DSBA-2560 review: 29 scored rows and one visually confirmed spurious fragment. The combined cooperative alternative is represented as one ground-truth row; preliminary code/Thai name 96.55%, English/credits 100%, prerequisite 52.63% over 19 verified values. Batch: `docs/results/a1_review_batch_dsba2560_remaining.json`; tests 19/19.
- 2026-10-01 — Added placeholder/elective-slot and table-fidelity requirements from real DSBA-2560 UI evidence to the active audit. Prioritized measuring leaked synthetic IDs, missing slot names, lost alternatives, semester totals, and PDF-vs-printed page citations before Phase B fixes.
- 2026-10-01 — Captured UI screenshots and ran `audit_live_curriculum_dbs.py` read-only against all 13 deployed SQLite files. Baseline: 93/93 synthetic rows lack both Thai and English names; all profiles lack the six new fidelity columns; DSBA-2560 coop storage contains only `06026130` while no-coop exposes two unnamed synthetic rows. Raw evidence: `docs/results/placeholder_table_fidelity_baseline.json` and `docs/results/screenshots/`.

## 4. FINDINGS AND PROBLEMS

1. **Rubric 5 / working app — open, critical.** The committed baseline contains no API or frontend files, so the required real-web-UI audit cannot run from the repository. Evidence: `docs/results/architecture_inventory.json`. Fix commit: n/a.
2. **Rubric 4 + L4 bonus / versions — open, critical.** The committed orchestrator supports only AI plus DSBA/IT current profiles; BIT and every 2560 profile are absent, and the schema has no version metadata. Evidence: `ocr_final/run_lab8b.py`, `ocr_final/scr/ocr_system/lab8b_curriculum_db.py`, inventory JSON. Fix commit: n/a.
3. **Rubric 2–3 / reproducibility — open, critical.** PDFs and `curriculum.db` files are not committed, so the documented `--program all` command cannot reproduce current reports from a fresh clone. Evidence: inventory JSON. Fix commit: n/a.
4. **Rubric 1 / DB design — open.** Lab8B has normalized tables and useful credit views, but `prerequisite` lacks declared foreign keys, only two plan indexes exist, version/plan metadata is missing, and the default legacy FTS5 tokenizer is unsuitable evidence for Thai word retrieval. Evidence: committed DDL. Fix commit: n/a.
5. **Potential source/repo divergence / all rubric items — open.** A separate working folder contains newer implementation and results; the Git baseline must be measured before selected changes are ported. Fix commit: n/a.
6. **Reliability / Rubric 5 — open.** Lab7 readiness crashes under Windows cp874 unless `PYTHONUTF8=1` is set; the documented setting is an effective workaround. Evidence: `docs/results/baseline_execution.json`. Fix commit: n/a.
7. **Rubric 2–3 / row integrity — open, verified visually.** BIT-2565 coop page 35 contains fragmented OCR rows with repeated `96642033`; DSBA-2560 coop page 34 splits a six-credit alternative and leaves one candidate without credits. Evidence: rendered source pages and sample IDs recorded in `docs/AUDIT_PHASE_A.md`. Fix commit: n/a.
8. **Rubric 2–3 / prerequisite coverage — open.** Current Lab7 profiles OCR only plan-table page ranges, which do not contain prerequisite fields; a zero/`ไม่มี` value cannot be treated as verified. Evidence: 36-page visual pass. Fix commit: n/a.
9. **Rubric 2–3 / PDF text matching — fixed in audit tooling, visually spot-checked.** A raw exact-code search confused codes cited as prerequisites with course headers (for example IT `06066302` and DSBA `90401013`). Header detection now requires credits before the course's prerequisite heading and rejects an intervening course code. Evidence: corrected locator and prerequisite JSON; product fix commit: n/a (audit tooling only).
10. **Rubric 2–3 / prerequisite accuracy — open, critical, visually verified on biased slice.** Every one of the first 18 prerequisite-bearing samples is wrong in the OCR candidate (0/18): candidates say `ไม่มี` or null while the PDF names a prerequisite code. This is not an overall rate because the batch intentionally selected prerequisite-bearing rows. Evidence: `docs/results/a1_review_batch_prerequisite_rows.json` and field metrics. Fix commit: n/a.
11. **Rubric 2–3 / IT-2560 row alignment — open, high.** Code `06016323` is paired with the next row's Requirement Engineering name in both sampled plans; three project rows include the specialization heading inside the Thai course name. Evidence: IT-60 plan pages 30/33/37 and description pages 233/236/242/247. Fix commit: n/a.
12. **Rubric 2–3 / DSBA-2560 alternative grouping — open, verified.** PDF page 34 prints `06026130` or `06026131` as one six-credit choice; OCR creates two candidates, leaves the second without credits, and fails to preserve the combined code/Thai label. In the 30-row sample this yields one wrong grouped row plus one spurious fragment. Evidence: `docs/results/a1_review_batch_dsba2560_remaining.json`. Fix commit: n/a.
13. **Rubric 1–4 / placeholder slots and UI fidelity — open, critical.** The real UI exposes `ELEC-SLOT-043/044` with no names although DSBA-60 PDF page 29 / printed page 24 names Free Elective Course 2 and Elective Course in Humanity 2. This is a schema/ingest plus answer-formatting failure, not missing source data. Evidence: user UI screenshot and rendered plan page. Fix commit: n/a.
14. **Rubric 4 / citation fidelity — open, high.** The real UI shows only PDF page 34 and a raw key/value snippet; the cited page is printed as page 29 inside the book. Both page numbers and a clean source summary are required. Evidence: user UI screenshot. Fix commit: n/a.
15. **Rubric 1–4 / deployed placeholder coverage — open, critical, measured.** Across 13 live databases, all 93 synthetic `ELEC-*` rows have null Thai and English names. The deployed `plan_item` schema has none of the required placeholder, raw-code, alternative-index, or printed-page columns. Evidence: `docs/results/placeholder_table_fidelity_baseline.json`. Fix commit: n/a.

## 5. DECISIONS AND REASONS

- Use a new branch from `week9` so audit tooling and later fixes cannot affect `main` and the existing submitted branch remains recoverable.
- Treat the committed repository as the Phase A baseline. The separate `ocr_final` working folder is evidence/reference only until specific changes are reviewed and intentionally ported.
- Store raw machine-readable evidence under `docs/results/` and screenshots under `docs/results/screenshots/`; reports will reference those paths.
- Do not invent a `clean_curriculum_db.py`; record its absence and use the actual active Lab7/Lab8 pipeline.
- Treat PDF text extraction as an evidence locator, not ground truth by itself. Only a course-header-shaped match is accepted, and all extracted values retain `requires_visual_confirmation: true` until reviewed against rendered pages.
- Model placeholders as typed curriculum slots with their printed wildcard code and names; synthetic database identifiers are internal implementation details and must never be answer text.
- Model alternatives as grouped choices rather than duplicate independent courses or merged text; credit totals count the group once.
- Capture product defects through read-only SQLite inspection before migrations. This separates storage loss from answer-formatting bugs and provides exact before/after counts.
- Never repair credit deficits by creating unnamed electives: preserved printed totals are blockers, not a license to invent rows. Manually verified table repairs go into separate hash-guarded ingest copies; original OCR stays the evaluation input.
- Windows SQLite connections must close in `finally`, including failed staged loads. A transaction context manager alone does not close the handle.

## 6. HOW TO RERUN

Repository and branch:

```powershell
Set-Location 'C:\Users\thana\OneDrive\เอกสาร\isd-2026-cooltone'
git switch audit/curriculum-challenge
git status --short
```

Current known application commands (must be verified during A0 before relying on them):

```powershell
.\ocr_final\venv\Scripts\python.exe -m unittest discover -s ocr_final\tests -v
$env:PYTHONUTF8 = "1"
.\ocr_final\venv\Scripts\python.exe .\ocr_final\scr\ocr_system\lab7b_curriculum.py --check
.\ocr_final\venv\Scripts\python.exe .\ocr_final\run_lab8b.py --program all
.\ocr_final\venv\Scripts\python.exe .\ocr_final\scripts\locate_a1_description_pages.py
.\ocr_final\venv\Scripts\python.exe .\ocr_final\scripts\render_a1_description_pages.py
.\ocr_final\venv\Scripts\python.exe .\ocr_final\scripts\extract_a1_prerequisites.py
.\ocr_final\venv\Scripts\python.exe .\ocr_final\scripts\apply_a1_review_batch.py .\docs\results\a1_review_batch_prerequisite_rows.json
.\ocr_final\venv\Scripts\python.exe .\ocr_final\scripts\compare_a1_field_accuracy.py
.\ocr_final\venv\Scripts\python.exe .\ocr_final\scripts\audit_live_curriculum_dbs.py --app-root 'C:\Users\thana\OneDrive\เอกสาร\ocr_final' --output .\docs\results\placeholder_table_fidelity_baseline.json
```

- Expected generated database paths: `ocr_final/work/lab8b_<profile>/curriculum.db`; none are committed at the baseline.
- Backup path: live `work/backups/2026-10-01-before-placeholder-migration` (13 databases, integrity checked); backups are not committed.
- The committed baseline has no runnable web command. OCR/ingest exists as above; evaluation, UI automation, and latency commands require A1/A3 audit tooling.

Current feature implementation verification (not the historical baseline):

```powershell
$env:PYTHONUTF8 = '1'
.\ocr_final\venv\Scripts\python.exe -m pip install -r .\ocr_final\requirements.txt
.\ocr_final\venv\Scripts\python.exe .\ocr_final\scripts\capture_b1_checkpoint.py --app-root 'C:\Users\thana\OneDrive\เอกสาร\ocr_final' --output .\docs\results\b1_resume_checkpoint.json
# Start the feature API against generated live DBs without copying DBs into Git:
$env:CURRICULUM_DATABASE_ROOT = 'C:\Users\thana\OneDrive\เอกสาร\ocr_final'
Set-Location .\ocr_final
.\venv\Scripts\python.exe -m uvicorn lab10_fastapi.curriculum_app.main:app --host 127.0.0.1 --port 8001
# Separate terminal from ocr_final: serve frontend (if 5500 is free)
.\venv\Scripts\python.exe -m http.server 5500 --directory frontend
```

The existing live frontend uses API port 8000. Port 8001 above is an isolated verification instance; do not stop a user's running server. For normal use start the feature API on 8000 when that port is free.

Recreate the reviewed BIT ingest without changing OCR (from repository root):

```powershell
$liveApp = 'C:\Users\thana\OneDrive\เอกสาร\ocr_final'
.\ocr_final\venv\Scripts\python.exe .\ocr_final\scripts\apply_reviewed_plan_term.py --input "$liveApp\work\lab8b_bit_2560_coop\lab7b\pred_vlm.json" --review .\docs\results\b1_bit2560_coop_page30_review.json --pdf "$liveApp\data\input\BIT-60.pdf" --output "$liveApp\work\lab8b_bit_2560_coop\lab7b\reviewed_ingest.json"
```

Exact subsequent import/load/verify arguments and raw output are saved in `docs/results/b1_bit2560_reviewed_import.json`. The default orchestrator still reads original OCR and intentionally rejects its missing semester; do not mistake that for loss of the reviewed repair. Source hash checks require review again if the PDF or OCR changes.

## 7. OPEN QUESTIONS / THINGS NOT VERIFIED

- `clean_curriculum_db.py` was not found anywhere in the repository; whether an instructor expected a separate script remains unknown.
- No committed database files exist; the JSON reports cannot by themselves prove a fresh-clone run.
- The committed app does not include the version-aware FastAPI/frontend implementation shown in the separate working folder.
- Independent PDF-derived ground truth for at least 30 rows per program-version has not been completed; the 180 candidates and prerequisite evidence remain unapproved until per-row visual review.
- PDF embedded Thai text is visibly/font-encoding corrupted; it cannot be used as a shortcut for Thai-name ground truth. Visual renders are required.
- The 180-row review file is not yet valid ground truth; no OCR accuracy claim may use it until all rows have a visual-review status and populated ground-truth fields.
- Real-browser L1–L4 evaluation, cold/warm latency, citation accuracy, and hold-out performance are not yet measured.
- Full semester-by-semester visual table-fidelity review, printed-page mapping, and ingest-time total/row-count checks are not yet implemented.
- Five live profiles still use pre-migration schemas because source-fidelity checks blocked replacement. Full per-semester visual review and all Phase A field/UI/latency measurements remain incomplete.
- The BIT-2560 coop manual table correction is curated ingest data, not a model improvement; its prerequisite/category/type fields remain unknown. No new OCR accuracy or held-out answer score was claimed.
