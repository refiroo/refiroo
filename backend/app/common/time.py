from datetime import UTC, datetime


def as_utc(value: datetime) -> datetime:
    """Return an aware UTC datetime, treating naive values as already UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
