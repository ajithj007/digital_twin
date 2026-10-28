"""Small helpers so every module handles time the same way.

All timestamps are stored in the database as UTC ISO strings (YYYY-MM-DDTHH:MM:SSZ).
Timetable logic uses Indian Standard Time (IST, UTC+05:30).
"""
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime(ISO_FORMAT)


def utcnow_iso() -> str:
    return to_iso(utcnow())


def parse_iso(value: str) -> datetime:
    return datetime.strptime(value, ISO_FORMAT).replace(tzinfo=timezone.utc)


def now_ist() -> datetime:
    return datetime.now(IST)


def age_seconds(iso_value, now=None):
    """Seconds since an ISO timestamp, or None if the timestamp is missing."""
    if not iso_value:
        return None
    now = now or utcnow()
    return (now - parse_iso(iso_value)).total_seconds()
