# Curriculum OCR project

- Build source-faithful OCR + database + chatbot behavior for AI, DSBA, IT, BIT and legacy, across all available versions/plans. Books and recorded identity mappings are authoritative; OCR is not independent ground truth.
- Read the existing `curriculum-audit` skill at `C:/Users/thana/.codex/skills/curriculum-audit/SKILL.md`.
- Single authoritative checkpoint: `docs/PROGRESS.md` (`C:/Users/thana/OneDrive/เอกสาร/isd-2026-cooltone/docs/PROGRESS.md`). Do not create STATE.md. Resume NEXT ACTION and update this checkpoint during work and last as handoff.
- Work on `audit/curriculum-challenge`, never directly on main. Preserve unrelated changes; do not push without a user request.
- Live application is the separate `C:/Users/thana/OneDrive/เอกสาร/ocr_final` folder; deliberately port reviewed implementation changes into this repository's `ocr_final/` folder. Do not edit another duplicate by accident.
- Audit SQLite read-only. Back up affected databases before repairs. Preserve original OCR, source PDFs and protected held-out inputs; no fabricated course facts or registration permissions.
- Run `python scripts/audit_all.py`, real gold Q&A checks and existing tests. Save evidence, separate unverified coverage from passing results, and inspect the real UI before claiming it works.
- Project report prose is Thai; replies and code comments are English. Keep technical terms unchanged.
