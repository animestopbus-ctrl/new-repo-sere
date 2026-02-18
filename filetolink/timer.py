# timer.py — secure, timezone-safe token & expiry helpers
from __future__ import annotations
import secrets
import datetime
from typing import Optional

UTC = datetime.timezone.utc


def generate_hash(length: int = 12) -> str:
    """
    Generate a URL-safe, high-entropy token.

    - Uses `secrets.token_urlsafe` (crypto RNG).
    - `length` is the desired visible string length (clamped 6..128).
    """
    if length < 6:
        raise ValueError("length must be >= 6")
    if length > 128:
        raise ValueError("length must be <= 128")

    # token_urlsafe produces ~1.3 chars per byte; compute nbytes conservatively
    nbytes = max(8, int(length * 0.8) + 1)
    return secrets.token_urlsafe(nbytes)[:length]


def get_expiry_date(hours: int = 1) -> datetime.datetime:
    """
    Return a timezone-aware UTC expiry datetime `hours` from now.
    Microseconds are stripped for cleaner DB storage.
    """
    if hours < 0:
        raise ValueError("hours must be >= 0")
    return (datetime.datetime.now(UTC).replace(microsecond=0)
            + datetime.timedelta(hours=hours))


def is_expired(expiry: datetime.datetime, now: Optional[datetime.datetime] = None) -> bool:
    """
    Check if `expiry` (tz-aware) is past the current time.
    If `now` not provided, uses current UTC time.
    """
    if expiry.tzinfo is None:
        raise ValueError("expiry must be timezone-aware")
    now = now or datetime.datetime.now(UTC)
    return now >= expiry


def ttl_seconds(expiry: datetime.datetime, now: Optional[datetime.datetime] = None) -> int:
    """
    Return remaining seconds until expiry.
    Returns 0 if already expired.
    """
    if expiry.tzinfo is None:
        raise ValueError("expiry must be timezone-aware")
    now = now or datetime.datetime.now(UTC)
    delta = expiry - now
    return max(0, int(delta.total_seconds()))


# Optional helpers for ISO storage / parsing (handy for JSON / DB)
def expiry_to_iso(expiry: datetime.datetime) -> str:
    """Convert tz-aware expiry to ISO-8601 string (UTC)."""
    if expiry.tzinfo is None:
        raise ValueError("expiry must be timezone-aware")
    return expiry.astimezone(UTC).isoformat()


def iso_to_expiry(s: str) -> datetime.datetime:
    """
    Parse ISO-8601 expiry string into tz-aware datetime.
    Accepts strings with or without timezone — if no tz, assume UTC.
    """
    dt = datetime.datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt
