# VISTA

Vendor Intelligence Screening & Trust Assessment — an AI-powered Vendor Risk Intelligence Platform for a bank's Know Your Vendor (KYV) process, built module by module.

## Modules

- [`module1/`](module1/README.md) — Digital Intake & Entity Extraction Engine. Streamlit app that extracts vendor/director/shareholder/UBO profiles from uploaded documents and persists them to SQLite.
- [`module2/`](module2/README.md) — Screening Intelligence Hub. Aggregates CTOS, NetReveal, prior KYV reviews, adverse news, and public records into one unified per-entity view with an AI-generated, source-attributed summary.

Each module has its own README with setup instructions, its own dependency manifest, and runs independently. Module 2 reads Module 1's entity profiles as a read-only input; it does not modify or depend on Module 1's internals.

## Repository layout

```
vista/
├── module1/     # Digital Intake & Entity Extraction (Streamlit + SQLite)
├── module2/     # Screening Intelligence Hub (FastAPI + React + Postgres)
├── docs/        # Cross-module specs and prompts
└── README.md    # this file
```
