"""small helpers shared by the commands. underscore name so it isn't a command."""

import calendar
import getpass
import re
from datetime import datetime, timedelta

from magicicapsula.core import config

_RELATIVE = re.compile(r"^\+(\d+)([dwmy])$", re.IGNORECASE)


def read_capsule(path):
    with open(path, "rb") as fh:
        return fh.read()


def ask_password(confirm=False):
    configured = config.get("password")
    if configured:
        return configured
    pw = getpass.getpass("password: ")
    if not pw:
        raise SystemExit("error: empty password")
    if confirm and pw != getpass.getpass("confirm password: "):
        raise SystemExit("error: passwords do not match")
    return pw


def _add_months(dt: datetime, months: int) -> datetime:
    total = dt.month - 1 + months
    year = dt.year + total // 12
    month = total % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])  # clamp e.g. Jan 31 + 1m
    return dt.replace(year=year, month=month, day=day)


def parse_unlock(s: str) -> datetime:
    """Absolute ISO (YYYY-MM-DD[THH:MM]) or relative (+30d, +2w, +6m, +1y)."""
    s = s.strip()
    m = _RELATIVE.match(s)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
        base = datetime.now().astimezone()
        if unit == "d":
            return base + timedelta(days=n)
        if unit == "w":
            return base + timedelta(weeks=n)
        return _add_months(base, n if unit == "m" else n * 12)
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        raise SystemExit(f"error: bad date {s!r} (use YYYY-MM-DD, YYYY-MM-DDTHH:MM, or +30d/+2w/+6m/+1y)") from None
    return dt.astimezone() if dt.tzinfo is None else dt  # naive means local time


def fmt_remaining(delta: timedelta) -> str:
    secs = max(int(delta.total_seconds()), 0)
    days, secs = divmod(secs, 86400)
    hours, secs = divmod(secs, 3600)
    mins = secs // 60
    return f"{days}d {hours}h {mins}m"
