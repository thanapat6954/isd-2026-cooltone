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
