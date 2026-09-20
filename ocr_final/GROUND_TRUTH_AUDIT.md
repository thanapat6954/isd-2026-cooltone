# Ground-truth audit

Audit date: 2026-09-20

## Scope and source policy

The academic-plan tables were checked against the project PDFs, using visual page renders and extracted text. The canonical input files are `data/input/DSBA.pdf`, `data/input/AI.pdf`, and `data/input/IT.pdf`. A separate local copy of `IT.pdf` has a different SHA-256 hash and one extra physical page, so it is no longer used by `run_lab8b.py`.

The workbook named in several JSON `source` fields (`GT_Template-2.xlsx`) was not present in the checked project files. Therefore, claims that require that workbook are marked "source unavailable" rather than treated as verified.

## File-by-file result

| File | Result | Evidence / discrepancy |
|---|---|---|
| `DSBA_ground_truth.json` | Verified and corrected | Both plans total 132. Years 1-3 contain the same 39 academic-plan rows. Coop term totals are 18, 21, 18, 21, 18, 18, 12, 6. No-coop totals are 18, 21, 18, 21, 18, 18, 9, 9. Cooperative education is coop-only. Wildcard slots now carry their own printed labels and credits instead of inheriting the first pool course. |
| `DSBA_academic_plan_coop.json` | Verified derived file | Regenerated from the normalized DSBA source. Contains 44 plan rows and no spreadsheet instruction row. |
| `DSBA_academic_plan_no_coop.json` | Verified derived file | Generated from the normalized DSBA source. Contains 45 plan rows. Years 1-3 are identical to coop after excluding plan-specific page citations. |
| `AIT_academic_plan.json` | Structurally clean; plan totals verified | Removed one spreadsheet instruction row and normalized the first year/semester to integers. Printed term totals sum to 120. All 49 unique numeric course codes occur in `AI.pdf`. The current OCR alignment is 37/41 matched (F1 0.9136); see discrepancy list below. |
| `IT_academic_plan_coop.json` | Structurally clean; plan totals verified | Removed one spreadsheet instruction row and normalized the first year/semester to integers. Effective printed total is 129 after treating the three specialization columns as alternatives. All 98 unique numeric course codes occur in `IT.pdf`. The source PDF itself repeats code `06016418` under a second specialization heading; the GT preserves that printed anomaly and Lab 8B deduplicates the plan row. |
| `IT_academic_plan_no_coop.json` | Structurally clean; plan totals verified | Same cleanup and source-code coverage as IT coop. Effective printed total is 129. The coop-only `06016481/06016482` catalogue description is retained in the course catalogue but excluded from the no-coop plan. |
| `general_education_ground_truth.json` | Valid JSON; source unavailable for full audit | 266 rows, 266 unique numeric codes, and no missing name/credit fields. Only 9 codes appear in the three curriculum PDFs because those books print only the courses used by these plans, not the full general-education catalogue. The remaining 257 rows cannot be line-by-line verified without `GT_Template-2.xlsx` or the official general-education catalogue. |
| `rules_ground_truth.json` | Shape verified; partially source-verified | Contains 16 categories for each of IT, DSBA, BIT, and AIT. Programme totals 129/132/120 agree with the available IT/DSBA/AI PDFs. BIT and the remaining detailed rule fields cannot be fully verified because the BIT PDF and source workbook are absent. |
| `extracted_curriculum.json` | Invalid and archived | It claimed to be DSBA no-coop but contained five `012...` rows, only 12 credits, missing names/credits, and no correspondence to the DSBA academic plan. Moved to `work/_archive_candidates_2026-09-20/invalid_sources_2026-09-20/extracted_curriculum.json`. |

## OCR-to-ground-truth discrepancies

These are alignment discrepancies, not automatically ground-truth errors. Several are representation differences such as a wildcard in GT versus a named elective slot in OCR.

### DSBA coop

- GT-only alignment keys: free elective 1, free elective 2, and combined `06026259 หรือ 06026260`.
- OCR-only alignment keys: the two named free-elective slots and the two cooperative-education codes split into separate rows.
- Alignment: 41/44 matched, F1 0.9213. SQLite verification: 7/7.

### AI

- GT-only: `06016401`; free elective 1; language elective `90644xxx`; free elective 2.
- OCR-only: the two named free-elective slots and language wildcard `9064xxxx`.
- Alignment: 37/41 matched, F1 0.9136. SQLite verification: 7/7.

### IT coop

- GT-only: the repeated source row `06016418`; `9064xxxx` in year 4/1; two separately represented free-elective slots; `90644042` in year 4/2.
- OCR-only: one merged free-elective row and one row where `90644042` was misread as `90642033`.
- Alignment: 48/53 matched, F1 0.9320. SQLite verification: 7/7.

### IT no-coop

- GT-only: the repeated source row `06016418`; `90644042` in year 3/2; free elective 1; free elective 2.
- OCR-only: one row where `90644042` was misread as `90642033`, plus named free-elective slot representations.
- Alignment: 50/54 matched, F1 0.9346. SQLite verification: 7/7.

## Verification outputs

- DSBA coop: 7/7 checks; 30/30 evaluation answers; 30/30 cited.
- DSBA no-coop: 7/7 checks; 30/30 evaluation answers; 30/30 cited.
- AI: 7/7 checks.
- IT coop: 7/7 checks.
- IT no-coop: 7/7 checks.

## Known source anomalies and limitations

1. The IT PDF prints `06016418` twice in year 3/semester 1, once under software development and once under multimedia. This is an anomaly in the source document itself, not an invented GT duplicate.
2. A fresh Typhoon OCR attempt returned only `@@@@@@@@...` for every IT page (zero tokens). The bad transcript was removed from the live Lab 7B folders. Preserved candidate JSON from the prior valid OCR run was restored and its page citations shifted by one to match the project-local IT PDF.
3. Full verification of the 266-course general-education catalogue and all rule fields requires the missing `GT_Template-2.xlsx` (and a BIT source PDF for BIT-specific rules).
