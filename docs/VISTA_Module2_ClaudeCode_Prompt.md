# Prompt for Claude Code — VISTA Module 2: Unified Screening Intelligence View

> Paste everything below this line directly into Claude Code as your task instructions.

---

## Role

You are the lead engineer building **VISTA (Vendor Intelligence Screening & Trust Assessment)**, an AI-powered Vendor Risk Intelligence Platform for a bank's Know Your Vendor (KYV) process. VISTA is being built module by module. **This task covers only Module 2: the Unified Screening Intelligence View ("Screening Intelligence Hub").** Do not build other modules, but design Module 2's interfaces so those modules can plug in later (see "Forward Compatibility" below).

If this repository already contains scaffolding, conventions, or a data model from a prior module (e.g. Module 1: Digital Intake & Entity Extraction), **inspect the existing code first and follow its stack, folder structure, and coding conventions** instead of the defaults below. If the repo is empty, use the defaults in this prompt.

## Product Context

KYV screening today is manual: reviewers search CTOS, NetReveal, adverse news sources, and public records one at a time, then reconcile the results by hand before assessing risk. Module 2's job is to remove that manual reconciliation step by pulling every source into **one unified view per vendor/entity**, with an AI-generated synthesis on top, so reviewers spend their time on judgment rather than searching.

## Module 2 Objective

Build the **Screening Intelligence Hub**: a service + UI that, given a vendor entity (vendor, director, shareholder, or UBO), automatically aggregates screening data from multiple sources into a single structured view, and generates an AI summary that highlights what a reviewer actually needs to know.

## Input: Vendor Entity Profile

Assume Module 1 produces a unified entity profile in roughly this shape (adjust if the repo already defines this schema — treat that as source of truth instead):

```json
{
  "entity_id": "string",
  "entity_type": "vendor | director | shareholder | ubo",
  "legal_name": "string",
  "aliases": ["string"],
  "id_numbers": [{ "type": "SSM_NO | NRIC | PASSPORT", "value": "string" }],
  "nationality": "string",
  "date_of_incorporation_or_birth": "date",
  "related_entities": [{ "entity_id": "string", "relationship": "string" }]
}
```

## Data Sources to Integrate

- **CTOS** — credit/business risk reports
- **NetReveal** — prior screening/watchlist hits
- **Previous KYV reviews** — internal historical review outcomes
- **Adverse news sources** — negative media mentions
- **Public records** — registries, litigation, sanctions lists

Real credentials/APIs for these are **not available in this environment**. Build against a `ScreeningConnector` interface with one implementation per source, and ship a **mock provider** for each that returns realistic, varied sample data (including some "no hits," some "false-positive-shaped" hits, and some genuine high-risk hits) so the rest of the system can be developed and tested end-to-end. Structure each mock provider so swapping in a real API client later requires no changes outside that one file.

## Core Capabilities

1. **Aggregation Engine**
   - Given an `entity_id`, query all five connectors concurrently.
   - Normalize each source's response into a common `ScreeningResult` schema (source, query timestamp, raw hits, hit count, risk category tags, confidence/match-quality indicator, source-specific metadata).
   - Handle partial failures gracefully (e.g. one source times out) — the aggregation must still return results from the sources that succeeded, with a clear status per source.
   - Cache results per entity with a configurable TTL so repeat views don't re-query unchanged sources; expose a manual "refresh this source" action.

2. **AI-Generated Summary**
   - Given the aggregated `ScreeningResult` set for an entity, call an LLM to produce a structured summary: a short narrative overview, a list of notable findings grouped by risk theme (financial crime, sanctions, fraud, regulatory breach, tax, ESG, operational), and an explicit list of what data is *missing or inconclusive*.
   - The summary must always cite which source each finding came from — never blend sources into an unattributed claim.
   - Treat this as a distinct, swappable service (`SummaryGenerator`) so the prompt/model can be iterated on independently of the aggregation logic.

3. **Unified View UI**
   - One screen per entity: a combined summary at the top, and a per-source tab/section below (CTOS, NetReveal, Prior KYV, Adverse News, Public Records) so a reviewer can always drill into raw source data.
   - Each finding shows: source, date retrieved, staleness (e.g. "queried 3 days ago"), and match-confidence indicator.
   - A search/filter view listing all screened entities, with status badges (clear / hits found / needs refresh / source unavailable).
   - Clear visual distinction between "AI-generated synthesis" and "raw source data" — reviewers must never mistake one for the other.

4. **Audit Trail**
   - Log every screening query (who ran it, entity, sources queried, timestamp) and every view of results.
   - This is a banking control system — assume audit logging is a hard requirement, not an afterthought.

## Forward Compatibility (for later modules — do not implement, just don't block)

- Module 3 (Adverse Media Screening Engine) will consume this module's adverse-news `ScreeningResult` records as input — keep that schema stable and documented.
- Module 4 (False Positive & True Hit Triage) will consume the full aggregated result set — expose it via a clean internal API/function, not something buried in UI logic.
- Module 7 (Vendor Risk Knowledge Repository) will eventually read historical aggregation runs — don't hard-delete old results; soft-archive instead.

## Repository Structure & Separation from Module 1

This repo already contains Module 1's script and documentation. **Module 2 must be kept fully separate for easy independent review** — do not modify, refactor, or move any existing Module 1 files.

- If Module 1's files are not already isolated in their own folder, **stop and ask me before touching them**. Propose a folder layout (e.g. `module1/` and `module2/` as siblings) and wait for confirmation rather than reorganizing on your own.
- All new Module 2 code, tests, and docs go in a new `module2/` directory.
- If Module 2 needs to read Module 1's output (the unified entity profile), treat that as a **read-only dependency** — import/reference it, don't inline or duplicate Module 1's logic.
- If a genuinely shared piece is needed (e.g. a common schema both modules use), propose putting it in a `shared/` folder and ask before creating it.
- End your first response with a short summary of the folder layout you're using, before writing any code.

## Technical Requirements

- **Stack** (use if repo is empty): Backend in Python (FastAPI) or Node (Express/Nest) — your choice, state which and why. Frontend in React/Next.js. Postgres for storage. Pick whichever pairing lets you move fastest; document the choice in the README.
- **Security**: this handles PII and financial-crime-relevant data. Design for encryption at rest, role-based access control (reviewer vs. admin), and no secrets in code. Mock connectors should still go through an auth-stub layer that mirrors how real credentials would be injected later.
- **Performance**: aggregation for one entity should complete in a few seconds against mocks; design the connector calls to run in parallel, not sequentially.
- **Testing**: unit tests for the aggregation engine (including partial-failure handling) and the connector normalization logic; at least one integration test that goes from entity_id → aggregated results → AI summary.

## Build Plan (work in this order; check in after each phase with a brief summary before continuing)

1. **Design pass**: propose the schema for `ScreeningResult`, the `ScreeningConnector` interface, and the folder structure. Get this right before writing implementation code.
2. **Data models & mock connectors**: implement the five mock providers with varied sample data.
3. **Aggregation engine**: concurrent querying, normalization, caching, partial-failure handling, audit logging. Unit tests.
4. **AI summarization service**: prompt design, structured output parsing, source attribution. Tests with at least one "genuinely risky" and one "clean" entity fixture.
5. **API layer**: endpoints to trigger aggregation, fetch cached results, force refresh, fetch summary, list entities.
6. **Frontend**: entity list view, unified entity detail view with per-source tabs and AI summary panel.
7. **Integration test + README**: end-to-end flow, plus a README explaining how to run it, how mock connectors work, and what would need to change to point at real CTOS/NetReveal APIs.

## Assumptions & Ambiguity

Where anything in this spec is underspecified, pick a sensible default, implement it, and note the assumption in the README rather than stopping to ask — except where a real credential, real API contract, or a genuine architectural fork (e.g. which language/framework) is needed, in which case state your choice explicitly and proceed.

## Definition of Done

- [ ] All five mock connectors return realistic, varied data through a common interface
- [ ] Aggregation engine handles concurrent queries and partial source failure without crashing
- [ ] AI summary is generated per entity, source-attributed, and clearly separated from raw data in the UI
- [ ] Reviewer can view a single entity's full screening picture without leaving one screen
- [ ] Every query and view is audit-logged
- [ ] Unit + integration tests pass
- [ ] README documents architecture, how to run it, and the path to swapping in real APIs
