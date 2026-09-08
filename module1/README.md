# VISTA Module 1 — Digital Intake & Entity Extraction Engine

Uploads vendor due-diligence source documents, extracts entities (vendor, directors, shareholders,
UBOs, related parties), and persists a consolidated, deduplicated profile — the entity data every
other VISTA module ultimately reads from, directly or transitively.

## Stack

FastAPI + Pydantic v2 + SQLAlchemy backend, matching Modules 2–7 exactly (own venv, `app/core/
config.py`, RBAC, audit logging, `pytest`). The interactive upload/validate/browse UI stays
Streamlit — the right tool for that job — but is now a **thin HTTP client** against this module's
own FastAPI backend rather than importing services in-process, so Module 1 is composable into the
eventual single combined application the same way Modules 3–7 already are (see "Alignment
refactor" below for why).

## Architecture

```
module1/
├── app/                        # FastAPI backend
│   ├── core/                   # config.py, time.py, auth.py (Role: reviewer|admin,
│   │                           # Module 2's original pattern)
│   ├── schemas/vendor.py       # VendorProfile (draft) / VendorRecord (persisted+read) — the
│   │                           # external output contract, see below
│   ├── db/                     # base.py, session.py (SQLAlchemy, the same vista.db file)
│   ├── models/
│   │   ├── vendor.py           # Vendor, Director, Shareholder, Ubo, RelatedParty
│   │   └── audit.py            # AuditLogRecord (NEW)
│   ├── services/
│   │   ├── pdf_service.py / docx_service.py / ocr_service.py   # unchanged text extraction
│   │   ├── entity_extractor.py       # Gemini + deterministic local fallback
│   │   ├── vendor_profile_builder.py # merge + dedupe multiple extractions
│   │   ├── vendor_service.py         # persistence (replaces the old database_service.py)
│   │   └── audit_service.py          # NEW — logs every extraction run and save
│   ├── api/routes/vendors.py   # POST /extract, POST /vendors, GET /vendors, GET /vendors/{id}
│   └── main.py
├── ui/                          # Streamlit thin client
│   ├── streamlit_app.py         # landing page (was app.py)
│   ├── api_client.py            # httpx calls into the FastAPI backend above
│   └── pages/{upload,validation,vendor_repository}.py
├── database/                    # schema + the actual vista.db (unchanged location/file)
├── fixtures/                    # sample_vendor.txt, contract_baseline.json (see below)
└── tests/
```

## Running it

Two processes, matching Module 2's backend+frontend pattern:

```powershell
# Terminal 1 — API
cd module1
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2 — UI
cd module1
.\.venv\Scripts\Activate.ps1
streamlit run ui/streamlit_app.py
```

For Gemini extraction, set `GEMINI_API_KEY` before launching the API (copy `.env.example` to
`.env`). Without it, extraction uses the included deterministic local extractor — an SSM-report-
aware parser plus a generic labeled-text fallback.

Run the tests:

```powershell
cd module1
python -m pytest
```

## The output contract

`VendorRecord` (`app/schemas/vendor.py`) is what Module 2 reads directly from `database/vista.db`,
and what Modules 3–7 depend on transitively. Field names, table names, and column names are
unchanged from before this refactor — see "Alignment refactor" below for the one additive field
and the exact fixes made, both verified against a captured pre-refactor baseline.

## Alignment refactor (this pass)

Module 1 was built before Modules 2–7 existed and had never been brought into line with the
conventions they established. This refactor did that — full audit and plan in
`docs/VISTA_Module1_Realignment_ClaudeCode_Prompt.md` and the Phase A report in this
conversation's history — without changing the persisted output contract except as documented here.

**What changed internally** (no contract impact): folder layout, venv/dependency isolation,
Pydantic schemas replacing untyped dicts/dataclasses, SQLAlchemy replacing raw `sqlite3`, a
`pytest` suite (Module 1 had none before), README format, and the FastAPI+thin-Streamlit-client
split described above. The dead `repositories/` package and four unused `models/*.py` dataclass
files (only `VendorProfile` was ever actually imported anywhere) were removed rather than carried
forward.

**New capabilities added** (per the realignment spec's explicit instruction to bring Module 1 up
to Module 2's cross-cutting standards):
- **Audit logging** — every extraction run and every save is now logged (`app/services/
  audit_service.py`), matching Module 2's pattern. Module 1 previously had none.
- **Access control** — reuses Module 2's exact `reviewer | admin` RBAC stub (`app/core/auth.py`).
  Module 1 previously had none; every endpoint now requires a recognized actor.

**Output contract: one additive field, two verified bug fixes, both confirmed by a permanent
regression test** (`tests/test_contract_baseline.py`, comparing against `fixtures/
contract_baseline.json` — the exact output the pre-refactor code produced against the same
fixtures, captured before any refactor code was touched):

1. **`id_number` added to Director/Shareholder/UBO** (Phase A gap #2). Module 1 previously had no
   column at all for an individual's NRIC/passport — only vendors had `registration_number` —
   which meant Module 4's `id_match` entity-resolution signal could never be true for any
   individual. Purely additive: nullable columns, existing consumers reading named columns are
   unaffected. Currently only populated by the SSM-report extraction path (verified against the
   real sample PDF's "IC/Paspot" field); the generic labeled-text extractor doesn't populate it
   yet. **Wiring Module 2 to read and forward this field remains outstanding** (out of scope here
   — Module 2's code isn't touched by this task).
2. **Shareholder-name parsing bug fix.** Found while capturing the baseline: when a shareholder's
   corporate suffix wraps across two PDF lines ("...SDN." / "BHD."), the old parser fell back to
   matching an unrelated repeated page-header line ("Nama : COMPANY SDN. BHD.") as the shareholder
   name. Fixed to reconstruct the wrapped name from the genuine continuation line, or drop the row
   (never fabricate) if the next line doesn't look like one.
3. **A transient `shares` field is no longer carried into the draft profile shown to a reviewer
   before saving.** It was never part of the persisted contract either way — the original
   `save_vendor` never wrote it to the database — so this only drops it one step earlier, from the
   intermediate JSON. Not contract-impacting; noted for completeness.

**Outstanding / not done in this pass** (flagged, not silently skipped):
- Related-party names are captured and persisted by Module 1 (unchanged) but still never surface
  downstream — Module 2's reader only pulls `relationship_type`, not `related_party_name`. A
  Module 2 change, out of scope here.
- The generic (non-SSM) local extractor doesn't yet populate `id_number` — only the SSM path does.
- No unified frontend/gateway across all 7 modules exists yet. Module 1's Streamlit UI now talks
  to its own FastAPI backend rather than another module's — building the single combined
  application (one frontend across Modules 1–7) is future work, not this task.

## Assumptions

- RBAC follows Module 2's original `reviewer | admin` model exactly, per the realignment spec's
  explicit instruction — not Module 5/6's later `approver` extension. Nothing in Module 1 today is
  sensitive enough to need an admin-only gate, so `require_admin` exists but isn't called anywhere
  yet.
- `database/vista.db`'s existing rows (from real prior use across this project) are preserved
  as-is; the two new `id_number` columns are added to the live database via an idempotent
  `ALTER TABLE` on startup, not a destructive migration.
