# VISTA Module 3 — Adverse Media Screening Engine

Takes the adverse-news slice of Module 2's aggregated screening output and does the actual risk
analysis on it: matching against an approved keyword library, applying a risk taxonomy, and
producing categorized, explainable findings — so reviewers see *why* something matters, not just
that an article was found.

## Stack

Matches Module 2: Python + FastAPI + Pydantic v2, `pytest`/`pytest-asyncio`, its own venv and
`requirements.txt`, fully isolated from Module 1 and Module 2's environments. Module 3 has no
database of its own — it's a stateless analysis pass over Module 2's already-cached data (Module
2 owns caching/audit for the underlying screening hits), so there's no SQLAlchemy/storage layer
here, unlike Module 2.

## Architecture

```
module3/
├── config/
│   └── taxonomy.yaml        # editable keyword library + risk taxonomy (compliance-owned)
├── app/
│   ├── core/config.py        # Settings: module1/module2 DB paths, taxonomy path, API key
│   ├── schemas/
│   │   ├── taxonomy.py       # RiskTheme, KeywordEntry, TaxonomyConfig — the config contract
│   │   ├── adverse_news.py   # AdverseNewsHitIn/Bundle — the Module 2 input contract
│   │   └── finding.py        # AdverseMediaFinding — the stable Module 4-facing output contract
│   ├── taxonomy/loader.py    # loads + validates config/taxonomy.yaml
│   ├── services/
│   │   ├── adverse_news_source.py  # reads Module 2's screening.db (+ Module 1's vista.db for
│   │   │                           # entity names), read-only; falls back to fixtures/
│   │   ├── text_utils.py            # shared name/text normalization helpers
│   │   ├── dedup_service.py         # collapses near-duplicate articles about the same event
│   │   ├── relevance_filter.py      # near-miss name filtering + keyword/negation matching
│   │   ├── categorization_service.py# AI categorizer (ABC) + Anthropic impl + deterministic fallback
│   │   └── screening_engine.py      # orchestrates: fetch -> dedup -> filter -> categorize
│   ├── api/routes/findings.py       # thin FastAPI router (optional API surface, mirrors module2)
│   └── main.py
├── fixtures/
│   └── sample_adverse_news.json     # standalone bundles for isolated testing
└── tests/
```

**Input contract.** Module 2's real `ScreeningHit` shape (`module2/backend/app/schemas/screening.py`)
is `title`/`description`/`hit_date`/`raw`, not the illustrative `headline`/`publication`/`url`/
`excerpt` shape in this module's prompt. `app/schemas/adverse_news.py` maps onto what Module 2
actually produces (`headline` <- `title`, `excerpt` <- `description`, `publish_date` <- `hit_date`,
`publication`/`url` read opportunistically from `raw` — Module 2's mock adverse-news connector
doesn't currently populate a `url`, so it's commonly `None`).

**Reading Module 2 (and Module 1).** `AdverseNewsSource` reads `module2/backend/database/
screening.db` directly as a plain SQLite file — never Module 2's Python code, which runs in its
own venv/process — the same read-only, adapt-at-the-boundary pattern Module 2 uses for Module 1.
Resolving an `entity_id` to a `legal_name` (needed for the relevance filter) goes one hop further
back to Module 1's `vista.db`, for the same reason: no cross-venv Python import, no server
dependency. If either database is missing or the entity isn't found live, falls back to
`fixtures/sample_adverse_news.json` automatically — Module 3 runs and tests fully standalone.

**Pipeline** (`ScreeningEngine.screen_entity`):
1. **Dedup** (`dedup_service.py`) — collapses republished/reworded articles about the same event.
   Similarity is content-token overlap with the entity's own name and stopwords excluded — without
   that exclusion, two *different* stories about the same company score artificially similar just
   from sharing the company name.
2. **Relevance filter** (`relevance_filter.is_relevant_to_entity`) — drops hits that are a
   near-miss name collision (a different, similarly-named company), before spending an LLM call
   on them.
3. **Keyword matching** (`relevance_filter.find_keyword_matches`) — candidate taxonomy matches per
   hit, each flagged `negated` when a configured `negation_guard` phrase is also present (victim
   framing, exoneration, plaintiff-not-defendant). This is a blunt, testable heuristic for the
   deterministic fallback — real contextual judgment is the AI categorizer's job.
4. **AI categorization** (`categorization_service.py`) — an `AICategorizer` ABC, mirroring Module
   2's `SummaryGenerator` pattern: an Anthropic (`claude-sonnet-5`) implementation that falls back
   to a deterministic categorizer (built directly from the non-negated keyword matches) whenever
   no `ANTHROPIC_API_KEY` is configured or any call/parse fails. Every finding carries a
   `source_hit` reference (result_id + hit_id + headline/excerpt/url) — never a blended or
   unattributed claim.

## Taxonomy config format

`config/taxonomy.yaml` is owned by compliance/risk staff, not engineering — no code changes are
needed to add a keyword or retheme one. Structure:

```yaml
version: "1.0"
themes:                       # all seven themes below are required
  financial_crime: "..."
  sanctions: "..."
  fraud: "..."
  regulatory_breach: "..."
  tax_offence: "..."
  esg: "..."
  operational: "..."
keywords:
  - phrase: "money laundering"
    themes: [financial_crime]           # a keyword may map to more than one theme
    negation_guard: ["victim of", "cleared of"]   # optional
    notes: "optional reviewer-facing note"
```

To add a keyword: append an entry under `keywords`. To retheme one: edit its `themes` list. The
file is validated on load (`app/taxonomy/loader.py`) — an unknown theme name, a blank phrase, or a
missing theme description raises a clear `TaxonomyLoadError` rather than failing silently.

Note: theme names here (e.g. `tax_offence`) are Module 3's own taxonomy, not a reuse of Module 2's
`RiskCategory` Python enum, which uses `tax`. They describe the same domain but are independently
config-driven per the spec — keeping them decoupled avoids a Python-level dependency between
modules that run in separate venvs.

## Running it

```powershell
cd module3
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

`GET /api/entities/{entity_id}/adverse-media-findings` runs the full pipeline fresh (no caching —
Module 2 already caches the underlying hits) and returns an `AdverseMediaScreeningResponse`. Try
it against a real entity from your Module 1/2 setup (e.g. `vendor:1`), or against the bundled
fixture entities `vendor:demo-highrisk` / `vendor:demo-clean`, which work even with Module 1/2
never having been run.

Run the tests:

```powershell
cd module3
python -m pytest
```

**To point the categorizer at the real Anthropic API**: set `ANTHROPIC_API_KEY` (copy
`.env.example` to `.env`). Without it, every finding comes from the deterministic fallback.

## Assumptions

- **"Live" pull mechanism**: reads Module 2's SQLite file directly rather than calling its HTTP
  API, so Module 3 needs no other server running — matches the spec's "test in isolation without
  spinning up Module 2."
- **No persistence/caching in Module 3**: findings are computed fresh per request. Module 2 already
  owns caching and audit logging for the underlying screening data; re-adding either here seemed
  like unnecessary duplication for a stateless analysis pass. Revisit if Module 4 needs findings
  to be queryable without recomputation.
- **Negation heuristic is text-wide, not sentence-scoped**: `negation_guard` checks whether the
  phrase appears anywhere in the hit's headline+excerpt, not specifically near the matched
  keyword. Good enough for the deterministic fallback; the real LLM path does proper contextual
  reading.
- **Dedup/relevance thresholds** (`dedup_similarity_threshold: 0.3`, `relevance_token_overlap_
  threshold: 0.5` in `app/core/config.py`) were tuned empirically against the bundled fixtures, not
  derived analytically — adjust if real adverse-news phrasing behaves differently.
