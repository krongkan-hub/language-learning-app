"""Small helpers every table module uses."""
from datetime import datetime, timezone


def _utcnow() -> str:
    """ISO-8601 UTC timestamp, no microseconds."""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
