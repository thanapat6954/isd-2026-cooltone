# Curriculum OCR project

- Build source-faithful OCR + database + chatbot behavior for AI, DSBA, IT, BIT and legacy, across all available versions/plans. Books and recorded identity mappings are authoritative; OCR is not independent ground truth.
- Read the existing `curriculum-audit` skill in the configured Codex skills directory (normally `$CODEX_HOME/skills/curriculum-audit/SKILL.md`).
- Single authoritative checkpoint: repository-root `docs/PROGRESS.md`. Do not create STATE.md. Resume NEXT ACTION and update this checkpoint during work and last as handoff.
- Work locally on `week11_thanapat` (created from the latest audit/UI work), never directly on main. Preserve unrelated changes. Do not commit, push, open a PR, or merge unless explicitly requested.
- On the development machine the live application is a separate sibling `../ocr_final` folder; discover its absolute location before acting. Deliberately port reviewed implementation changes into this repository's `ocr_final/` folder. Do not edit another duplicate by accident.
- Audit SQLite read-only. Back up affected databases before repairs. Preserve original OCR, source PDFs and protected held-out inputs; no fabricated course facts or registration permissions.
- Run `python scripts/audit_all.py`, real gold Q&A checks and existing tests. Save evidence, separate unverified coverage from passing results, and inspect the real UI before claiming it works.
- Project report prose is Thai; replies and code comments are English. Keep technical terms unchanged.
