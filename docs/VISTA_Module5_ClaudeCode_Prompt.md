# Prompt for Claude Code — VISTA Module 5: Risk Assessment & EDD Recommendation

> Paste everything below this line into Claude Code, working inside the project root: `C:\Users\tongc\claude_base\vista`

---

## Role

You are the lead engineer building **VISTA (Vendor Intelligence Screening & Trust Assessment)**, an AI-powered Vendor Risk Intelligence Platform for a bank's Know Your Vendor (KYV) process. VISTA is being built module by module in this repo (`C:\Users\tongc\claude_base\vista`), which already contains:

- **Module 1** — Digital Intake & Entity Extraction
- **Module 2** — Unified Screening Intelligence View (aggregates CTOS, NetReveal, prior KYV reviews, adverse news, public records)
- **Module 3** — Adverse Media Screening Engine (categorizes adverse-news hits against a risk taxonomy)
- **Module 4** — Risk Signal Intelligence Engine (triages findings into false-positive vs. needs-review, with confidence scores)

**This task covers only Module 5: the Risk Assessment Engine (Risk Assessment & EDD Recommendation).** Do not modify Module 1, 2, 3, or 4's code.

### Before writing any code

1. Open `module1/`, `module2/`, `module3/`, and `module4/` and inspect their conventions: language/framework, folder layout, coding style, schema definition patterns, README structure, and venv/`requirements.txt` setup.
2. Match those conventions for Module 5. If prior modules conflict with each other, tell me and ask which to follow rather than picking one yourself.
3. Summarize your findings and the folder/venv plan for Module 5, and wait for my confirmation before proceeding.

## Product Context

Module 4 tells a reviewer which findings are likely noise and which genuinely warrant attention, with a confidence score and rationale for each. It does not, however, translate that into an actual risk decision — a reviewer still has to manually weigh the surviving findings against the bank's KYV policy, decide how material each one is, assign an overall risk rating, and work out what level of Enhanced Due Diligence (EDD), if any, is required.

**Module 5's job is to do that first-pass policy evaluation**: take the prioritized findings from Module 4, evaluate them against KYV governance rules, and produce a draft risk rating, a materiality justification, and an EDD recommendation — so the reviewer is editing and approving a well-reasoned draft instead of starting from a blank page.

## Module 5 Objective

Build the **Risk Assessment Engine**: given an entity's triaged findings (from Module 4), evaluate them against a configurable KYV policy/governance rule set to produce a draft overall risk rating, a materiality justification explaining which findings drove that rating and why, and an EDD recommendation — all fully traceable back to specific findings and policy rules.

## Hard Requirement: This Module Drafts, It Does Not Approve

- Module 5 produces a **draft** risk assessment, never a final, approved one. Every output must be clearly labeled as AI-drafted and pending reviewer review/approval under the existing Maker-Checker framework.
- The reviewer retains final accountability for the risk rating and EDD decision. Nothing in this module should be built in a way that implies auto-approval is possible or intended.
- Every draft, and every subsequent reviewer edit or override of it, must be logged — this history is valuable input for Module 7's knowledge repository later, and for audit.
- Risk assessment drafts are sensitive (the source document marks this area "Confidential") — access to draft assessments should be restricted to authorized reviewer/approver roles, consistent with the RBAC approach already established in Module 2.

## Inputs

Module 5 consumes Module 4's output. Treat the actual schema in `module4/` as source of truth — read it rather than assuming. Roughly: a ranked list of findings per entity, each with match-quality sub-scores, historical outcome signal, confidence score, and disposition recommendation (`likely_false_positive` / `needs_review` / `high_priority_review`).

It should also have access to the entity profile (originally from Module 1, carried through Module 2) for context — entity type, relationships, jurisdiction, etc., since some policy rules depend on entity attributes, not just findings.

Module 5 should be runnable against **live output from Module 4** (read-only) and against **standalone fixture files**.

## Core Capabilities

1. **KYV Policy & Governance Rule Library (config-driven)**
   - Store the bank's KYV policy rules as an editable config file (JSON or YAML), not hardcoded — this needs to be maintainable by compliance/risk staff, mirroring Module 3's approach to the keyword/taxonomy library.
   - Rules should map combinations of risk theme, severity, confidence, and entity attributes to: a risk rating contribution (e.g. low/medium/high), a materiality guidance note, and an EDD requirement (e.g. standard due diligence, enhanced due diligence with specific required steps, senior management escalation).
   - Ship a starter rule set with realistic sample rules covering each risk theme from Module 3 (financial crime, sanctions, fraud, regulatory breach, tax offence, ESG, operational).

2. **Deterministic Rule Evaluation Layer**
   - Evaluate an entity's Module 4 findings against the rule library and produce a list of **which rules matched, on which findings, and why** — this should be deterministic and testable, not left to the LLM, mirroring how Module 4 kept entity-resolution scoring deterministic and reserved the LLM for reasoning over the results.
   - `likely_false_positive` findings from Module 4 should generally be weighted down or excluded from rule triggers, but never silently dropped from the record — keep them visible in the draft for context.

3. **AI-Driven Materiality Justification & Narrative**
   - Given the matched rules and their triggering findings, use an LLM to synthesize a coherent materiality justification: why the surviving risk findings do or don't matter enough to affect the vendor relationship, referencing specific findings and the policy rules that applied.
   - Produce an overall draft risk rating and EDD recommendation as structured output, plus the narrative justification as readable text.
   - The narrative must cite specific finding references and rule IDs — never an unattributed judgment. Treat this as a distinct, swappable service, consistent with the pattern used in Modules 2-4.

4. **Structured Draft Output**
   - Output structure (adapt once you've reviewed Module 4's actual schema):

     ```json
     {
       "entity_id": "string",
       "draft_status": "ai_drafted | reviewer_edited | approved",
       "overall_risk_rating": "low | medium | high",
       "matched_rules": [
         {
           "rule_id": "string",
           "triggering_finding_references": ["string"],
           "contribution": "string, e.g. 'raises rating to medium due to unresolved sanctions-theme hit'"
         }
       ],
       "materiality_justification": "string, citing specific findings and rule_ids",
       "edd_recommendation": {
         "level": "standard | enhanced | senior_escalation",
         "required_steps": ["string"]
       },
       "contributing_findings": ["finding_reference"],
       "excluded_findings": ["finding_reference (likely false positives, kept visible but excluded from rating)"]
     }
     ```

5. **Integration Point**
   - Expose this as a clean function/API that takes an `entity_id`, pulls the relevant Module 4 data, and returns the draft risk assessment. This will be consumed next by Module 6 (Smart KYV Report Generation) — keep the output schema stable and documented, but do not build Module 6 now.

## Technical Requirements

- **Environment setup — align with Modules 1-4, isolate from all four**:
  - Create Module 5 in its own `module5/` folder with its **own virtual environment** (`module5/.venv`) and its own `requirements.txt`.
  - Use the **same Python version** as the prior modules, but do not cross-install dependencies in either direction.
  - Add `module5/.venv/` to `.gitignore` if not already covered.
- **Stack**: match the prior modules' backend framework choice unless there's a clear reason not to — state explicitly if you deviate.
- **Access control**: draft risk assessments should only be readable/writable by authorized reviewer/approver roles — extend whatever RBAC approach Module 2 established rather than inventing a new one.
- **Testing**: unit tests for the rule-matching logic (including cases with no rule matches, single-rule matches, and multiple overlapping rule matches that should combine into a higher rating) and for the false-positive exclusion logic. At least one integration test going from a fixture set of Module 4 findings through to a complete draft risk assessment.

## Build Plan (work in this order; check in after each phase with a brief summary before continuing)

1. **Inspection pass**: review Module 1-4 conventions; propose Module 5's folder structure and venv setup; wait for confirmation.
2. **Design pass**: propose the policy/governance rule config schema and the `RiskAssessmentDraft` output schema. Get this right before implementation.
3. **Rule library & loader**: config file + starter rule set + loader/validator.
4. **Deterministic rule evaluation engine**: matching findings against rules, handling overlapping matches and false-positive exclusion. Unit tests.
5. **AI materiality justification & narrative service**: synthesis of matched rules + findings into a cited narrative, risk rating, and EDD recommendation. Tests against fixtures with known-correct expected ratings.
6. **Draft versioning**: track draft status, capture reviewer edits/overrides for audit.
7. **Integration point**: function/API taking an `entity_id` through to a complete draft risk assessment.
8. **Tests + README**: end-to-end test, plus a README explaining the rule config format, how to add new rules, how to run Module 5 standalone against fixtures, how it connects to Module 4, and an explicit note that its output is a draft pending reviewer approval.

## Assumptions & Ambiguity

Where anything here is underspecified, pick a sensible default, implement it, and note the assumption in the README — except for genuine architectural forks or anything touching Module 1-4's existing files, where you should stop and ask me first.

## Definition of Done

- [ ] Folder/venv setup mirrors Modules 1-4 conventions and stays fully isolated from all of them
- [ ] Policy/governance rules are config-driven and editable without code changes
- [ ] Rule matching is deterministic, testable, and handles overlapping-rule cases explicitly
- [ ] Likely-false-positive findings are excluded from rating but remain visible in the draft
- [ ] Materiality justification cites specific findings and rule IDs — never an unattributed claim
- [ ] All outputs are clearly labeled as drafts pending reviewer approval
- [ ] Draft history (including reviewer edits/overrides) is logged for audit
- [ ] Access to draft assessments is restricted to authorized roles
- [ ] Output schema is documented and stable for Module 6 to consume later
- [ ] Unit + integration tests pass, including overlapping-rule and exclusion cases
- [ ] README documents the rule config format, how to run it, and how it connects to Module 4
