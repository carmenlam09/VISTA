from datetime import datetime, timezone


def ensure_utc(dt: datetime) -> datetime:
    """SQLite drops tzinfo on round-trip, so a datetime read back from it
    comes back naive even though it was stored as UTC. Treat any naive
    datetime as UTC rather than comparing/serializing it ambiguously.
    (Same fix Module 2 and Module 4 needed.)"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
