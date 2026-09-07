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
    nationality TEXT
);
CREATE TABLE IF NOT EXISTS shareholders (
    shareholder_id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id INTEGER NOT NULL REFERENCES vendors(vendor_id) ON DELETE CASCADE,
    shareholder_name TEXT NOT NULL,
    ownership_percentage REAL
);
CREATE TABLE IF NOT EXISTS ubos (
    ubo_id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id INTEGER NOT NULL REFERENCES vendors(vendor_id) ON DELETE CASCADE,
    ubo_name TEXT NOT NULL,
    ownership_percentage REAL
);
CREATE TABLE IF NOT EXISTS related_parties (
    related_party_id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id INTEGER NOT NULL REFERENCES vendors(vendor_id) ON DELETE CASCADE,
    related_party_name TEXT NOT NULL,
    relationship_type TEXT
);
CREATE INDEX IF NOT EXISTS idx_vendors_name ON vendors(vendor_name);
CREATE INDEX IF NOT EXISTS idx_vendors_registration ON vendors(registration_number);
