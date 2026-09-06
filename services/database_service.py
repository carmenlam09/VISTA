from pathlib import Path
import sqlite3
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "vista.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    return connection


def save_vendor(profile: dict[str, Any]) -> int:
    with get_connection() as connection:
        cursor = connection.execute("INSERT INTO vendors (vendor_name, registration_number, country, address) VALUES (?, ?, ?, ?)", (profile["vendor_name"], profile.get("registration_number"), profile.get("country"), profile.get("address")))
        vendor_id = cursor.lastrowid
        connection.executemany("INSERT INTO directors (vendor_id, director_name, nationality) VALUES (?, ?, ?)", [(vendor_id, item.get("director_name", ""), item.get("nationality", "")) for item in profile.get("directors", []) if item.get("director_name")])
        connection.executemany("INSERT INTO shareholders (vendor_id, shareholder_name, ownership_percentage) VALUES (?, ?, ?)", [(vendor_id, item.get("shareholder_name", ""), item.get("ownership_percentage")) for item in profile.get("shareholders", []) if item.get("shareholder_name")])
        connection.executemany("INSERT INTO ubos (vendor_id, ubo_name, ownership_percentage) VALUES (?, ?, ?)", [(vendor_id, item.get("ubo_name", ""), item.get("ownership_percentage")) for item in profile.get("ubo", []) if item.get("ubo_name")])
        connection.executemany("INSERT INTO related_parties (vendor_id, related_party_name, relationship_type) VALUES (?, ?, ?)", [(vendor_id, item.get("related_party_name", ""), item.get("relationship_type", "")) for item in profile.get("related_parties", []) if item.get("related_party_name")])
        return int(vendor_id)


def search_vendors(query: str = "") -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM vendors WHERE vendor_name LIKE ? OR registration_number LIKE ? ORDER BY created_date DESC", (f"%{query}%", f"%{query}%")).fetchall()
        return [dict(row) for row in rows]


def get_vendor(vendor_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        vendor = connection.execute("SELECT * FROM vendors WHERE vendor_id = ?", (vendor_id,)).fetchone()
        if not vendor:
            return None
        result = dict(vendor)
        for table, key in [("directors", "directors"), ("shareholders", "shareholders"), ("ubos", "ubo"), ("related_parties", "related_parties")]:
            result[key] = [dict(row) for row in connection.execute(f"SELECT * FROM {table} WHERE vendor_id = ?", (vendor_id,)).fetchall()]
        return result
