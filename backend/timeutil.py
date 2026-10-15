"""Time helpers shared by the models."""
from datetime import datetime, timezone


def utc_now_naive():
    """
    The current UTC time without a timezone, for `timestamp without time zone` columns.
    Same value the deprecated utcnow gave, without its warning.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
