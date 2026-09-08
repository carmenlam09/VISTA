# Prompt for Claude Code — VISTA Module 6: GEN AI Smart KYV Report Generation

> Paste everything below this line into Claude Code, working inside the project root: `C:\Users\tongc\claude_base\vista`

---

## Role

You are the lead engineer building **VISTA (Vendor Intelligence Screening & Trust Assessment)**, an AI-powered Vendor Risk Intelligence Platform for a bank's Know Your Vendor (KYV) process. VISTA is being built module by module in this repo (`C:\Users\tongc\claude_base\vista`), which already contains:

- **Module 1** — Digital Intake & Entity Extraction
- **Module 2** — Unified Screening Intelligence View (aggregates CTOS, NetReveal, prior KYV reviews, adverse news, public records)
- **Module 3** — Adverse Media Screening Engine (categorizes adverse-news hits against a risk taxonomy)
- **Module 4** — Risk Signal Intelligence Engine (triages findings into false-positive vs. needs-review, with confidence scores)
- **Module 5** — Risk Assessment Engine (draft risk rating, materiality justification, EDD recommendation)

**This task covers only Module 6: the Smart Report Generation Engine.** Do not modify Module 1-5's code.

### Before writing any code

1. Open `module1/` through `module5/` and inspect their conventions: language/framework, folder layout, coding style, schema definition patterns, README structure, and venv/`requirements.txt` setup.
2. Match those conventions for Module 6. If prior modules conflict with each other, tell me and ask which to follow rather than picking one yourself.
3. Summarize your findings and the folder/venv plan for Module 6, and wait for my confirmation before proceeding.

## Required Input Before Building: The Existing KYV Report Template

Module 6's entire purpose is producing reports "aligned to existing templates" — but this repo does not currently contain that template, and you cannot infer the bank's real report structure, section order, or house style.

- Check whether a `templates/` folder or any sample KYV report already exists anywhere in the repo. If it does, use it as source of truth.
- If it does not exist, **stop and ask me for the actual template or a sample past KYV report** before designing the document-generation logic.
- If I'm not able to provide one right away, you may proceed with a clearly-labeled **placeholder template** (a sensible KYV report structure you design) so the rest of the module can be built and tested — but flag prominently in the README that this placeholder must be swapped for the bank's real template before this module is used for anything real.

## Product Context

Modules 2-5 produce, respectively: aggregated raw screening evidence, categorized adverse-media findings, triaged confidence scores, and a draft risk assessment with a materiality justification and EDD recommendation. Today, a reviewer has to manually pull all of that together into a formatted report for approval — copying findings, writing narrative sections, and making sure nothing required by the template is missing.

**Module 6's job is to assemble everything upstream into one approval-ready report**: populate the bank's existing KYV report template with the screening evidence, categorized findings, triage outcomes, and risk assessment, with AI-drafted narrative sections filling in the write-up a reviewer would otherwise draft by hand — while keeping every claim in the report traceable back to the specific finding or rule that produced it.

## Module 6 Objective

Build the **Smart Report Generation Engine**: given an entity, pull together its data from Modules 1-5, populate the existing KYV report template with structured findings and AI-drafted narrative sections, and produce an approval-ready draft report plus a separate traceability manifest that maps every narrative claim back to its source data — all clearly labeled as a draft pending reviewer sign-off.

## Hard Requirement: This Module Drafts a Report, It Does Not Approve One

- Output is always a **draft** report. Nothing in this module should imply the report is final, sent, or approved — that remains a human action under the Maker-Checker framework.
- If Module 5's risk assessment has been edited by a reviewer since the AI draft, **the report must use the reviewer-edited version**, not the original AI draft — pull the latest state, not a cached first pass.
- Every version of a generated report, and any regeneration after upstream data changes, must be logged for audit.
- Report generation must never silently drop a required template section because upstream data is missing — if data for a section isn't available, the report should say so explicitly (e.g. "No prior KYV review found") rather than omitting the section or leaving it blank without explanation.

## Inputs

Module 6 consumes outputs from all five prior modules. Treat each module's actual current schema as source of truth — read them rather than assuming:

- **Module 1** — entity profile (name, aliases, IDs, relationships)
- **Module 2** — aggregated screening evidence across all five sources
- **Module 3** — categorized adverse-media findings (theme, severity, rationale)
- **Module 4** — triaged findings with confidence scores and disposition recommendations
- **Module 5** — draft (or reviewer-edited) risk assessment: rating, matched rules, materiality justification, EDD recommendation

Module 6 should be runnable against **live output from Modules 1-5** and against **standalone fixture files** covering both a complete data set and a deliberately incomplete one (to test graceful handling of missing sections).

## Core Capabilities

1. **Data Aggregation Layer**
   - Pull and assemble the entity's data from all five upstream modules into one unified `ReportData` structure.
   - Handle partial/missing upstream data gracefully — flag what's missing rather than failing or silently omitting it.

2. **AI-Drafted Narrative Sections**
   - Generate the prose sections a reviewer would otherwise write by hand: executive summary, screening findings summary, adverse media narrative, risk assessment narrative, EDD recommendation write-up.
   - Reuse Module 5's materiality justification as the basis for the risk assessment narrative rather than re-deriving it independently — this module assembles and formats, it doesn't re-decide the assessment.
   - Match the tone/style of the real template or sample report if one was provided; otherwise use a clear, formal, audit-appropriate tone.
   - Treat narrative generation as a distinct, swappable service, consistent with the pattern used in Modules 2, 3, and 5.

3. **Template Population / Document Generation**
   - Populate the existing (or placeholder) template's actual sections and fields — do not invent a different report structure than the template specifies.
   - Produce output in the same file format as the template (most likely `.docx`) using an appropriate library (e.g. `python-docx` if the stack is Python).

4. **Traceability Manifest**
   - Alongside the generated report, produce a separate machine-readable manifest (JSON) mapping each narrative section/claim to the specific finding references, rule IDs, and source module records that support it.
   - This keeps the report itself readable prose for reviewers/regulators while preserving full auditability underneath — do not clutter the report text itself with inline citation markers.

5. **Draft & Version Tracking**
   - Track report status: `draft`, `under_review`, `approved`.
   - Regenerating a report after upstream data changes (e.g. a reviewer edits the Module 5 assessment) should produce a new version, not silently overwrite history.

6. **Integration Point**
   - Expose this as a clean function/API that takes an `entity_id`, pulls the relevant data from Modules 1-5, and returns the generated report file plus its traceability manifest.

## Technical Requirements

- **Environment setup — align with Modules 1-5, isolate from all five**:
  - Create Module 6 in its own `module6/` folder with its **own virtual environment** (`module6/.venv`) and its own `requirements.txt`.
  - Use the **same Python version** as the prior modules, but do not cross-install dependencies in either direction.
  - Add `module6/.venv/` to `.gitignore` if not already covered.
- **Stack**: match the prior modules' backend framework choice unless there's a clear reason not to — state explicitly if you deviate. For document generation specifically, choose a library appropriate to the template's actual file format once you've identified it.
- **Testing**: unit tests for the aggregation layer's handling of missing/partial data; tests confirming the traceability manifest correctly maps every narrative claim to a source reference; at least one integration test generating a full report from a complete fixture set, and one from a deliberately incomplete fixture set to confirm graceful degradation.

## Build Plan (work in this order; check in after each phase with a brief summary before continuing)

1. **Inspection pass**: review Module 1-5 conventions; locate or request the existing report template as described above; propose Module 6's folder structure and venv setup; wait for confirmation.
2. **Design pass**: propose the `ReportData` aggregation schema, the template-field mapping approach, and the traceability manifest schema. Get this right before implementation.
3. **Data aggregation layer**: pull from Modules 1-5, handle missing data gracefully. Unit tests.
4. **AI narrative drafting service**: generate the report's prose sections from `ReportData`. Tests against fixtures with known-expected content.
5. **Template population / document generation**: fill the real (or placeholder) template and produce the output file.
6. **Traceability manifest generation**: map narrative claims to source references. Tests confirming completeness.
7. **Draft/version tracking**: status field, versioning on regeneration.
8. **Integration point**: function/API taking an `entity_id` through to a generated report + manifest.
9. **Tests + README**: end-to-end tests (complete and incomplete fixture sets), plus a README explaining the template requirement, how to run Module 6 standalone against fixtures, how it connects to Modules 1-5, and an explicit note that output is a draft pending reviewer sign-off.

## Assumptions & Ambiguity

Where anything here is underspecified, pick a sensible default, implement it, and note the assumption in the README — except for genuine architectural forks, anything touching Module 1-5's existing files, or the report template itself, where you should stop and ask me first.

## Definition of Done

- [ ] Folder/venv setup mirrors Modules 1-5 conventions and stays fully isolated from all of them
- [ ] The real KYV report template is used, or a clearly-labeled placeholder is in place pending the real one
- [ ] Reports pull the latest (reviewer-edited, if applicable) Module 5 assessment, not a stale AI draft
- [ ] Missing upstream data is explicitly flagged in the report, never silently omitted
- [ ] Narrative sections are AI-drafted but traceable via a separate manifest, not inline citation clutter
- [ ] Report status (`draft` / `under_review` / `approved`) is tracked, and regeneration creates new versions rather than overwriting
- [ ] All outputs are clearly labeled as drafts pending reviewer sign-off
- [ ] Unit + integration tests pass, including the deliberately-incomplete-data case
- [ ] README documents the template requirement, how to run it, and how it connects to Modules 1-5
