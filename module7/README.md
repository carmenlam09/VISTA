# VISTA Module 7 — Vendor Risk Knowledge Repository

> ## ⚠️ RETENTION POLICY IS A PLACEHOLDER — NOT CONFIRMED WITH COMPLIANCE
>
> `config/retention_policy.yaml`'s `retain_days` values are sensible-looking placeholders, not
> figures confirmed with the bank's actual compliance/legal function. `is_placeholder: true` in
> that file, and every retrieval response's `disclaimer` field, exist specifically so this can't be
> missed downstream. **Before this module is used for anything real**, get the actual retention
> periods from compliance and update the YAML (see "Retention & archival" below).

> ## 🔌 OUTSTANDING INTEGRATION WORK — Modules 2 and 4 are not wired to this module yet
>
> This task builds Module 7's capability; it does not change Module 1-6 code. Two integration
> points remain for a future pass:
> - **Module 2's `prior_kyv` connector** (`module2/backend/app/connectors/prior_kyv.py`) is
>   currently a mock. It's meant to eventually call `POST /api/knowledge-records/search`
>   (filtered by `entity_id`, `record_type=kyv_review`) instead of returning canned data.
> - **Module 4's historical-outcome lookup** (`module4/app/services/historical_outcome.py`)
>   currently reads Module 2's `prior_kyv` source directly. It's meant to eventually also query
>   Module 7 for `false_positive_decision` records on the same entity — a confirmed false positive
>   or true hit is exactly the "high-value historical signal" capability 2 of this module's own
>   spec calls out.
>
> Module 7's retrieval API (`RetrievalQuery`/`RetrievalResponse`, see below) was designed with
> this swap in mind — both integrations are a matter of replacing a mock/local read with an HTTP
> call to this module's `/search` endpoint, not a schema change.

Captures completed KYV reviews, adverse-media assessments, false-positive decisions, EDD outcomes,
and approval records from across the platform as the bank's growing institutional memory, and
provides AI-assisted retrieval so a reviewer working a new case can surface relevant past
assessments instead of starting from zero.

## Hard requirements

- **Never hard-deleted.** There is no delete path anywhere in this module. A corrected record
  supersedes the prior version (`status: superseded`), which stays in the table forever,
  retrievable via `include_superseded` or the lineage endpoint.
- **Retrieval surfaces context, it does not decide.** Every `RetrievalResponse` carries a constant
  `disclaimer` field; nothing in this module resolves a finding on its own.
- **Access control extends Module 2's original RBAC** (`reviewer | admin`), not Module 5/6's later
  3-role Maker-Checker extension — see "Access control" below.

## Stack

Matches Modules 2-6: Python + FastAPI + Pydantic v2, `pytest`/`pytest-asyncio`, own venv and
`requirements.txt`, fully isolated from Modules 1-6. SQLAlchemy + own SQLite database, same as
every prior module.

## Storage & retrieval approach

**Structured storage**: SQLite, matching every prior module's choice — no case for introducing
Postgres or a separate database service in this environment.

**Semantic retrieval**: rather than a real embeddings API, this module uses a **local, deterministic
embedding** — token/bigram term-frequency vectors hashed into a fixed-size (256-dim, configurable)
array and L2-normalized, ranked by cosine similarity (`app/services/embedding.py`). Reasoning:
Anthropic (the one AI provider every prior module uses) has no embeddings endpoint, and introducing
a second provider (e.g. OpenAI) just for this module's semantic search would be a bigger
architectural decision than this task calls for. Feature hashing (the "hashing trick") is a real,
established lightweight technique — not a toy — and needs no external API, key, or model download,
so semantic search works fully offline and is exactly reproducible in tests. It's built behind an
`EmbeddingProvider` ABC specifically so a real embedding API can be substituted later without
touching `retrieval_service.py`. The vector itself is stored as a JSON column on the same SQLite
row — no separate vector index — which is fast enough at the record volumes a fixture-driven system
like this will see; a real production deployment at bank scale would want a proper vector index
(e.g. pgvector) once record counts are large enough for linear cosine-similarity scan to matter.

## Access control

Reuses Module 2's exact `Role` enum (`reviewer | admin`) rather than Module 5/6's later 3-role
extension — there's no approve/reject workflow here that would call for an `approver` role.
**Retrieval** (`POST /search`, `GET /{record_id}`, `GET /lineage/{lineage_id}`) requires
`reviewer` or `admin` — historical records span every vendor the bank has ever reviewed, one of
the most sensitive stores in the platform. **Ingestion** (`POST /api/knowledge-records`) is
`admin`-only: it's meant to be called by other modules' backends (or a future integration pass),
not a human reviewer's day-to-day action, so it's gated more tightly than read access.

## Architecture

```
module7/
├── config/
│   └── retention_policy.yaml   # PLACEHOLDER retention rules — see warning above
├── app/
│   ├── core/                   # config.py, time.py, auth.py (Role: reviewer|admin)
│   ├── schemas/
│   │   ├── record.py           # KnowledgeRecord — the unified schema (capability 1)
│   │   ├── ingestion.py        # IngestionRequest/Result — the ingestion API contract
│   │   ├── retrieval.py        # RetrievalQuery/Response — structured + freeform query interface
│   │   └── retention.py        # RetentionPolicyConfig — the retention config contract
│   ├── db/                     # base.py, session.py (own knowledge_repository.db)
│   ├── models/record.py        # KnowledgeRecordORM — no delete path exists anywhere on it
│   ├── policy/loader.py        # loads + validates config/retention_policy.yaml
│   ├── services/
│   │   ├── embedding.py            # EmbeddingProvider (ABC) + local hashed-TF default
│   │   ├── ingestion_service.py    # idempotent capture + supersede-on-change versioning
│   │   ├── retrieval_service.py    # structured filtering + cosine-similarity ranking,
│   │   │                           # retention-aware default exclusion
│   │   └── fixture_loader.py       # seeds a fixture history for standalone dev/testing
│   ├── api/routes/
│   │   ├── ingestion.py         # POST (admin), GET /{id}, GET /lineage/{lineage_id}
│   │   └── retrieval.py         # POST /search (reviewer+)
│   └── main.py
├── fixtures/
│   └── sample_records.json      # a small history across all 5 record types, incl. a
│                                 # name-collision false-positive case for relevance tests
└── tests/
```

## The KnowledgeRecord schema

```jsonc
{
  "record_id": "uuid",
  "lineage_id": "uuid",          // groups every version of "the same" record across supersessions
  "entity_id": "vendor:1",
  "record_type": "kyv_review | adverse_news_assessment | false_positive_decision | edd_outcome | approval_record",
  "timestamp": "when the underlying event/decision happened",
  "source_module": "module3 | module4 | module5 | module6 | ...",
  "source_reference": "stable id from the source module (finding_id/draft_id/report_id/...)",
  "status": "active | superseded",
  "summary_text": "narrative/rationale text — embedded for retrieval, shown to reviewers",
  "tags": ["risk themes, dispositions, outcomes — structured, filterable"],
  "payload": { "...": "the actual assessment/finding data, opaque to this module" },
  "supersedes": "record_id this replaced, or null",
  "content_hash": "sha256 over (source_module, source_reference, payload) — the idempotency key",
  "created_at": "when Module 7 ingested this version"
}
```

## Ingestion (capability 2)

`POST /api/knowledge-records` with an `IngestionRequest` (everything above except the
server-computed fields). Idempotency key is `(source_module, source_reference)`:

- Same payload resubmitted → no-op, existing record returned (`was_duplicate: true`).
- Different payload under the same `source_reference` → prior version marked `superseded` (never
  deleted), new version inserted under the same `lineage_id`.

## Retrieval (capabilities 3/4)

`POST /api/knowledge-records/search` with a `RetrievalQuery` — any combination of structured
filters (`entity_id`, `record_type`, `tags`, `date_from`/`date_to`) and a freeform `query_text`.
With no `query_text`, every row surviving the structured filters is scored `1.0` (an exact filter
match by definition). With a `query_text`, semantic similarity is the primary ranking signal, with
small bonuses for also matching `entity_id`/`tags` as tie-breakers; results below a minimum
similarity floor (and with no structured match) are excluded outright rather than padded in at the
bottom. `include_archived`/`include_superseded` opt into records normal search hides.

There is no dedicated reviewer-facing search UI — consistent with Modules 3-5 (only Module 2 has a
frontend), the interactive `/docs` (Swagger UI) page serves as the search interface for now.

## Retention & archival (capability 5)

`config/retention_policy.yaml` maps each `record_type` to `retain_days`. Archival is **computed at
query time** (`age_days > retain_days`), not a stored, mutable flag set by a background job — there
is no scheduler/cron in this environment, and computing it on read is simpler, always-correct, and
needs no maintenance process. A record past its retention window is excluded from default search
results (`is_archived: true` on results that are explicitly requested via `include_archived: true`)
but is never deleted and never stops being retrievable by id or lineage.

## Running it

```powershell
cd module7
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8006
```

Seed the bundled fixture history for a quick standalone try:

```powershell
python -c "from sqlalchemy.orm import Session; from app.db.session import engine, init_db; from app.services.fixture_loader import seed_fixture_history; init_db(); seed_fixture_history(Session(engine))"
```

Then try `POST /api/knowledge-records/search` with `{"query_text": "name collision false positive
sanctions"}` (header `X-User-Role: reviewer`) — this is the fixture designed to demonstrate exactly
the retrieval scenario the spec's own example describes.

Run the tests:

```powershell
cd module7
python -m pytest
```

## Assumptions

- **RBAC split**: retrieval requires `reviewer|admin`; ingestion requires `admin` only, treating it
  as a system/service-level write rather than a normal reviewer action. The spec doesn't specify
  this split explicitly; it follows from "one of the most sensitive stores in the platform" plus
  ingestion being framed throughout as something *other modules* call, not a human UI action.
  Extend `require_admin`/`require_authorized` in `app/core/auth.py` if a finer split is needed later.
- **Archival is computed at query time**, not a stored/cron-maintained flag — see "Retention &
  archival" above.
- **Tags are caller-supplied, not derived by Module 7** — whichever module eventually calls
  ingestion is responsible for deriving appropriate tags (risk themes, disposition, etc.) from its
  own record shape; Module 7 stores and filters on them but doesn't try to infer them from `payload`.
- **Vector storage is a JSON column on the record row**, not a separate index — see "Storage &
  retrieval approach" above for the reasoning and the scaling caveat.
