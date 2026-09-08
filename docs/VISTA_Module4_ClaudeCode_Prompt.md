# Prompt for Claude Code — VISTA Module 4: False Positive & True Hit Triage

> Paste everything below this line into Claude Code, working inside the project root: `C:\Users\tongc\claude_base\vista`

---

## Role

You are the lead engineer building **VISTA (Vendor Intelligence Screening & Trust Assessment)**, an AI-powered Vendor Risk Intelligence Platform for a bank's Know Your Vendor (KYV) process. VISTA is being built module by module in this repo (`C:\Users\tongc\claude_base\vista`), which already contains:

- **Module 1** — Digital Intake & Entity Extraction
- **Module 2** — Unified Screening Intelligence View (aggregates CTOS, NetReveal, prior KYV reviews, adverse news, public records)
- **Module 3** — Adverse Media Screening Engine (categorizes adverse-news hits against a risk taxonomy)

**This task covers only Module 4: the Risk Signal Intelligence Engine (False Positive & True Hit Triage).** Do not modify Module 1, 2, or 3's code.

### Before writing any code

1. Open `module1/`, `module2/`, and `module3/` and inspect their conventions: language/framework, folder layout, coding style, schema definition patterns, README structure, and venv/`requirements.txt` setup.
2. Match those conventions for Module 4. If prior modules conflict with each other on some convention, tell me and ask which to follow rather than picking one yourself.
3. Summarize your findings and the folder/venv plan for Module 4, and wait for my confirmation before proceeding.

## Product Context

Module 2 pulls raw hits from five sources into one view. Module 3 adds risk-theme categorization to the adverse-news hits specifically. Neither module tells a reviewer whether a given hit is a **genuine risk or a false positive** — that judgment call is still manual today, and it's where reviewers currently spend most of their time (a common name match, a director who shares a name with someone on a watchlist, an article about an unrelated company, etc.).

**Module 4's job is to do the entity-resolution and pattern-analysis legwork that lets a reviewer see, at a glance, which findings are almost certainly noise and which ones genuinely warrant attention** — without ever making that final call itself. This system supports a Maker-Checker control; a human always retains final accountability.

## Module 4 Objective

Build the **Risk Signal Intelligence Engine**: given an entity's full screening findings (from Module 2's aggregated results and Module 3's categorized adverse-media findings), evaluate each finding using entity-resolution signals (name variation, nationality, ID match, ownership/corporate relationships) and historical screening outcomes, and produce a confidence score, a triage recommendation, and an explainable rationale — so reviewers can prioritize their attention instead of manually re-verifying every hit.

## Hard Requirement: This Module Recommends, It Does Not Decide

- Module 4 must never auto-dismiss or auto-clear a finding. Every output is a **recommendation** (`likely_false_positive`, `needs_review`, `high_priority_review`) that a human reviewer confirms or overrides under the existing Maker-Checker framework.
- Any UI or API response must be labeled unambiguously as AI-suggested and pending confirmation — never presented as a resolved status.
- Every recommendation must be logged with its full rationale for audit purposes, including cases where the reviewer later overrides it — that override history is valuable input for Module 7 later.

## Inputs

Module 4 consumes two upstream outputs. Treat the actual schemas in `module2/` and `module3/` as source of truth — read them rather than assuming. Roughly:

**From Module 2** — the entity's full aggregated screening results (all five sources), plus the entity profile itself (name, aliases, nationality, ID numbers, related entities/ownership structure — originally from Module 1).

**From Module 3** — categorized adverse-media findings: theme, severity, confidence, source hit reference, rationale.

Module 4 should be runnable against **live output from Module 2/3** (read-only) and against **standalone fixture files**, so entity-resolution and scoring logic can be tested in isolation.

## Core Capabilities

1. **Entity Resolution Engine**
   - Compare each finding's subject (as named/described in the raw hit) against the queried entity's known profile: legal name, aliases, nationality, ID numbers, and related entities (directors, shareholders, UBOs, corporate relationships).
   - Use fuzzy name-matching (e.g. token-based and edit-distance similarity, not just exact string match) to score name similarity, and produce explicit sub-scores: name similarity, nationality match, ID match, ownership/relationship overlap.
   - This is deterministic, testable logic — do not rely on the LLM for the similarity scoring itself, only for reasoning over the results.

2. **Historical Outcome Signal**
   - Check whether this entity (or a matching finding) has a prior KYV review outcome available from Module 2's `previous_kyv_reviews` source.
   - If a prior reviewer already marked a similar finding as a false positive or a confirmed true hit, surface that as a strong signal — but never let it silently override fresh analysis; always show both the current signals and the historical one side by side in the rationale.

3. **AI Contextual Reasoning & Confidence Scoring**
   - Combine the entity-resolution sub-scores, the historical outcome signal, and (for adverse-media findings) Module 3's theme/severity into an LLM-driven reasoning step that produces a final confidence score and a triage recommendation.
   - The rationale must explicitly name which signals drove the score (e.g. "name similarity 42%, no ID match, no ownership overlap, no prior review found → likely false positive") — never an unexplained score.
   - Treat this as a distinct, swappable service, consistent with Module 2's `SummaryGenerator` and Module 3's categorization service pattern.

4. **Prioritized Output for Reviewers**
   - Produce a ranked list of findings per entity, sorted so `high_priority_review` items surface first, with `likely_false_positive` items still visible but clearly deprioritized — never hidden entirely.
   - Output structure (adapt as needed once you've reviewed Module 2/3's actual schemas):

     ```json
     {
       "entity_id": "string",
       "finding_reference": "string (links back to the Module 2 hit or Module 3 finding)",
       "match_quality": {
         "name_similarity_score": "number 0-1",
         "nationality_match": "boolean",
         "id_match": "boolean",
         "ownership_overlap_score": "number 0-1"
       },
       "historical_outcome_signal": {
         "prior_review_found": "boolean",
         "prior_outcome": "false_positive | true_hit | unknown",
         "prior_review_date": "date | null"
       },
       "confidence_score": "number 0-100",
       "disposition_recommendation": "likely_false_positive | needs_review | high_priority_review",
       "rationale": "string, explicitly citing which signals drove the score"
     }
     ```

5. **Integration Point**
   - Expose this as a clean function/API that takes an `entity_id`, pulls the relevant Module 2 + Module 3 data, and returns the ranked triage list. This will be consumed next by Module 5 (Risk Assessment & EDD Recommendation) — keep the output schema stable and documented, but do not build Module 5 now.

## Technical Requirements

- **Environment setup — align with Module 1/2/3, isolate from all three**:
  - Create Module 4 in its own `module4/` folder with its **own virtual environment** (`module4/.venv`) and its own `requirements.txt`.
  - Use the **same Python version** as the prior modules, but do not cross-install dependencies in either direction.
  - Add `module4/.venv/` to `.gitignore` if not already covered.
- **Stack**: match the prior modules' backend framework choice unless there's a clear reason not to — state explicitly if you deviate.
- **Testing**: unit tests for the entity-resolution scoring (name similarity, nationality/ID matching, ownership overlap) with deliberately tricky cases — common names, transliteration variants, shared surnames across unrelated entities, partial ownership chains. Unit tests for the historical-outcome lookup. At least one integration test going from a fixture set of Module 2/3 findings through to a ranked triage output.

## Build Plan (work in this order; check in after each phase with a brief summary before continuing)

1. **Inspection pass**: review Module 1/2/3 conventions; propose Module 4's folder structure and venv setup; wait for confirmation.
2. **Design pass**: propose the `TriageResult` output schema and the match-quality sub-scoring approach. Get this right before implementation.
3. **Entity resolution engine**: name similarity, nationality/ID matching, ownership/relationship overlap scoring. Unit tests with tricky cases.
4. **Historical outcome lookup**: read prior KYV review outcomes from Module 2's source (or fixtures). Unit tests.
5. **AI reasoning & scoring service**: combine all signals into a confidence score and rationale. Tests against fixtures with known-correct expected dispositions.
6. **Prioritized output & integration point**: ranking logic, function/API taking an `entity_id` through to a ranked triage list.
7. **Tests + README**: end-to-end test, plus a README explaining the scoring approach, how to run Module 4 standalone against fixtures, how it connects to Module 2/3, and an explicit note that its output is a recommendation, not a decision.

## Assumptions & Ambiguity

Where anything here is underspecified, pick a sensible default, implement it, and note the assumption in the README — except for genuine architectural forks or anything touching Module 1/2/3's existing files, where you should stop and ask me first.

## Definition of Done

- [ ] Folder/venv setup mirrors Module 1/2/3 conventions and stays fully isolated from all three
- [ ] Entity resolution produces explicit, testable sub-scores (name, nationality, ID, ownership) — not a black-box single number
- [ ] Historical outcome signal is surfaced, not silently applied
- [ ] Every confidence score has a rationale explicitly citing the signals that drove it
- [ ] Findings are ranked, never hidden — including low-confidence "likely false positive" items
- [ ] All outputs are clearly labeled as recommendations pending human confirmation
- [ ] Every triage recommendation is logged for audit, including later reviewer overrides
- [ ] Output schema is documented and stable for Module 5 to consume later
- [ ] Unit + integration tests pass, including tricky entity-resolution cases
- [ ] README documents the scoring approach, how to run it, and how it connects to Module 2/3
