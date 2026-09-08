from datetime import datetime, timezone


def ensure_utc(dt: datetime) -> datetime:
    """SQLite drops tzinfo on round-trip, so a datetime read back from it
    comes back naive even though it was stored as UTC. Treat any naive
    datetime as UTC rather than comparing/serializing it ambiguously.
    (Same fix Modules 2, 4, and 5 needed.)"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
