-- Reference only as of the Module 1 alignment refactor — the live schema is
-- now owned by the SQLAlchemy models in app/models/vendor.py and app/models/
-- audit.py, created via Base.metadata.create_all() and upgraded in place by
-- app/db/session.py::_upgrade_existing_tables() (the id_number columns were
-- added to an already-populated database via idempotent ALTER TABLE, not a
-- destructive migration). Kept here as a human-readable reference matching
-- what those models actually produce.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS vendors (
    vendor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_name TEXT NOT NULL,
    registration_number TEXT,
    country TEXT,
    address TEXT,
    created_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS directors (
    director_id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id INTEGER NOT NULL REFERENCES vendors(vendor_id) ON DELETE CASCADE,
    director_name TEXT NOT NULL,
    nationality TEXT,
    id_number TEXT  -- added by the alignment refactor; NRIC/passport, nullable
);
CREATE TABLE IF NOT EXISTS shareholders (
    shareholder_id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id INTEGER NOT NULL REFERENCES vendors(vendor_id) ON DELETE CASCADE,
    shareholder_name TEXT NOT NULL,
    ownership_percentage REAL,
    id_number TEXT  -- added by the alignment refactor; nullable
);
CREATE TABLE IF NOT EXISTS ubos (
    ubo_id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id INTEGER NOT NULL REFERENCES vendors(vendor_id) ON DELETE CASCADE,
    ubo_name TEXT NOT NULL,
    ownership_percentage REAL,
    id_number TEXT  -- added by the alignment refactor; nullable
);
CREATE TABLE IF NOT EXISTS related_parties (
    related_party_id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id INTEGER NOT NULL REFERENCES vendors(vendor_id) ON DELETE CASCADE,
    related_party_name TEXT NOT NULL,
    relationship_type TEXT
);
CREATE INDEX IF NOT EXISTS idx_vendors_name ON vendors(vendor_name);
CREATE INDEX IF NOT EXISTS idx_vendors_registration ON vendors(registration_number);

-- Added by the alignment refactor (see app/models/audit.py):
CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    actor_id TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    action TEXT NOT NULL,
    vendor_id INTEGER,
    detail TEXT,
    created_at DATETIME NOT NULL
);
