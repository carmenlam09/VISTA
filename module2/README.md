# VISTA Module 2 — Screening Intelligence Hub

Given a vendor entity (vendor, director, shareholder, or UBO), aggregates screening data from
five sources into one unified view and generates an AI summary that highlights what a reviewer
actually needs to know — so reviewers spend their time on judgment, not manual reconciliation.

## Stack

- **Backend**: Python + FastAPI, chosen for async-native concurrent connector calls (the core
  requirement — query 5 sources in parallel), Pydantic for schema validation shared cleanly
  between the API and the internal service layer, and consistency with Module 1's Python stack.
- **Frontend**: React + TypeScript + Vite. Plain Vite over Next.js since this is a single
  internal SPA behind an API gateway with no need for SSR/routing-on-the-server.
- **Storage**: SQLAlchemy against SQLite by default (zero setup, matches Module 1's approach).
  Point `DATABASE_URL` at a Postgres DSN (e.g.
  `postgresql+psycopg://user:pass@host:5432/vista_screening`) for production — no code changes
  needed, only the connection string and adding `psycopg` to requirements.

## Architecture

```
module2/
├── backend/
│   └── app/
│       ├── connectors/     # ScreeningConnector interface + one mock per source + registry
│       ├── schemas/        # Pydantic contracts: EntityProfile, ScreeningResult, ScreeningSummary
│       ├── models/         # SQLAlchemy tables (screening_results, audit_log)
│       ├── services/       # entity_service, aggregation_service, cache_service,
│       │                   # audit_service, summary_generator — all UI-independent
│       ├── api/routes/     # thin FastAPI routers calling the services above
│       ├── fixtures/       # bundled sample entities, used when Module 1's DB isn't present
│       └── core/           # config, auth-stub, time helpers
└── frontend/
    └── src/
        ├── api/            # typed fetch client
        ├── components/     # StatusBadge, SummaryPanel, FindingCard, SourceSection
        └── pages/          # EntityListPage, EntityDetailPage
```

**Entity input.** Module 1's actual SQLite schema (`module1/database/schema.sql`) models a
vendor with nested directors/shareholders/UBOs, not the unified `entity_id`/`entity_type` shape
described in the Module 2 spec. `EntityService`
([entity_service.py](backend/app/services/entity_service.py)) reads
`module1/database/vista.db` **read-only** (a plain SQLite file — never Module 1's Python code,
which would drag in Streamlit/OCR dependencies just to read data) and adapts each row into
`EntityProfile` at the boundary, synthesizing ids like `director:<director_id>`. If that
database doesn't exist yet, it falls back to `app/fixtures/sample_entities.json` automatically,
so Module 2 runs and tests standalone.

**Aggregation.** `AggregationService.aggregate()` queries the requested sources concurrently via
`asyncio.gather`, checks a per-source TTL cache first, and never lets one connector's failure
take down the others — each failure becomes a `ScreeningResult` with `status: error|timeout`
instead of an exception. Old cached rows are soft-archived (`is_archived=True`), never deleted,
so a future Module 7 can read historical runs.

**AI summary.** `SummaryGenerator` is a separate interface from aggregation, per the spec. With
no `ANTHROPIC_API_KEY` configured (or on any call/parse failure), it falls back to a
deterministic, rule-based summarizer built directly from the hits — the same
real-API-with-local-fallback pattern Module 1 uses for Gemini. Every finding the LLM path
returns is checked against the actual queried sources before being accepted, so a finding can
never cite a source that wasn't part of the aggregation.

**Auth stub.** `core/auth.py` reads `X-User-Id`/`X-User-Role` headers to produce an `Actor`,
mirroring the boundary a real SSO/JWT integration would sit behind. Swapping in real auth means
replacing `get_current_actor` only.

**Audit trail.** Every query, refresh, and view is logged to `audit_log` (actor, entity, sources,
timestamp). `GET /api/entities/{id}/audit` is admin-only, demonstrating the reviewer/admin RBAC
split.

## Running it

Backend:

```powershell
cd module2/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend (separate terminal):

```powershell
cd module2/frontend
npm install
npm run dev
```

Open the URL Vite prints (typically `http://localhost:5173`). The dev server proxies `/api/*` to
the backend on `http://localhost:8000`.

Run the backend tests:

```powershell
cd module2/backend
python -m pytest
```

## Mock connectors

Real CTOS/NetReveal/etc. credentials aren't available in this environment, so each source has a
mock implementation in `app/connectors/`. Output is deterministic per `(entity_id, source)` — the
same entity always produces the same result — but varies across entities via a stable
`risk_profile()` hash (`clean` / `false_positive` / `moderate` / `high_risk`), so a given demo
entity tells a coherent story across all five sources. NetReveal and a few others also
deterministically raise `ConnectorTimeoutError` for specific entities, exercising the
partial-failure path realistically. `app/fixtures/sample_entities.json` includes:

- `vendor:4` — genuinely high-risk (hits across all 5 sources, used as the "risky" test fixture)
- `vendor:9` — clean (zero hits anywhere, used as the "clean" test fixture)
- `vendor:1` — a source (NetReveal) deterministically fails, for partial-failure testing

**To point a connector at the real API**: replace the body of that connector's `fetch()` method
with an authenticated HTTP call, mapping the response onto the existing `ScreeningResult`/
`ScreeningHit` schema. No other file changes — `AggregationService`, the cache, the audit log,
and the frontend only depend on the `ScreeningConnector` interface and the normalized schema.

## Assumptions

- **Postgres vs. SQLite**: shipped against SQLite for zero-setup local development; swapping to
  Postgres is a `DATABASE_URL` change (see Stack above).
- **Encryption at rest**: not implemented against local SQLite (no practical way to demo it in
  this environment). A real deployment on Postgres should enable disk-level/TDE encryption at
  the database layer; this is a documented gap, not a design decision.
- **RBAC scope**: reviewer and admin both can query/view; only the raw audit log endpoint is
  admin-gated. Extend `require_admin` calls in `api/routes/` if more actions need restricting.
- **AI provider**: Anthropic Claude (`claude-sonnet-5`) was chosen for the summary generator;
  swap the model string in `summary_generator.py` or add another `SummaryGenerator`
  implementation to change providers.
