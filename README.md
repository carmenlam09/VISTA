# VISTA

Vendor Intelligence Screening & Trust Assessment — an AI-powered Vendor Risk Intelligence Platform for a bank's Know Your Vendor (KYV) process, built module by module.

## Modules

- [`module1/`](module1/README.md) — Digital Intake & Entity Extraction Engine. Streamlit app that extracts vendor/director/shareholder/UBO profiles from uploaded documents and persists them to SQLite.
- [`module2/`](module2/README.md) — Screening Intelligence Hub. Aggregates CTOS, NetReveal, prior KYV reviews, adverse news, and public records into one unified per-entity view with an AI-generated, source-attributed summary.
- [`module3/`](module3/README.md) — Adverse Media Screening Engine. Matches Module 2's adverse-news hits against a compliance-editable keyword taxonomy and produces categorized, source-attributed risk findings.
- [`module4/`](module4/README.md) — Risk Signal Intelligence Engine (False Positive & True Hit Triage). Scores Module 2/3's findings on entity-resolution and historical signals and produces a ranked, AI-suggested (never auto-decided) triage recommendation per finding.
- [`module5/`](module5/README.md) — Risk Assessment Engine (Risk Assessment & EDD Recommendation). Evaluates Module 4's triaged findings against a compliance-editable policy rule set to produce a draft risk rating, cited materiality justification, and EDD recommendation — Maker-Checker, never auto-approved.
- [`module6/`](module6/README.md) — Smart Report Generation Engine. Assembles Modules 1–5's data into an approval-ready draft KYV report (`.docx`) with AI-drafted narrative sections and a separate traceability manifest. **Uses a placeholder report template** — see the warning at the top of module6/README.md.
- [`module7/`](module7/README.md) — Vendor Risk Knowledge Repository. Ingests completed reviews/assessments/decisions from Modules 3–6 into a never-deleted historical store, with AI-assisted (structured + semantic) retrieval so reviewers can surface relevant past cases. **Uses a placeholder retention policy**, and Modules 2/4's live wiring into it remains outstanding — see the warnings at the top of module7/README.md.

Each module has its own README with setup instructions, its own dependency manifest, and runs independently. Module 2 reads Module 1's entity profiles as a read-only input; Module 3 reads Module 2's adverse-news output (and, transitively, Module 1's entity names) the same way; Module 4 reads Module 1's and Module 2's data the same read-only way and calls Module 3's live API (Module 3 has no database of its own to read); Module 5 reads Module 4's data the same read-only way, plus Module 2/3 again for risk-theme recovery (a gap in Module 4's output — see module5/README.md); Module 6 reads Modules 1, 2, 4, and 5's data the same read-only way and calls Module 3's live API, the same as Module 5; Module 7 is a standalone ingestion+retrieval store other modules will call in a future integration pass (not wired up in this task). None of the modules modify or import another module's code.

## Repository layout

```
vista/
├── module1/     # Digital Intake & Entity Extraction (Streamlit + SQLite)
├── module2/     # Screening Intelligence Hub (FastAPI + React + Postgres)
├── module3/     # Adverse Media Screening Engine (FastAPI, own venv)
├── module4/     # Risk Signal Intelligence Engine / Triage (FastAPI, own venv)
├── module5/     # Risk Assessment Engine / EDD Recommendation (FastAPI, own venv)
├── module6/     # Smart Report Generation Engine (FastAPI, own venv)
├── module7/     # Vendor Risk Knowledge Repository (FastAPI, own venv)
├── docs/        # Cross-module specs and prompts
└── README.md    # this file
```
