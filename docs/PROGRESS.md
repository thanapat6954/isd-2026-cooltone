# Curriculum OCR — authoritative checkpoint

Updated 2026-10-02 (Asia/Bangkok). This is the ONE authoritative memory file:
`C:/Users/thana/OneDrive/เอกสาร/isd-2026-cooltone/docs/PROGRESS.md`.
The separate live application's older PROGRESS.md is a historical mirror, not authority. Do not create STATE.md.

## 1. GOAL AND RULES

- Source-faithful OCR/database/chatbot across AI, DSBA, IT, BIT, legacy and every available version/plan.
- Verified ch1 PDF5/7: P2 weights DB/RAG20, OCR20, output20, LLM30, app/docs10; accuracy >91% full band, 80–90% partial, <80% low. Prerequisite/registration example L2; old/new comparison L3; same-year revision/dual degree L4; retrieval+generation <5s bonus, combined bonus capped +10.
- Feature branch ONLY: `audit/curriculum-challenge`. Never main, never push/merge without authorization.
- Preserve /api/ask and /ask contracts; no fabricated answers, permissions, filler electives, or curriculum identities.
- Audit SQLite mode=ro/query_only=ON; verified recoverable SQLite backup before fixes, staged integrity-checked replacement.
- Original OCR, frozen candidates and protected held-out inputs are unchanged. Curated book corrections are NOT an OCR accuracy gain.
- One memory file; detailed evidence under docs/results and ocr_final/reports, not in chat. Checkpoint before long jobs and last as handoff.
- Replies English; report/README prose Thai. Do not hand-edit generated EVAL/README.
- No additional agents, skills/plugins/dependencies unless justified. Actual browser tests use the browser tool, not hidden browser state.

## Resume

1. Read root AGENTS.md, curriculum-audit skill and THIS file; resolve live app versus Git checkout.
2. Check branch/status/latest commits. Historical evidence is not proof of unchanged live state.
3. Check jobs/logs before restarting. Reuse only results with unchanged code/data/source hashes.
4. Continue NEXT ACTION below. Do not redo A0 or completed source-review batches.

## 2. CURRENT STATUS

- Phase: reported prerequisite/version failures repaired and verified; wider source/table fidelity audit INCOMPLETE.
- Git repo: `C:/Users/thana/OneDrive/เอกสาร/isd-2026-cooltone`; repo application: `ocr_final/`.
- Live app (the user's actual server/data): `C:/Users/thana/OneDrive/เอกสาร/ocr_final`.
- Entry commit `bb00c8a`; this checkpoint accompanies the next feature commit. Run git log for its hash.
- All product changes deliberately ported to both app copies; new audit/report tools also copied to live when applicable. No PDFs/DBs/env secrets added to Git.
- Available sources: AI.pdf cover visually confirms **2566** (PDF1), DSBA/IT/BIT 2565+2560 mapping remains authoritative. Seven books are cached as page-delimited/hash-keyed locators under live work/ref_text. AI has no older source. Same-year revision/dual-degree sources absent.
- Audit covers 16 SQLite datasets: 13 active normalized profiles, 1 legacy catalog, 2 repair-validation copies. Current exit1: 1377 FAIL + 4882 NEEDS_REVIEW/SKIPPED findings. Counts are locator/schema/coverage findings, NOT accuracy. All five curriculum families present. Reports are ocr_final/reports/audit_*.md; read Summary/HIGH only. Historical AI unknown-year report moved to reports/history, not deleted.
- Final development gold: **70/70 each of 3 runs** (210 responses) across 13 normalized identity/plan combinations + legacy. Legacy's 5 cases test uncertainty safety only, not book content accuracy. Source-backed structured checks plus missing-evidence cases; NOT final held-out.
- Source/citation metadata checks: 52/52 content cases in first run; only 26/52 specify an exact source PDF page. This is not full semantic citation accuracy.
- Latency of correct substantive L1/L2 cases (n52/run): first median501.99ms p95642.41ms; repeats median503.85/506.89ms p95566.94/559.54ms. First cache hit0/70, repeats70/70. Not guaranteed cold start; these structured cases don't call LLM generation and don't establish difficult L3/L4 bonus.
- Final full suite **64/64**, schema selftests **30/30**, original backup integrity **13/13**. Raw commands/output: docs/results/current_audit_final_regressions.json.
- Real browser AI/DSBA/IT/BIT current-family cases observed; /ask agrees with rendered answer/citations **4/4**. DSBA prerequisite desktop/mobile screenshots; mobile390x844, document width375, no horizontal overflow. Not every version/level. Legacy has no UI selector.
- Live backend currently PID **20272**, Uvicorn port8000. Log: live work/web/backend-25691002-201156-484.stderr.log; verify PID/command/port before changing it. No OCR or gold jobs remain running; earlier launcher exec sessions may retain background-process handles, not active evaluation jobs. Browser left showing repaired DSBA question; temporary viewport reset.
- Credential-pattern scan found no matches in new raw QA/UI/reports. Raw debug evidence and AGENTS contain absolute local paths; this is a local feature commit only, not publication. Live/repo hashes match for 11 changed product/review paths. Root README, root ocr_system and Lab07 report unchanged.
- Final report: `ocr_final/reports/audit_summary.md`; generator scripts/summarize_current_audit.py.
- **NEXT ACTION:** Resume B1 blocked table repairs, FIRST IT-2560 coop PDF36/40. Read its current conversion fidelity_errors, inspect only those rendered tables, compare row count/fields/credits with original OCR, and repair extraction or create a separate hash-guarded reviewed ingest. Back up that DB before replacement. Then IT-2565 no-coop36/37, IT-2565 coop43/44, BIT-2565 no-coop29/30, BIT-2565 coop34/35. Preserve frozen OCR and held-out inputs. After each profile: update this checkpoint, run affected gold + regressions + audit. Do not begin full held-out/L3/L4 evaluation until these source-fidelity defects are resolved.

## 3. DONE LOG

- 2026-10-01 — A0: created feature from week9; measured committed baseline and environment, preserved frozen OCR. Evidence docs/results/architecture_inventory.json, baseline_execution.json; docs/AUDIT_PHASE_A.md.
- 2026-10-01 — A1: 180 stratified DSBA/IT/BIT candidates (30/program-version); 36 plan pages + 43 description renders/locators. Only 38 field rows approved + 1 spurious. DSBA2560 all30 decisions completed. Evidence a1_ground_truth_review.json, a1_render_checkpoint.json, a1_description_render_checkpoint.json, a1_review_batch_*.json, a1_field_metrics.json. Not full-book GT; original prerequisite-bearing biased slice0/18, not overall accuracy.
- 2026-10-02 — B1 commit fb8b714: lossless placeholder/alternatives/page schema and UI, no invented deficit fillers, safe backed-up staged loads; BIT2560coop missing Y4S2 repaired from PDF30/book25 through reviewed_ingest.json. Count126credits, structural7/7. Original OCR remains114credits and default rebuild correctly rejects it.
- 2026-10-02 — Commit bb00c8a fixed HTTP501: Python static server occupied8000; real Uvicorn now serves same-origin /frontend/. scripts/start_web.ps1 guards occupied non-API ports. Prior regressions47/47+selftests30/30.
- 2026-10-02 — Read authoritative skill/task/rubric; created concise AGENTS; implemented read-only explicit-schema audit_all.py and resumable/hash-keyed cache_book_reference.py (all7books).
- 2026-10-02 — Reproduced 06066302 “not found” in actual AIT/current UI; historic reported selector not recoverable, not guessed. SQL-only prerequisite lookup was earliest confirmed retrieval loss. DSBA.pdf319/book318 and IT.pdf359/book358 visually explicitly NONE for06066301/02/03. New course-aware evidence query/uncertainty formatter and scoped version behavior verified.
- 2026-10-02 — Hash-guarded reviewed ingest applied current NONE facts and reused12 previously approved prerequisite-bearing A1 descriptions. Active profiles now carry32 course prerequisite reviews; most course catalog coverage remains unknown. SQLite backups and before/after: prerequisite_review_ingest_2026-10-02.json, approved_prerequisite_ingest.json.
- 2026-10-02 — Development gold exposed Thai no-coop selection loss and course-name/program-name intent collision; fixed shared parser/selection and added regressions. Gold first68/70 after those/prerequisite fixes.
- 2026-10-02 — Book-approved canonical names repaired IT2560 code06016323 in both plans and removed three verified specialization-header bleed-ins. Rebuild reapplies the same review, original OCR untouched. approved_name_prerequisite_ingest.json has exact old/new and backup paths. Parser/VLM source-row loss beyond these reviews remains OPEN.
- 2026-10-02 — AI.pdf cover1 explicitly new curriculum2566; backed-up metadata correction, source SHA and before/after in ai_identity_cover_review.json, document_identity_reviews.json. AI latest display/config and generic explicit-year/latest selection fixed.
- 2026-10-02 — Final real API gold210responses allpass, full64tests +30selftests; current-family browser4/4 API/UI agreement, mobile verified. Raw qa_gold_final_2026-10-02.json, current_audit_final_regressions.json, ui_observations_2026-10-02.json, ui_api_agreement_2026-10-02.json, screenshots/. Full audit still incomplete.

## 4. FINDINGS AND PROBLEMS (ranked)

1. **HIGH OPEN — OCR/table fidelity, P2 OCR/output.** Five profiles still pre-migration because real-source validation blocks rebuild; pages in NEXT ACTION. No filler-elective workaround. 8/13 active DBs have fidelity schema. Requires table-by-table independent visual review.
2. **HIGH OPEN — prerequisite/source coverage, P2 RAG/LLM.** Only reviewed subset has explicit status (32 active course reviews), general_education pool lacks official PDF provenance in audit. Empty edges ≠ no prerequisite. Evidence audit_results.json; remaining records unknown.
3. **HIGH OPEN — legacy, P2 accuracy/identity.** 6147 page-fragment rows combine books; metadata lacks authoritative years/versions; many invalid codes/page locator problems. Preserve data; establish source-backed mapping and parser repair before cleanup/accuracy claims. Five safety gold cases aren't legacy content GT.
4. **HIGH OPEN — full independent source/LLM evaluation.** 180 candidates aren't all approved; A1 target >=30 rows/program-version incomplete, AI not in that older stratified set. L3/L4, graduation conditions, same-year/dual-degree (missing docs), final held-out and model seed stability unmeasured.
5. **FIXED/VERIFIED — false prerequisite absence, wrong version/plan selection and intent.** Course-aware LEFT JOIN; explicit None versus unknown; no unsupported enrollment grant; no unrelated legacy/version fallback; Thai no-coop and AI suffix independence; 64regressions and210gold results. Fix commit: this checkpoint commit.
6. **FIXED/VERIFIED — reviewed IT names and prerequisites.** Official source-reviewed ingest + recoverable backups; exact changes in approved_name_prerequisite_ingest.json. Not OCR model improvement. Broader row/name extraction root causes remain1.
7. **FIXED/VERIFIED — AI identity and display.** Cover2566, source hash, safe DB update, config/UI/version routing. current gold AI-2566-coop5/5 x3.
8. **OPEN — citations and app breadth.** DSBA319/book318 and IT359/book358 exact prerequisite sources verified; printed folios not propagated for every course query. AI23/book19 visually known but course citation only PDF23. No legacy UI selector. Real-browser all-version/L1–L4 layouts/errors still incomplete.
9. **FIXED/VERIFIED — HTTP501, cache timing, misleading engine label.** Actual Uvicorn on8000, same origin; cache returns current-request timing; structured answers label SQL(database-backed), not fictional model generation.

## 5. DECISIONS AND REASONS

- Books/hash-guarded visual reviews authoritative; embedded Thai text font-corrupted, locator-only. Course code match isn't independent GT.
- Exact program/version/source mappings, no folder substring guesses; don't apply one printed-page offset to appendices.
- Reviewed facts are a reusable generic ingest layer, not course-specific production branches or eval answers fed to app.
- Keep raw baseline/intermediate/final results separate. Interrupted baseline (OneDrive replacement error at80) preserved in qa_gold_before_legacy_reviews.json and qa_gold_interrupted_checkpoint_80.json; not completed, not resumable after dependency changes.
- Gold resume keys include source gold hash + deployed code + DB hashes; changing dependencies requires a new output. Repeated template success doesn't prove generalization.
- SQLite backup API preserves logical snapshots, not necessarily identical file header bytes. Validate integrity/content and record backup hashes, not byte equality with original DB.
- Preserve source data and staged failed ingest; Windows connections close explicitly before replacement. Git lock/index failure means stop, not retry.
- More complete source audit is deferred to next bounded batch because current context is long; don't launch a new multi-page repair before handing off this verified step.

## 6. HOW TO RERUN

PowerShell from repository root (use application cwd for direct unittest imports):
```powershell
Set-Location 'C:\Users\thana\OneDrive\เอกสาร\isd-2026-cooltone'
git branch --show-current
git status --short
git log --oneline -3
$env:PYTHONUTF8='1'
$liveApp='C:\Users\thana\OneDrive\เอกสาร\ocr_final'
.\ocr_final\venv\Scripts\python.exe ocr_final/scripts/audit_all.py --app-root $liveApp --out ocr_final/reports
# Exit1 is expected while unresolved FAIL findings exist; exit2 means incomplete coverage.

.\ocr_final\venv\Scripts\python.exe ocr_final/scripts/capture_b1_checkpoint.py --app-root $liveApp --output docs/results/new_regression_checkpoint.json
.\ocr_final\venv\Scripts\python.exe ocr_final/scripts/run_qa_gold.py --app-root $liveApp --output docs/results/new_gold_run.json --runs 3
# Add --resume ONLY when dependencies are unchanged; output saves after each case.

.\ocr_final\venv\Scripts\python.exe ocr_final/scripts/cache_book_reference.py --app-root $liveApp
.\ocr_final\venv\Scripts\python.exe ocr_final/scripts/verify_ui_observations.py --observations docs/results/ui_observations_2026-10-02.json --output docs/results/new_ui_agreement.json
.\ocr_final\venv\Scripts\python.exe ocr_final/scripts/summarize_current_audit.py
Set-Location $liveApp
.\scripts\start_web.ps1
# http://localhost:8000/frontend/ ; never python -m http.server on API port8000.

```
- OCR/build: live `venv/Scripts/python.exe run_lab8b.py --program <profile>` (profile keys in run_lab8b.py). **all** includes source-blocked profiles, not a verified clean rebuild. Rebuild reapplies approved identity/prerequisite/name reviews after load with a fresh backup.
- BIT2560coop reviewed rebuild must explicitly use preserved live work/lab8b_bit_2560_coop/lab7b/reviewed_ingest.json. Exact import/load/verify arguments: docs/results/b1_bit2560_reviewed_import.json; helper scripts/apply_reviewed_plan_term.py with docs/results/b1_bit2560_coop_page30_review.json.
- DBs: live work/lab8b_<profile>/curriculum.db; legacy live curriculum.db. DBs/PDFs are gitignored.
- Backups: live work/backups/2026-10-01-before-placeholder-migration (13 verified); work/backups/prerequisite-review/<UTC>/<profile>.db; work/backups/identity-review/<UTC>/lab8b_ai.db. Exact paths/results in ingest JSONs.
- Reference cache: live work/ref_text/manifest.json + hash-named .jsonl files (locator only).
- Protected final held-out: unchanged robustness_eval.py/tests inputs; no new final held-out score.
- UI reproduction: DSBA latest + “วิชา 06066302 มีวิชาบังคับก่อนอะไร และถ้ายังไม่ผ่านสามารถลงทะเบียนได้หรือไม่”; prerequisite NONE with PDF319/book318, registration uncertainty. IT analogous PDF359/book358.
- Latency benchmark: scripts/run_qa_gold.py produces first/repeat/cache timings; true cold LLM/difficult-question benchmark still to implement/run after source correctness.

## 7. OPEN QUESTIONS / UNVERIFIED

- Missing same-year revisions/dual-degree books, AI old source and actual Lab9 assignment brief; don't invent them.
- Historical selector for the originally reported06066302 case not recoverable. Tested actual AIT/current reproduction and all real identities instead.
- Fresh clone requires local PDFs/DB regeneration; full end-to-end OCR rebuild currently blocked and not verified.
- Independent names/category/credits/graduation/whole-book completeness, final held-out, L3/L4 accuracy and semantic citations remain incomplete.
- Five blocked table repairs and broader legacy extraction/source mapping are exact next work. No task-complete claim, no push/main change.
