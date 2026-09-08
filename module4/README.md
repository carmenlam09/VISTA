# VISTA Module 4 — Risk Signal Intelligence Engine (False Positive & True Hit Triage)

Given an entity's full screening findings (Module 2's aggregated results + Module 3's categorized
adverse-media findings), scores each one on entity-resolution and historical signals and produces
a confidence score, a triage recommendation, and an explainable rationale — so a reviewer can
prioritize attention instead of manually re-verifying every hit.

## Hard requirement: this module recommends, it does not decide

Every `TriageResult` carries a constant `label` field ("AI-suggested — pending human confirmation,
not a resolved status") specifically so no caller can present one as resolved by accident. This
module never auto-dismisses or auto-clears a finding — `likely_false_positive` findings stay in
the ranked list, never hidden. Every triage run and every reviewer override is persisted for
audit (see "Persistence" below).

## Stack

Matches Module 2 and Module 3: Python + FastAPI + Pydantic v2, `pytest`/`pytest-asyncio`, own venv
and `requirements.txt`, fully isolated from Modules 1–3. Unlike stateless Module 3, Module 4 needs
SQLAlchemy + its own SQLite database — see "Persistence" below.

## Architecture

```
module4/
├── app/
│   ├── core/                  # config.py, time.py (SQLite tzinfo fix), auth.py (actor stub)
│   ├── schemas/
│   │   ├── entity.py          # EntityProfile — Module 4's own copy of the Module 1->2 contract
│   │   ├── upstream.py        # what's read from Module 2 (ScreeningResult/Hit) and Module 3
│   │   │                      # (AdverseMediaFinding), adapted at the boundary
│   │   └── triage.py          # MatchQuality, HistoricalOutcomeSignal, TriageResult — the
│   │                          # stable Module 5-facing output contract
│   ├── db/                    # base.py, session.py (SQLAlchemy, own triage.db)
│   ├── models/triage.py       # TriageResultRecord, TriageOverrideRecord (soft-archived history)
│   ├── services/
│   │   ├── entity_lookup.py         # reads module1's vista.db (or fixtures) -> EntityProfile
│   │   ├── module2_source.py        # reads module2's screening.db (or fixtures), all 5 sources
│   │   ├── module3_source.py        # calls Module3's live API (or fixtures) for adverse-media
│   │   ├── text_utils.py            # name normalization + anchored character similarity
│   │   ├── entity_resolution.py     # deterministic: name similarity, nationality/ID text-match,
│   │   │                            # ownership/relationship overlap — NOT LLM-driven
│   │   ├── historical_outcome.py    # derives the signal from Module 2's prior_kyv source
│   │   ├── reasoning_service.py     # AI scorer (ABC) + Anthropic impl + deterministic fallback
│   │   ├── triage_engine.py         # orchestrates + ranks
│   │   └── audit_service.py         # persists every run + every override
│   ├── api/routes/
│   │   ├── triage.py           # GET /api/entities/{id}/triage
│   │   └── overrides.py        # POST .../triage/{triage_id}/override, GET .../triage/overrides
│   └── main.py
├── fixtures/                  # standalone entities + screening results + adverse-media findings
└── tests/
```

## Inputs and how they're read

**Module 2** (`module2_source.py`): reads `module2/backend/database/screening.db` directly as a
plain SQLite file — never Module 2's Python code, which runs in its own venv/process — the same
read-only, adapt-at-the-boundary pattern Module 3 uses for the same database. All five sources are
read; `prior_kyv` feeds the historical-outcome signal (see below) rather than becoming a triaged
finding itself, and `adverse_news` is skipped here in favor of Module 3's refined output (see
next), so the same underlying articles aren't triaged twice.

**Module 3** (`module3_source.py`): Module 3 has **no database of its own** — it's fully stateless,
computing adverse-media findings fresh on every API call (see `module3/README.md`). So "live" here
means an HTTP call to Module 3's running server (default `http://localhost:8001`), not a file
read — the one boundary in Module 4 that needs another module's server actually running. If
unreachable, falls back to `fixtures/sample_adverse_media_findings.json` for that entity rather
than failing the whole triage run.

**Module 1** (via `entity_lookup.py`): resolves the queried entity's profile (name, aliases,
nationality, ID numbers, related entities) the same way Module 2 does — reading
`module1/database/vista.db` directly. Also resolves each related entity's `legal_name` (one hop),
feeding the ownership/relationship overlap signal.

Both DB reads and the Module 3 HTTP call fall back to `fixtures/` automatically when unavailable,
so Module 4 runs and tests fully standalone (`python -m pytest` needs no other module running).

## Scoring approach

**Entity resolution (`entity_resolution.py`) is deterministic, not LLM-driven** — per the spec,
the LLM reasons *over* these results, it does not recompute them:

- **Name similarity**: blends token coverage (do the name's words appear in the hit text?) with
  character-level similarity of the best-matching window (`text_utils.best_substring_char_similarity`)
  — the character-level half specifically catches transliteration/spelling variants ("Tan Wei Ming"
  vs. "Tan Wei Meng") that token overlap alone would score at zero. That function anchors on a
  real word-level match before trusting a character-similarity score, precisely because a naive
  sliding window can score short names as spuriously similar to unrelated text — a bug caught
  during development (see git history) where "Tan Wei Ming" scored 0.55 against text that never
  mentioned it, purely from coincidental letter overlap with common short words like "an".
- **Nationality / ID match**: text-mention proxies, not structured field comparisons (see
  "Adaptations" below) — does the hit's text/raw metadata mention the entity's known nationality
  or ID number?
- **Ownership/relationship overlap**: does the hit's text mention one of the entity's known related
  parties (director, shareholder, UBO) by name? A single strong mention counts as real
  corroboration even when the entity's own name similarity is weak — this is what makes a partial
  ownership chain (an article about "a company linked to director X" with no direct company-name
  mention) still surface for review instead of being missed.

**Historical outcome (`historical_outcome.py`)**: Module 2's `prior_kyv` source, surfaced
alongside fresh signals, never silently applied — see "Adaptations" below for how its two mock
outcome values map onto the spec's three-value `prior_outcome`.

**Confidence scoring (`reasoning_service.py`)**: the deterministic fallback is an explicit weighted
formula (name similarity up to 45 points, nationality +10, ID match +20, ownership overlap up to
15, adverse-media/hit severity up to +10, historical true-hit +20 / false-positive −30, clamped to
0–100), chosen so that **name similarity alone — even a perfect match — cannot reach
`high_priority_review`** without at least one other corroborating signal; that's deliberately the
"common name" case the spec calls out as needing a human, not an auto-resolution. `>=60` →
`high_priority_review`, `>=35` → `needs_review`, else `likely_false_positive`. The real
(Anthropic) path receives the same sub-scores as given facts and is instructed not to recompute
them, only to reason over and explain them — with the same disposition guidance baked into its
system prompt.

## Persistence

Every `GET .../triage` call runs the full pipeline fresh (no caching — Module 2 already caches the
underlying hits) **and persists the batch**: "every triage recommendation must be logged for audit
purposes" is read literally, so each generation event is itself an audit entry, not just a cache.
The entity's previous batch is soft-archived (`is_archived`), never deleted. Reviewer overrides
(`POST .../triage/{triage_id}/override`) are a separate, append-only table, and work even against
an already-archived (superseded) recommendation — a reviewer must always be able to explain what
they overrode, which is exactly the override-history input Module 7 will want later.

## Running it

```powershell
cd module4
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002
```

Try `GET /api/entities/{entity_id}/triage` against a real entity from your Module 1/2/3 setup, or
the bundled fixtures `vendor:fixture-1` / `director:fixture-1` (deliberately tricky cases — see
tests) / `vendor:fixture-clean` / `vendor:fixture-conditions`, which work even with Modules 1–3
never having been run. For a live Module 3 pull, also run Module 3's server (`module3/`, default
port 8001) — otherwise Module 4 falls back to Module 3's fixtures automatically.

Run the tests:

```powershell
cd module4
python -m pytest
```

**To point the reasoning service at the real Anthropic API**: set `ANTHROPIC_API_KEY` (copy
`.env.example` to `.env`). Without it, every score comes from the deterministic fallback.

## Assumptions

- **Module 2 schema gaps**: `ScreeningHit` has no separate subject-nationality/subject-ID field
  distinct from the queried entity, so nationality/ID matching scans hit text/metadata for the
  *entity's own* known values rather than comparing structured fields. `EntityProfile.related_entities`
  carries no ownership percentage, so ownership overlap is a text-mention signal (is a related
  party named in this hit?), not a percentage-weighted calculation.
- **Historical outcome mapping**: the spec's illustrative schema wants `prior_outcome:
  false_positive | true_hit | unknown`, but Module 2's actual `prior_kyv` mock only ever emits
  `approved_with_conditions` or `escalated` (module2/backend/app/connectors/prior_kyv.py) — never
  an explicit "cleared" disposition. Both map to `true_hit` here (both reflect a reviewer engaging
  with a real concern, not dismissing one), `unknown` covers "no prior review found." The mapping
  structurally supports `false_positive` for a real prior-review system that does record clearances.
- **Naming**: the spec's prompt calls this source `previous_kyv_reviews`; Module 2's actual
  `SourceName` enum value is `prior_kyv` — used as-is rather than introducing a third name for the
  same thing.
- **No re-triage of Module 2's adverse_news hits**: Module 3 already dedups/filters/categorizes
  that exact data, so Module 4 triages Module 3's refined findings instead of also triaging Module
  2's raw adverse_news hits, to avoid double-counting the same articles.
- **Entity-level historical signal**: Module 2's `prior_kyv` mock records a whole-entity review
  outcome, not a per-finding disposition history, so the same historical signal is attached to
  every finding for a given entity rather than derived per finding.
