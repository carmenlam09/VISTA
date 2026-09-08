# VISTA Module 6 — Smart Report Generation Engine

> ## ⚠️ PLACEHOLDER REPORT TEMPLATE — READ BEFORE USE
>
> **No real KYV report template or sample past report was available when this module was built.**
> The repo was checked for a `templates/` folder or sample report (none existed); the user was
> asked and chose to proceed with a placeholder for now. `config/report_template.yaml` is a
> sensible, clearly-labeled **placeholder** structure — every generated `.docx` carries a bold
> "PLACEHOLDER TEMPLATE" warning on its first page and `is_placeholder: true` in the config.
>
> **Before this module is used for anything real**, replace `config/report_template.yaml` with the
> bank's actual template structure, and update `app/services/document_generator.py`'s per-section
> rendering to match its real layout/house style. See "Swapping in the real template" below.

Given an entity, pulls together its data from Modules 1–5, populates the KYV report template with
structured findings and AI-drafted narrative sections, and produces an approval-ready draft report
(`.docx`) plus a separate traceability manifest (JSON) mapping every narrative claim back to its
source data — all clearly labeled as a draft pending reviewer sign-off.

## Hard requirement: this module drafts a report, it does not approve one

Every `GeneratedReport` carries a constant `label` and an explicit `status`
(`draft -> under_review -> approved`), matching the pattern established by Modules 4/5. Approving
a report requires the `approver`/`admin` role (Module 5's RBAC, extended — see below).
Regenerating a report (`POST .../regenerate`) always creates a **new version**, never overwriting
history; every generation and every status change is logged for audit.

## Stack

Matches Modules 2–5: Python + FastAPI + Pydantic v2, `pytest`/`pytest-asyncio`, own venv and
`requirements.txt`, fully isolated from Modules 1–5. SQLAlchemy + own SQLite database for
version/status history (like Modules 4/5). Document generation uses `python-docx`, since the
placeholder (and the bank's real template, most likely) is a `.docx`.

## Access control

Extends Module 5's RBAC (`reviewer | approver | admin`) rather than inventing a new one — draft
reports carry the same sensitivity as the risk assessments they're built from. Reading/generating/
editing status requires any authorized role; moving a report to `approved` requires
`approver`/`admin` (a reviewer can't self-approve their own report).

## Architecture

```
module6/
├── config/
│   └── report_template.yaml   # PLACEHOLDER template structure — see warning above
├── app/
│   ├── core/                  # config.py, time.py, auth.py (Role: reviewer|approver|admin)
│   ├── schemas/
│   │   ├── entity.py          # EntityProfile — own copy of the Module 1 contract
│   │   ├── upstream.py        # Module 2/3/4/5 output shapes, adapted at the boundary
│   │   ├── report_template.py # ReportTemplateConfig — the template config contract
│   │   ├── report_data.py     # ReportData — unified aggregation, every section status-flagged
│   │   └── report.py          # GeneratedReport, TraceabilityManifest — the stable output
│   ├── db/                    # base.py, session.py (own reports.db)
│   ├── models/report.py       # GeneratedReportRecord (one row per version, never overwritten),
│   │                          # ReportHistoryRecord (generation + status-change audit log)
│   ├── services/
│   │   ├── entity_lookup.py           # reads module1's vista.db (or fixtures)
│   │   ├── module2_source.py          # reads module2's screening.db (or fixtures), all 5 sources
│   │   ├── module3_source.py          # calls module3's live API (or fixtures)
│   │   ├── module4_source.py          # reads module4's triage.db (or fixtures)
│   │   ├── module5_source.py          # reads module5's risk_assessment.db (or fixtures) —
│   │   │                              # the CURRENT state, reviewer edits included (see below)
│   │   ├── report_data_aggregator.py  # pulls from all 5, flags what's missing (capability 1)
│   │   ├── narrative_service.py       # AI narrative (ABC) + Anthropic + deterministic fallback
│   │   ├── template_loader.py         # loads + validates config/report_template.yaml
│   │   ├── document_generator.py      # python-docx: renders the template from ReportData +
│   │   │                              # narrative (capability 3)
│   │   ├── traceability_service.py    # builds the JSON manifest (capability 4)
│   │   ├── report_engine.py           # orchestrates generation; versioning is the caller's job
│   │   └── audit_service.py           # persists every version + status change
│   ├── api/routes/
│   │   ├── report.py           # GET (latest/generate), POST /regenerate, GET /{v}/download,
│   │   │                       # GET /{v}/manifest
│   │   └── review.py           # POST /{v}/status (approve requires approver+), GET /history
│   └── main.py
├── fixtures/
│   ├── complete/                # a full data set across all 5 upstream modules
│   └── incomplete/               # entity known, everything else deliberately absent
└── tests/
```

## Inputs and how they're read

Same read-only, adapt-at-the-boundary pattern as every prior module — each of `entity_lookup.py`
(Module 1), `module2_source.py`, `module4_source.py`, and `module5_source.py` reads its upstream
module's SQLite file directly, never that module's Python code. `module3_source.py` calls Module
3's live HTTP API (it has no database of its own — see `module3/README.md`), falling back to
fixtures. All five fall back to `fixtures/complete/` (or `fixtures/incomplete/`, depending on which
`ReportDataAggregator` is constructed) when live data is unavailable, so Module 6 runs and tests
fully standalone with no other module's server required.

**Reviewer-edited assessments, automatically.** The hard requirement says the report must use the
latest (reviewer-edited, if applicable) Module 5 assessment, never a stale AI draft.
`module5_source.py` satisfies this without any special-case logic: it reads the entity's single
non-archived `risk_assessment_drafts` row, and Module 5's own edit endpoint
(`module5/app/services/audit_service.py apply_edit`) mutates that same row in place rather than
inserting a new one — so "the current row" already *is* "the latest, edits included."

## Missing data handling

Every `ReportData` section carries an explicit `status` (`ok` / `missing` / `error`) and, when not
`ok`, a `note` explaining why. `document_generator.py` and `narrative_service.py` both check this
status per section and render the note explicitly (e.g. "No Module 5 risk assessment found for
this entity.") rather than silently skipping the section or leaving it blank — verified by the
`fixtures/incomplete/` integration test, and enforced even against a non-compliant LLM response:
any section whose data is missing has its narrative text forced to the deterministic note
regardless of what the model returned for it.

## Traceability manifest

A separate JSON document (`GET /{version}/manifest`), not inline citations in the report prose.
Every section_id used in the report narrative has at least one manifest entry — even a missing
section gets an entry (with an empty `source_references` list) so completeness can be checked
mechanically, never silently dropped. Entries cite Module 2 `result_id`s, Module 3 `finding_id`s,
Module 4 `triage_id`/`finding_reference`s, and Module 5 `draft_id`/`rule_id`s directly.

## Design note: the risk assessment narrative is never AI-authored

`risk_assessment_narrative` is always Module 5's own `materiality_justification` text, lightly
wrapped — in both the deterministic and Anthropic-backed paths. Per the spec: "this module
assembles and formats, it doesn't re-decide the assessment." Letting an LLM paraphrase that text
risks silently dropping a citation Module 5 already validated; reusing it verbatim is the only way
to guarantee that can't happen. Its `generator` field is labeled `module5-reuse:<module5's own
generator>` rather than claiming fresh authorship.

## Swapping in the real template

1. Replace `config/report_template.yaml` with the real template's section structure (`section_id`,
   `title`, `type` per section — see the file's own header comment for the `type` vocabulary), and
   set `is_placeholder: false`.
2. If the real template's sections need a rendering `document_generator.py` doesn't already handle
   (a new layout, a section type beyond `metadata`/`narrative`/`structured`/
   `narrative_plus_table`/`table`/`narrative_plus_list`), extend that file — the
   aggregation/narrative/traceability layers don't need to change.
3. If the real template is itself a `.docx` file with fields/bookmarks to fill (rather than a
   structure to generate fresh), `document_generator.py`'s `generate_document` is the one function
   that needs rewriting to open and populate that file instead of building one from scratch.

## Running it

```powershell
cd module6
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8005
```

Try `GET /api/entities/{entity_id}/report` against a real entity from your Module 1–5 setup, or
the bundled fixtures `vendor:report-complete` (full data) / `vendor:report-incomplete` (entity
known, everything else absent) — both work even with Modules 1–5 never having been run.

Run the tests:

```powershell
cd module6
python -m pytest
```

**To point the narrative service at the real Anthropic API**: set `ANTHROPIC_API_KEY` (copy
`.env.example` to `.env`). Without it, every narrative section comes from the deterministic
fallback.

## Assumptions

- **Placeholder template**: see the warning at the top of this file — the single most important
  assumption in this module.
- **Version numbering**: `next_version()` is `max(existing versions) + 1` per entity; `GET
  .../report` returns the latest existing version (generating v1 if none exists), while `POST
  .../regenerate` always creates a new one — a deliberate split between "view" and "regenerate."
- **No content-edit endpoint**: unlike Module 5, this module doesn't expose an endpoint to edit a
  generated report's text — the spec's capability list for Module 6 only asks for status tracking
  and versioning-on-regeneration, not content editing. A reviewer who wants different narrative
  text triggers a regeneration (e.g. after editing the Module 5 assessment it's based on).
