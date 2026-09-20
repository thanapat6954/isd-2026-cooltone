# Pending-items resolution

Updated 2026-09-20 after rebuilding all authoritative Lab 8B outputs.

## 1. Chapter 9-style validation: completed

- Five separate held-out sets: DSBA coop, DSBA no-coop, AI, IT coop, IT no-coop.
- Three runs per set with the actual Ollama option `temperature=0.0`.
- Slices: value, count, set, and expected-not-found.
- All profiles: 12/12, stable across all three runs, citation coverage 12/12.
- Abstention precision, expected-not-found accuracy, and real-answer recall: 100%.
- Full results: `ROBUSTNESS_REPORT.md` and `work/robustness_summary.json`.

## 2. Lab 9: blocked by missing assignment brief

No Lab 9 implementation is claimed. The Chapter 9-style validation above is an
evaluation addition to Labs 7B/8B, not a substitute for the unknown Lab 9 rubric.
The actual Lab 9 assignment text is still required before implementing it.

## 4. AI/IT Q&A evaluation: completed

AI, IT coop, and IT no-coop each now have an independent 30-question answer key
and `eval_result.json`. Each scored 30/30 with 100% citations and 30/30 responses
under five seconds. `generate_program_gold.py` reproducibly creates these files.

## 5. IT identifier: clarified

`--program it` and the explicit alias `--program it-both` both run, in order:

1. `it-no-coop` (`program_id=IT-no-coop`)
2. `it-coop` (`program_id=IT-coop`)

Use `--program it-no-coop` or `--program it-coop` to run exactly one track.

## 6. General-education fallback: integrated without guessing

`run_lab8b.py` now passes
`data/ground_truth/general_education_ground_truth.json` to every import. The file
contains 266 unique catalog courses. Existing curriculum records take precedence;
missing catalog records are added to `course` only. The importer never assigns a
catalog course to a year/semester and never replaces a wildcard slot with an
arbitrary course.

The number newly added varies because some catalog courses already occur in each
plan: DSBA 258, AI 265, and IT 259. The behavior is covered by self-tests.

## Current reproducible checks

- Schema/import/security/verification self-tests: 30/30.
- Database verification: 7/7 for all five profiles.
- Known 30-question Q&A: 30/30 for all five profiles.
- Held-out three-run validation: 12/12 and stable for all five profiles.
