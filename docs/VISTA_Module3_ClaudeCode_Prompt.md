# Prompt for Claude Code — VISTA Module 3: Adverse Media Screening Engine

> Paste everything below this line into Claude Code, working inside the project root: `C:\Users\tongc\claude_base\vista`

---

## Role

You are the lead engineer building **VISTA (Vendor Intelligence Screening & Trust Assessment)**, an AI-powered Vendor Risk Intelligence Platform for a bank's Know Your Vendor (KYV) process. VISTA is being built module by module in this repo (`C:\Users\tongc\claude_base\vista`), which already contains **Module 1 (Digital Intake & Entity Extraction)** and **Module 2 (Unified Screening Intelligence View)**, each in its own folder with its own virtual environment.

**This task covers only Module 3: the Adverse Media Screening Engine.** Do not modify Module 1 or Module 2's code.

### Before writing any code

1. Open `module1/` and `module2/` and inspect their conventions: language/framework, folder layout, coding style, linter/formatter config, how each defines its data schemas, how each documents itself (README structure), and — critically — how each sets up its virtual environment and `requirements.txt`.
2. Match those conventions for Module 3 wherever reasonable, so the three modules feel like parts of one system rather than three unrelated projects. If Module 1 and Module 2 conflict with each other on some convention, tell me and ask which to follow.
3. Summarize what you found and the folder/venv plan you intend to use for Module 3, and wait for my confirmation before proceeding.

## Product Context

KYV screening today is manual: reviewers search CTOS, NetReveal, adverse news sources, and public records one at a time, then reconcile results by hand. Module 2 already aggregates raw hits from all of those sources — including adverse news — into a unified per-entity view. **Module 3 takes the adverse-news slice of that output and does the actual risk analysis on it**: matching against an approved keyword library, applying a risk taxonomy, and categorizing findings so reviewers see *why* something matters, not just that an article was found.

## Module 3 Objective

Build the **Adverse Media Screening Engine**: given an entity's adverse-news hits (from Module 2), analyze each one against an approved keyword library and risk taxonomy, and produce categorized, explainable risk findings across themes such as financial crime, sanctions, fraud, regulatory breaches, tax offences, ESG concerns, and operational risks.

## Input: Adverse-News Results from Module 2

Module 3 consumes the adverse-news subset of Module 2's `ScreeningResult` output. Treat Module 2's actual schema as source of truth — go read it in `module2/` rather than assuming. If it roughly matches this shape, build against it; if it differs, adapt and note the difference:

```json
{
  "entity_id": "string",
  "source": "adverse_news",
  "query_timestamp": "datetime",
  "hits": [
    {
      "headline": "string",
      "publication": "string",
      "publish_date": "date",
      "url": "string",
      "excerpt": "string",
      "raw_match_reason": "string"
    }
  ],
  "hit_count": "integer"
}
```

Module 3 should be able to run against **live output pulled from Module 2** (same DB/API, read-only) and also against **standalone fixture files**, so its keyword-matching logic can be tested in isolation without spinning up Module 2.

## Core Capabilities

1. **Keyword Library & Risk Taxonomy (config-driven)**
   - Store the approved keyword library and risk taxonomy as an editable config file (JSON or YAML), not hardcoded in logic — this needs to be maintainable by compliance/risk staff who aren't engineers.
   - Each keyword/phrase maps to one or more risk themes: `financial_crime`, `sanctions`, `fraud`, `regulatory_breach`, `tax_offence`, `esg`, `operational`.
   - Support multiple keywords/phrases per theme and allow a keyword to belong to more than one theme.
   - Ship a starter library with realistic sample entries per theme so the system is testable immediately.

2. **AI-Driven Adverse Media Analysis**
   - For each adverse-news hit, use an LLM to assess relevance and categorize it against the taxonomy — not just naive keyword string-matching, since headlines/excerpts need contextual judgment (e.g. "fraud" in a headline about a company being a *victim* of fraud is not the same risk signal as the company *committing* fraud).
   - For each categorized finding, produce: matched theme(s), a severity/confidence indicator, and a short rationale explaining the categorization — the rationale must be traceable back to the specific hit it came from (headline/excerpt + source URL), never a blended or unattributed claim.
   - Treat this as a distinct, swappable service (mirroring Module 2's `SummaryGenerator` pattern) so the prompt/model can be iterated on independently of the taxonomy-matching logic.

3. **Deduplication & Relevance Filtering**
   - Collapse duplicate/near-duplicate articles about the same event (common with adverse news — many outlets republish the same story).
   - Filter out clearly irrelevant matches (e.g. keyword hit on an unrelated entity with a similar name) before they reach the AI categorization step, to save cost and noise.

4. **Structured Output for Downstream Use**
   - Output a per-entity list of categorized findings: theme, severity, confidence, source hit reference, rationale.
   - This feed will be consumed next by Module 4 (False Positive & True Hit Triage) — keep the output schema stable and documented, and expose it via a clean function/API rather than something embedded in UI logic. You are not building Module 4 now, just don't block it.

## Technical Requirements

- **Environment setup — align with Module 1/2, isolate from both**:
  - Create Module 3 in its own `module3/` folder with its **own virtual environment** (`module3/.venv`) and its own `requirements.txt`.
  - Use the **same Python version** as Module 1 and Module 2 for compatibility, but do not install Module 3's dependencies into either module's environment, and do not install Module 1/2's dependencies into Module 3's.
  - Add `module3/.venv/` to `.gitignore` if not already covered by a root-level ignore rule.
- **Stack**: match Module 2's backend framework choice if it's suitable for this (likely yes, since this is a similar analysis-service pattern). If Module 2 used FastAPI, use FastAPI here too — state clearly if you deviate and why.
- **Testing**: unit tests for keyword/taxonomy matching (including deliberately tricky cases: negation, victim-vs-perpetrator framing, near-miss name matches) and for deduplication logic; at least one integration test that goes from a fixture set of adverse-news hits through to categorized findings.

## Build Plan (work in this order; check in after each phase with a brief summary before continuing)

1. **Inspection pass**: review Module 1 and Module 2 conventions as described above; propose Module 3's folder structure and venv setup; wait for confirmation.
2. **Design pass**: propose the keyword/taxonomy config schema and the `AdverseMediaFinding` output schema. Get this right before writing implementation code.
3. **Keyword library & taxonomy loader**: config file + starter data + loader/validator.
4. **Matching & filtering logic**: dedup, relevance filtering, candidate keyword matches. Unit tests, including the tricky cases above.
5. **AI categorization service**: LLM-based theme assignment with rationale and source attribution. Tests against fixtures with known-correct categorizations.
6. **Integration point**: function/API that reads Module 2's adverse-news output (or fixture files) and returns categorized findings for an entity.
7. **Tests + README**: end-to-end test, plus a README explaining the taxonomy config format, how to add new keywords/themes, how to run Module 3 standalone against fixtures, and how it connects to Module 2's live output.

## Assumptions & Ambiguity

Where anything here is underspecified, pick a sensible default, implement it, and note the assumption in the README rather than stopping to ask — except for genuine architectural forks (e.g. a stack mismatch with Module 1/2) or anything touching Module 1/2's existing files, where you should stop and ask me first.

## Definition of Done

- [ ] Folder/venv setup mirrors Module 1/2 conventions and stays fully isolated from both
- [ ] Keyword library and risk taxonomy are config-driven and editable without code changes
- [ ] Adverse-news hits are deduplicated and filtered before AI categorization
- [ ] AI categorization produces theme, severity/confidence, and a source-attributed rationale for every finding
- [ ] Module 3 runs both against Module 2's live output and against standalone fixtures
- [ ] Output schema is documented and stable for Module 4 to consume later
- [ ] Unit + integration tests pass, including tricky-case coverage for the taxonomy matcher
- [ ] README documents the taxonomy config format, how to run it, and how it connects to Module 2
