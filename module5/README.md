# VISTA Module 5 — Risk Assessment Engine (Risk Assessment & EDD Recommendation)

Given an entity's triaged findings (Module 4), evaluates them against a configurable KYV policy
rule set to produce a draft overall risk rating, a materiality justification citing specific
findings and rule IDs, and an Enhanced Due Diligence (EDD) recommendation — so a reviewer edits
and approves a well-reasoned draft instead of starting from a blank page.

## Hard requirement: this module drafts, it does not approve

Every `RiskAssessmentDraft` carries a constant `label` field ("AI-drafted — pending reviewer
review and approval, not a final assessment") and an explicit `draft_status`
(`ai_drafted -> reviewer_edited -> approved`) so no caller can present a draft as final by
accident. Approving a draft (`POST .../approve`) requires the `approver` or `admin` role — a
plain `reviewer` can view and edit but never self-approve. Every draft, edit, and approval is
persisted for audit (see "Persistence" below).

## Stack

Matches Modules 2–4: Python + FastAPI + Pydantic v2, `pytest`/`pytest-asyncio`, own venv and
`requirements.txt`, fully isolated from Modules 1–4. Needs SQLAlchemy + its own SQLite database
(like Module 4, unlike stateless Module 3) for draft/edit/approval history.

## Access control

Extends Module 2's RBAC approach (`reviewer | admin`) rather than inventing a new one, adding
`approver`: risk assessment drafts are Maker-Checker, so a reviewer can draft/edit but only an
approver (or admin) can approve. `GET`/`edit`/`history` require any of `reviewer | approver |
admin`; `approve` requires `approver | admin`. This is a role-based gate only — it does not verify
the approver is a *different person* from whoever last edited the draft (see Assumptions).

## Architecture

```
module5/
├── config/
│   └── policy_rules.yaml      # editable KYV governance rule library (compliance-owned)
├── app/
│   ├── core/                  # config.py, time.py, auth.py (Role: reviewer|approver|admin)
│   ├── schemas/
│   │   ├── entity.py          # EntityProfile — own copy of the Module 1->2 contract
│   │   ├── upstream.py        # TriageResultIn (Module 4's output, adapted) + EnrichedFinding
│   │   │                      # (Module 5's own addition — see "Theme enrichment" below)
│   │   ├── policy.py          # PolicyRule, RuleMatchCriteria — the rule config contract
│   │   └── assessment.py      # RiskAssessmentDraft, MatchedRule — the stable Module
│   │                          # 6-facing output contract
│   ├── db/                    # base.py, session.py (own risk_assessment.db)
│   ├── models/assessment.py   # RiskAssessmentDraftRecord, DraftHistoryRecord (soft-archived)
│   ├── policy/loader.py       # loads + validates config/policy_rules.yaml
│   ├── services/
│   │   ├── entity_lookup.py       # reads module1's vista.db (or fixtures) -> EntityProfile
│   │   ├── triage_source.py       # reads module4's triage.db (or fixtures)
│   │   ├── theme_enrichment.py    # recovers risk theme per finding (see below)
│   │   ├── rule_engine.py         # deterministic: matches findings against rules, combines
│   │   │                          # overlapping matches, excludes false positives
│   │   ├── narrative_service.py   # AI materiality justification (ABC) + Anthropic impl +
│   │   │                          # deterministic fallback
│   │   ├── assessment_engine.py   # orchestrates: gather -> enrich -> match -> narrate
│   │   └── audit_service.py       # persists every draft + every edit/approval
│   ├── api/routes/
│   │   ├── assessment.py      # GET /api/entities/{id}/risk-assessment (role-gated)
│   │   └── review.py          # POST .../edit, POST .../approve (approver+ only), GET .../history
│   └── main.py
├── fixtures/                  # standalone entities + triage results + theme-lookup data
└── tests/
```

## Inputs and how they're read

**Module 4** (`triage_source.py`): reads `module4/database/triage.db` directly as a plain SQLite
file — never Module 4's Python code, which runs in its own venv/process — the same read-only,
adapt-at-the-boundary pattern used at every module boundary in this repo. Returns the entity's
latest non-archived batch of `TriageResult` rows.

**Module 1** (via `entity_lookup.py`): resolves the queried entity's profile (type, nationality,
etc.) for policy rules that key on entity attributes, reading `module1/database/vista.db`
directly, the same way Module 2/4 do.

### Theme enrichment — a real gap, worked around

Module 4's `FindingSummary` (what `triage_source.py` reads) carries `source`, `headline`,
`excerpt`, `severity` — **but no risk theme**, from either Module 2's `risk_categories` or Module
3's `themes`. This was discovered while building Module 5: rule-matching explicitly needs to key
on theme, and Module 4 can't be modified. `theme_enrichment.py` recovers it by parsing Module 4's
`finding_reference` and reading the *original* hit/finding one hop further back:

- **`module2:{source}:{result_id}:{hit_id}`** references: a direct, reliable lookup — `result_id`
  and `hit_id` are stable, persisted ids in Module 2's `screening.db`, so this reads the exact hit
  and returns its `risk_categories`.
- **`module3:{finding_id}`** references: a second gap. Module 3 is stateless and regenerates a
  fresh `finding_id` (and `hit_id`) on *every* call (see
  `module3/app/services/categorization_service.py`), so the `finding_id` captured in Module 4's
  persisted record will almost never match a live Module 3 call's output — only Module 3's
  *content* is deterministic, not its generated ids. Matched by the finding's `headline` instead
  (which Module 4's `FindingSummary` does persist verbatim), calling Module 3's live API
  (`http://localhost:8001` by default) or falling back to fixtures. If no headline match is found
  (e.g. the underlying adverse-news data changed since the original triage run), themes come back
  empty rather than erroring — a themeless finding just can't trigger a theme-scoped rule, which
  is correct, conservative behavior for a compliance tool.

Both Module 2 and Module 3 reads fall back to `fixtures/` automatically when unavailable, so
Module 5 runs and tests fully standalone with no other module's server running (Module 3's live
call is a nice-to-have refinement, not a requirement, precisely because of this fallback).

## Rule config format

`config/policy_rules.yaml` is owned by compliance/risk staff — no code changes needed to add or
adjust a rule. Structure:

```yaml
rules:
  - rule_id: "SANCTIONS-01"
    description: "..."
    match:
      themes: [sanctions]              # empty/omitted = any theme
      min_severity: high                # low|medium|high floor; omit for none
      min_confidence_score: 60          # 0-100 floor on Module 4's confidence_score
      min_disposition: high_priority_review  # needs_review|high_priority_review floor
      entity_types: [vendor]             # empty/omitted = any
      nationalities: []                  # empty/omitted = any
    rating_contribution: high            # low|medium|high
    materiality_note: "..."
    edd:
      level: senior_escalation           # standard|enhanced|senior_escalation
      required_steps: ["...", "..."]
```

`likely_false_positive` findings never reach rule matching at all (excluded before evaluation
starts) but stay visible in the draft's `excluded_findings`. **Overlapping rule matches combine to
the highest rating and EDD level among them** (never averaged, never first-match-wins);
`required_steps` in the final draft is the deduplicated union across every matched rule, not just
the ones at the winning level.

## Scoring approach

**Rule evaluation (`rule_engine.py`) is deterministic, not LLM-driven** — per the spec, explicitly
mirroring how Module 4 kept entity-resolution scoring deterministic. The overall
`overall_risk_rating` and `edd_recommendation` are decided entirely by `combine_rule_matches()`,
*before* the AI narrative step runs.

**Narrative (`narrative_service.py`)** is the LLM's only job here: given the already-matched rules
and already-decided rating/EDD, produce a short, cited materiality justification — it does not
propose a different rating. This is narrower than Module 4's LLM step (which does produce the
final confidence score/disposition); the spec's explicit testing requirement — "overlapping rule
matches that should combine into a higher rating" as a property of "the rule-matching logic" — is
read as meaning that combination must be deterministic and testable without an LLM in the loop,
which is also the more conservative choice for a governance-sensitive draft. Anthropic
(`claude-sonnet-5`) is checked to have actually cited at least one given rule_id before its output
is accepted; if not (or on any failure), falls back to a deterministic templated narrative that
enumerates every matched rule, its contribution, and its triggering finding references.

## Persistence

Every `GET .../risk-assessment` call runs the full pipeline fresh and **persists the draft**,
soft-archiving the entity's previous one — "every draft... must be logged" is read literally, the
same pattern Module 4 uses for triage runs. Edits and approvals are a separate, append-only
`draft_history` table and work even against an already-archived (superseded) draft — a reviewer
must always be able to explain what they changed, which is exactly the override-history input
Module 7 will want later.

## Running it

```powershell
cd module5
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8004
```

Try `GET /api/entities/{entity_id}/risk-assessment` against a real entity from your Module 1–4
setup, or the bundled fixtures (`vendor:fixture-nomatch` / `-single` / `-overlap` / `-excluded` /
`-taxvendor`, and `director:fixture-taxdirector` for the entity-attribute-gating A/B case — see
tests), which work even with Modules 1–4 never having been run.

Run the tests:

```powershell
cd module5
python -m pytest
```

**To point the narrative service at the real Anthropic API**: set `ANTHROPIC_API_KEY` (copy
`.env.example` to `.env`). Without it, every narrative comes from the deterministic fallback.

## Assumptions

- **Theme enrichment** (see above): a real, documented gap in Module 4's output schema, worked
  around by re-reading Module 2/3's original data rather than modifying Module 4.
- **Rating/EDD are deterministic, narrative is AI**: see "Scoring approach" above for the
  reasoning; noted here because it's a genuine interpretation call on an underspecified point in
  the prompt.
- **Approval RBAC is role-based only**: `require_approval_role` checks the actor's role, not
  whether they're a different person from the draft's last editor. A real deployment enforcing
  strict separation of duties would need to track and check the specific prior actor(s), which
  the current auth-stub (matching Module 2's) doesn't model.
- **Jurisdiction ≈ nationality**: `EntityProfile` has no separate jurisdiction field; policy rules
  that key on jurisdiction use `nationality` (e.g. "Malaysia", "Singapore") as-is.
- **No caching**: like Module 4, every GET recomputes fully — Module 4 already caches/audits the
  underlying triage data, so re-adding caching here seemed like unnecessary duplication for a
  stateless-per-request analysis pass over already-cached data.
