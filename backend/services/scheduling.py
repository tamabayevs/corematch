"""
CoreMatch — Weekend-Aware Scheduling Utility
MENA weekend = Friday + Saturday (UTC+3 Asia/Riyadh).
"""
from datetime import datetime
from dateutil import tz

MENA_TZ = tz.gettz("Asia/Riyadh")
MENA_WEEKEND_DAYS = {4, 5}  # Monday=0 ... Friday=4, Saturday=5


def is_mena_weekend(dt=None):
    """
    Check if a given datetime falls on a MENA weekend (Friday/Saturday).
    Uses Asia/Riyadh timezone (UTC+3). Defaults to current time.
    """
    if dt is None:
        dt = datetime.now(MENA_TZ)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=MENA_TZ)
    return dt.weekday() in MENA_WEEKEND_DAYS


def get_weekend_warning():
    """Return a human-readable warning for MENA weekend sends."""
    return (
        "It is currently a MENA weekend (Friday/Saturday). "
        "Recipients may not see messages until Sunday."
    )
