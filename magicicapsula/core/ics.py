"""build a standard iCalendar (.ics) reminder for a capsule's unlock date.

pure text generation: no i/o, no network, no api. the user imports the
file into whatever calendar they like (google, apple, outlook). follows
rfc 5545 closely enough for every common calendar app -- utc timestamps,
folded lines, escaped text, a stable uid, and a display VALARM.
"""

import hashlib
from datetime import datetime, timedelta, timezone

_FOLD_LIMIT = 75  # rfc 5545 3.1: max octets per line before folding
# utf-8 continuation bytes match 0b10xxxxxx; used to back off mid-sequence
_UTF8_CONT_MASK = 0xC0
_UTF8_CONT_BITS = 0x80


def _stamp(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _escape(text: str) -> str:
    # rfc 5545 3.3.11: escape backslash first, then ; , and newlines.
    return (
        text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r\n", "\\n").replace("\n", "\\n")
    )


def _fold(line: str) -> str:
    # rfc 5545 3.1: lines over 75 octets fold onto a continuation line that
    # begins with a single space. fold on octets, backing off so a utf-8
    # multibyte sequence is never split across the boundary.
    raw = line.encode("utf-8")
    if len(raw) <= _FOLD_LIMIT:
        return line
    chunks = []
    limit = _FOLD_LIMIT  # the first line gets a full 75; folded lines lose one to the leading space
    while len(raw) > limit:
        cut = limit
        while cut > 0 and (raw[cut] & _UTF8_CONT_MASK) == _UTF8_CONT_BITS:
            cut -= 1
        chunks.append(raw[:cut])
        raw = raw[cut:]
        limit = _FOLD_LIMIT - 1
    chunks.append(raw)
    return "\r\n ".join(c.decode("utf-8") for c in chunks)


def _uid(name: str, unlock_at: datetime) -> str:
    # stable across re-runs for the same capsule, so re-importing updates
    # the event instead of creating a duplicate.
    digest = hashlib.sha1(f"{name}|{_stamp(unlock_at)}".encode()).hexdigest()
    return f"{digest[:16]}@magicicapsula"


def build(
    name: str,
    unlock_at: datetime,
    *,
    note: str = "",
    before_days: int = 0,
    now: datetime | None = None,
) -> str:
    """Return the .ics text for an unlock reminder. `name` is the capsule filename."""
    now = now or datetime.now(timezone.utc)
    start = unlock_at
    end = start + timedelta(minutes=30)
    summary = f"open time capsule: {name}"
    desc = note or f"the magicicapsula {name} unlocks now. run: magicicapsula open {name}"
    trigger = "PT0S" if before_days <= 0 else f"-P{before_days}D"

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//magicicapsula//capsule reminder//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{_uid(name, unlock_at)}",
        f"DTSTAMP:{_stamp(now)}",
        f"DTSTART:{_stamp(start)}",
        f"DTEND:{_stamp(end)}",
        f"SUMMARY:{_escape(summary)}",
        f"DESCRIPTION:{_escape(desc)}",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        f"DESCRIPTION:{_escape(summary)}",
        f"TRIGGER:{trigger}",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
