# Phase A Audit — Committed Baseline

Audit date: 2026-10-01  
Baseline: branch `week9`, commit `0b4a33a`  
Audit branch: `audit/curriculum-challenge`

## Executive result

The committed baseline does **not currently pass the challenge as a reproducible working application**. The Python environment and OCR models can be prepared successfully, and the 12 committed report-generator tests pass, but a fresh clone cannot run the complete pipeline because the source PDFs are absent. It also cannot run the required web UI because no API/frontend implementation is committed and the committed requirements do not include a web server. This is a measured baseline failure, not an inference; raw run results are in `docs/results/baseline_execution.json`.

The repository contains useful Lab7/Lab8 code and previously generated JSON reports, but those reports cannot substitute for running the committed system against its source files. OCR and Q&A scores therefore remain **unverified** in Phase A until the inputs, databases, application, and independent test sets are supplied.

## Current architecture

- `ocr_final/scr/ocr_system/lab7b_curriculum.py`: local Typhoon OCR followed by Qwen JSON structuring.
- `ocr_final/scr/ocr_system/lab8b_curriculum_db.py`: Pydantic validation, normalized SQLite tables, credit views, seven consistency checks, SQL Q&A, and evaluation command.
- `ocr_final/run_lab8b.py`: orchestrates AI plus DSBA/IT current profiles. It does not contain BIT or B.E. 2560 profiles.
- `ocr_final/curriculum_ocr.py`: separate EasyOCR legacy catalog with FTS5; it is not the active Lab7/Lab8 orchestrator.
- `clean_curriculum_db.py`: absent.
- FastAPI/backend/frontend: absent from the committed repository.

Machine-readable inventory: `docs/results/architecture_inventory.json`.

## Commands actually run

| Check | Result | Evidence |
|---|---|---|
| Install Python 3.11 requirements | passed | `docs/results/baseline_execution.json` |
| Lab7 environment with documented `PYTHONUTF8=1` | passed | Ollama and both models available |
| Unit tests | 12/12 passed | Tests cover report generation only |
| `run_lab8b.py --program all` | failed | `data/input/DSBA.pdf` missing |
| Web application startup | failed | `uvicorn` and the API/frontend module are absent |

## Preliminary rubric scorecard

These are conservative auditable points for the committed baseline. They will be replaced by measured before/after results after independent ground truth and real-browser tests exist.

| Rubric item | Maximum | Baseline estimate | Evidence and reason |
|---|---:|---:|---|
| 1. DB / RAG design | 20 | 11 | Normalized Lab8B schema and aggregate views exist, but version/plan identity, prerequisite foreign keys, version-aware indexes, and demonstrated Thai retrieval are missing. |
| 2. Image reading / OCR | 20 | n/a | Free local Typhoon OCR is configured, but the committed source PDFs are absent, so extraction cannot be rerun. |
| 3. Accuracy / result quality | 20 | n/a | Existing JSON reports claim metrics, but no independent six-version PDF-derived audit set is committed and the run cannot be reproduced. |
| 4. LLM answering | 30 | 0 | No committed web application can be driven; no verified L1–L4 real-UI answers or screenshots exist; no multi-version BIT/2560 data exists. |
| 5. Working app + docs | 10 | 3 | Thai run documentation and generated reports exist, but the documented data is absent and the web app cannot start from the repository. |
| Bonus | +10 cap | 0 | Multiple versions are not committed; real end-to-end hard-question latency is unmeasured. |

The Phase A baseline cannot receive a defensible total out of 100 because Rubric 2 and 3 are unmeasured rather than zero. Counting only demonstrated items gives 14 points; this is **not** a claim that the underlying OCR model scores 0.

## Ranked findings

1. **Rubric 4 and 5 — critical:** no committed API/frontend, so required real-browser evaluation and demo are impossible.
2. **Rubric 3 and reproducibility — critical:** PDFs and databases are absent; current metrics cannot be independently regenerated from a fresh clone.
3. **Rubric 4 / L4 bonus — critical:** BIT and all 2560 profiles are absent; old-vs-new questions cannot be answered from committed data.
4. **Rubric 1 — high:** schema does not identify curriculum version/plan at program level and lacks several integrity/index features.
5. **Rubric 2–4 — high:** no independent PDF-derived six-version ground truth or protected hold-out question set is committed.
6. **Rubric 5 — medium:** `requirements.txt` omits the web stack because the web application itself is absent.
7. **Reliability — medium:** on Windows without `PYTHONUTF8=1`, the readiness check crashes while printing Unicode status symbols; the documented environment setting avoids it.

## Phase A items still required

- Build and manually verify at least 30 PDF rows per program-version across representative pages.
- Run field-level comparison including page correctness, missing/spurious/duplicate rows, and garbled Thai.
- Build expected answers from PDFs before execution and protect a true hold-out subset.
- Drive the real browser UI for L1–L4 questions and save screenshots plus cold/warm timing.
- Re-score every rubric item using those raw results.

No product-code fix has been applied in Phase A. Only audit documentation and evidence files have been added.

## A1 visual review checkpoint

The first A1 batch rendered 36 plan-table pages at 180 DPI and visually inspected all six program-version documents. The render checkpoint is `docs/results/a1_render_checkpoint.json`; source page images are temporary local audit files and can be regenerated.

This pass confirms that the plan pages are suitable for verifying code, Thai/English names, credits/hours, year, semester, plan, and page number. They are **not sufficient** to verify prerequisites, and category/type is not explicit on many rows. The A1 sample must therefore be expanded to course-description and curriculum-structure pages before field accuracy can be calculated honestly.

Visible candidate defects already found include:

- **Rubric 2/3 — BIT-2565 coop, PDF page 35:** one curriculum-table row is fragmented into several OCR candidates and code `96642033` is incorrectly repeated across unrelated fragments (`BIT-2565-coop-12` through `-14`).
- **Rubric 2/3 — DSBA-2560 coop, PDF page 34:** the printed cooperative alternatives `06026130` / `06026131` form one six-credit choice, while the candidate split leaves the second item without credits.
- **Rubric 2/3 — merged/multi-column rows:** specialization and wildcard rows in IT-2560 and BIT require visual grouping; raw row-by-row OCR output cannot be assumed to represent one course per candidate.

These are preliminary findings, not final accuracy percentages. The 180-row JSON remains marked `candidate_only` until the expanded visual review is complete.

### Course-description and prerequisite evidence

The description-page locator was hardened after an exact-code search was found to match course codes cited inside another course's prerequisite. A valid course header now requires an eight-digit code, a credit pattern before the `PREREQUISITE` heading, and no intervening course-code line. This corrected method locates 104 of the 180 sampled rows; it does not claim the other 76 have no description, only that the deterministic header test did not locate one.

The resumable renderer produced or reused 43 corrected description pages. The evidence extractor classifies the 180 samples as 85 explicit `NONE`, 18 explicit prerequisite-code cases, and 77 not-applicable/unlocated (the extra case above the 76 unlocated rows is a combined-code candidate). Representative rendered-page checks for IT-2565 page 326, DSBA-2560 page 183, and BIT-2560 page 174 agree with the extracted prerequisite values.

Raw evidence is stored in `docs/results/a1_description_locator.json`, `docs/results/a1_description_render_checkpoint.json`, and `docs/results/a1_prerequisite_ground_truth.json`. The prerequisite result deliberately records `requires_visual_confirmation: true`; no row becomes independent ground truth until its rendered source is approved.

The field comparator at `ocr_final/scripts/compare_a1_field_accuracy.py` enforces that boundary in code. It scores only rows marked `visually_verified` or `corrected_after_visual_review`, derives lecture/lab/self-study hours from the verified credit pattern, and reports null accuracy when no approved value exists. Its initial result in `docs/results/a1_field_metrics.json` is therefore 0 approved and 180 unapproved rows, not a fabricated accuracy percentage. Three comparator tests raise the repository total to 15 passing tests.

### First approved field batch: prerequisite-bearing rows

The first approved batch contains 18 rows selected specifically because their description pages state a prerequisite code. Each row was checked against both its rendered plan-table page and rendered description page. The raw human-review decisions are in `docs/results/a1_review_batch_prerequisite_rows.json`; the original OCR candidates remain frozen.

| Field | Correct / n | Preliminary accuracy |
|---|---:|---:|
| Course code | 18/18 | 100% |
| Thai name | 13/18 | 72.22% |
| English name | 16/18 | 88.89% |
| Credits and each hour component | 18/18 | 100% |
| Prerequisite | 0/18 | 0% |
| Year / semester / plan / page | 18/18 each | 100% |
| Category / type | 0 reviewed | n/a |

**Rubric 2/3 warning:** these percentages are not overall OCR accuracy. The batch is intentionally prerequisite-heavy and currently covers DSBA-2560 (9), IT-2560 (5), BIT-2560 (3), and IT-2565 (1), with no approved DSBA-2565 or BIT-2565 rows yet. It proves a severe prerequisite extraction gap: all 18 candidates either say `ไม่มี` or return null although the source names a prerequisite code.

**Rubric 2/3 row-integrity finding:** IT-2560 code `06016323` is paired with the following row's Requirement Engineering name in both sampled plans; the correct PDF row is Mobile Device Programming. Three IT-2560 project rows also include the bold specialization heading inside `name_th`. These five corrections explain the Thai-name and English-name failures above. The repository test total is now 17 passing tests.

### Completed DSBA-2560 sample

All 30 DSBA-2560 candidate decisions are now resolved: 29 rows contain scoreable field ground truth and one candidate is a visually confirmed spurious fragment. Category/type remain excluded because the sampled plan rows do not print those labels directly.

| DSBA-2560 field | Correct / n | Accuracy |
|---|---:|---:|
| Course code | 28/29 | 96.55% |
| Thai name | 28/29 | 96.55% |
| English name | 29/29 | 100% |
| Credits | 29/29 | 100% |
| Prerequisite | 10/19 | 52.63% |
| Year / semester / plan / page | 29/29 each | 100% |
| Lecture / lab / self-study hours | 28/28 each | 100% |
| Category / type | 0 reviewed | n/a |

**Rubric 2/3 row-integrity finding:** DSBA-2560 page 34 prints `06026130` or `06026131` as one six-credit cooperative choice. The OCR candidate set splits it into two rows, omits credits from the second fragment, and loses the combined code/Thai label. The audit records one corrected combined row and one spurious candidate rather than pretending both are independent courses. Raw decisions are in `docs/results/a1_review_batch_dsba2560_remaining.json`. The repository test total is now 19 passing tests.
