# Prompt for Claude Code — VISTA Module 7: Vendor Risk Knowledge Repository

> Paste everything below this line into Claude Code, working inside the project root: `C:\Users\tongc\claude_base\vista`

---

## Role

You are the lead engineer building **VISTA (Vendor Intelligence Screening & Trust Assessment)**, an AI-powered Vendor Risk Intelligence Platform for a bank's Know Your Vendor (KYV) process. VISTA is being built module by module in this repo (`C:\Users\tongc\claude_base\vista`), which already contains:

- **Module 1** — Digital Intake & Entity Extraction
- **Module 2** — Unified Screening Intelligence View (aggregates CTOS, NetReveal, prior KYV reviews, adverse news, public records)
- **Module 3** — Adverse Media Screening Engine (categorizes adverse-news hits against a risk taxonomy)
- **Module 4** — Risk Signal Intelligence Engine (triages findings into false-positive vs. needs-review, with confidence scores)
- **Module 5** — Risk Assessment Engine (draft risk rating, materiality justification, EDD recommendation)
- **Module 6** — Smart Report Generation Engine (assembles everything into an approval-ready report + traceability manifest)

**This task covers only Module 7: the Vendor Risk Knowledge Repository.** Do not modify Module 1-6's code.

### Before writing any code

1. Open `module1/` through `module6/` and inspect their conventions: language/framework, folder layout, coding style, schema definition patterns, README structure, and venv/`requirements.txt` setup.
2. Match those conventions for Module 7. If prior modules conflict with each other, tell me and ask which to follow rather than picking one yourself.
3. Summarize your findings and the folder/venv plan for Module 7, and wait for my confirmation before proceeding.

## Product Context — This Module Closes the Loop

There's an important architectural point to understand before designing this: **Module 2 already queries a "previous KYV reviews" source as one of its five inputs — but up to now that's been a mock connector.** Module 7 is what that source is actually supposed to be. Once Module 7 exists, Module 2's mock previous-KYV-reviews connector is meant to eventually be swapped to query Module 7 live, and Module 4's historical-outcome lookup likewise. **You are not asked to make that wiring change now** (it touches Module 2/4's existing code, which is out of scope for this task) — but design Module 7's retrieval API so that swap is straightforward later, and call out clearly in your README that this integration step remains outstanding.

More broadly: every completed review currently produces valuable output — Module 3's adverse-media assessments, Module 4's false-positive decisions, Module 5's risk assessments, Module 6's approved reports — that today just sits in each module and is never reused. **Module 7's job is to capture all of it as the bank's growing institutional memory**, and make it retrievable so future reviewers don't have to re-investigate something the bank has effectively already figured out.

## Module 7 Objective

Build the **Vendor Risk Knowledge Repository**: an ingestion + retrieval system that captures historical KYV reviews, adverse-news assessments, false-positive decisions, EDD outcomes, and approval records from across the platform, and provides AI-assisted retrieval so a reviewer working a new case can surface relevant past assessments instead of starting from zero.

## Hard Requirements

- **Never hard-delete.** This is a regulated bank's audit trail. Superseded or corrected records must be **soft-archived** (marked inactive/superseded, retained, and still retrievable for audit) — never purged.
- **Retrieval surfaces context, it does not make decisions.** A past record showing "this exact name-collision was previously resolved as a false positive" is a reference point for the reviewer (and, later, an input signal for Module 4), never something the system uses to auto-resolve a new finding on its own.
- **Access control**: historical records span every vendor the bank has ever reviewed, which makes this one of the most sensitive stores in the platform. Extend Module 2's existing RBAC approach rather than inventing a separate one.
- **Retention policy is a placeholder pending real bank policy.** Build retention/archival rules as config-driven (mirroring Module 3's taxonomy and Module 5's rule library), but flag prominently in the README that the actual retention periods must be confirmed with compliance before this is used for anything real — similar to how Module 6 flagged its placeholder template.

## Inputs

Module 7 ingests completed records from prior modules. Treat each module's actual current schema as source of truth — read them rather than assuming:

- **Module 3** — categorized adverse-media assessments
- **Module 4** — triage dispositions, and specifically reviewer overrides of AI recommendations (a confirmed false positive or confirmed true hit is high-value historical signal)
- **Module 5** — risk assessments, including the final reviewer-approved version if it differs from the AI draft
- **Module 6** — approved reports and their traceability manifests
- **Module 1/2** — entity profiles and screening evidence, for context and entity-matching on retrieval

Design an **ingestion API** that any of these modules (or a future integration pass) could call to submit a completed record — you're building the capability, not wiring every upstream module to call it in this task.

## Core Capabilities

1. **Unified Knowledge Record Schema**
   - A `KnowledgeRecord` type covering all the record types above, with at minimum: `entity_id`, `record_type` (`kyv_review` / `adverse_news_assessment` / `false_positive_decision` / `edd_outcome` / `approval_record`), `timestamp`, `source_module`, `status` (`active` / `superseded`), `payload` (the actual assessment/finding data), and a link back to the originating record/report for traceability.

2. **Ingestion API**
   - Idempotent record capture — resubmitting the same completed record shouldn't create a duplicate.
   - New versions of a record (e.g. a corrected risk assessment) mark the prior version `superseded`, not deleted.

3. **AI-Assisted Retrieval**
   - Accept both structured queries (by entity, record type, risk theme, date range) and freeform natural-language queries (e.g. "past reviews involving name-collision false positives for this director").
   - Combine semantic similarity search (embeddings over narrative/rationale text) with structured filtering, so a reviewer can find records that are conceptually similar, not just exact entity matches.
   - Return results ranked by relevance, each with enough context (record type, date, outcome, link to source) for a reviewer to judge usefulness without having to open every result.

4. **Reviewer-Facing Search**
   - Expose retrieval as a clean function/API (and, if the stack supports it easily, a simple search view) so reviewers working a new case can query the repository directly.

5. **Retention & Archival**
   - Config-driven retention rules (placeholder values, clearly flagged as pending compliance confirmation).
   - Archival never removes a record from being retrievable for audit purposes — it only affects whether it surfaces in normal day-to-day retrieval results.

6. **Integration Point**
   - Expose ingestion and retrieval as clean, documented APIs designed to be called by Modules 2-6 in a future integration pass, and by any future Module 8+ work. Do not modify those modules now.

## Technical Requirements

- **Environment setup — align with Modules 1-6, isolate from all six**:
  - Create Module 7 in its own `module7/` folder with its **own virtual environment** (`module7/.venv`) and its own `requirements.txt`.
  - Use the **same Python version** as the prior modules, but do not cross-install dependencies in either direction.
  - Add `module7/.venv/` to `.gitignore` if not already covered.
- **Stack**: match the prior modules' backend framework choice unless there's a clear reason not to. For the retrieval store, propose an approach (e.g. Postgres with a vector extension, or a lightweight embedded vector store) and state your reasoning — don't default to something exotic without justifying it.
- **Access control**: extend Module 2's RBAC approach.
- **Testing**: ingestion idempotency tests; soft-archive behavior tests (superseded records remain retrievable but don't surface in normal search); retrieval relevance tests against a fixture history (given a known set of past records, confirm a query returns the expected matches and excludes clearly irrelevant ones).

## Build Plan (work in this order; check in after each phase with a brief summary before continuing)

1. **Inspection pass**: review Module 1-6 conventions; propose Module 7's folder structure and venv setup; wait for confirmation.
2. **Design pass**: propose the `KnowledgeRecord` schema, the ingestion API contract, and the retrieval query interface — including a short note on how Module 2/4's future integration would call this module. Get this right before implementation.
3. **Storage layer**: persistent schema, soft-archive mechanics (no hard deletes). Unit tests.
4. **Ingestion API**: idempotent capture, versioning/superseding. Unit tests.
5. **Retrieval engine**: structured filtering + semantic similarity search. Tests against a fixture history with known-expected matches.
6. **Reviewer-facing search interface**: API (and simple UI if straightforward given the stack).
7. **Retention/archival config**: config-driven placeholder rules, clearly flagged for compliance confirmation.
8. **Tests + README**: end-to-end ingestion-then-retrieval test, plus a README explaining the schema, how to run Module 7 standalone against fixtures, the outstanding integration work needed in Modules 2/4 to wire this module in live, and the retention-policy placeholder caveat.

## Assumptions & Ambiguity

Where anything here is underspecified, pick a sensible default, implement it, and note the assumption in the README — except for genuine architectural forks, anything touching Module 1-6's existing files, or actual retention-period values, where you should stop and ask me first (or, for retention periods, clearly mark as placeholder pending compliance input).

## Definition of Done

- [ ] Folder/venv setup mirrors Modules 1-6 conventions and stays fully isolated from all of them
- [ ] No record is ever hard-deleted — superseded records remain retrievable for audit
- [ ] Ingestion is idempotent and versions records instead of overwriting
- [ ] Retrieval combines structured filtering and semantic similarity, with results ranked and contextualized
- [ ] Retrieval is clearly framed as reference context for the reviewer, never an auto-decision
- [ ] Access to historical records extends Module 2's existing RBAC approach
- [ ] Retention rules are config-driven and explicitly flagged as placeholders pending compliance confirmation
- [ ] Ingestion/retrieval APIs are documented cleanly enough for a future pass to wire Modules 2 and 4 into this repository
- [ ] Unit + integration tests pass, including idempotency, soft-archive, and retrieval-relevance cases
- [ ] README documents the schema, how to run it, and the outstanding integration work in Modules 2/4
