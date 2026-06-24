import contextlib
import os
from datetime import datetime

from magicicapsula.commands import _style
from magicicapsula.core import draft

_UNIT_STEP = 1024  # bytes per unit; promote to KB/MB/... at each step


def _fmt_size(n: int) -> str:
    size: float = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        # promote to the next unit once the value would render as 1024.x here
        if round(size, 0 if unit == "B" else 1) < _UNIT_STEP:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= _UNIT_STEP
    return f"{size:.1f} PB"


def register(sub):
    p = sub.add_parser("status", help="show the draft: unlock date and staged files")
    p.set_defaults(func=run)


def run(args):
    d = draft.load()
    print(_style.bold(f"draft at {d.dir}"))

    if d.unlock_at:
        dt = datetime.fromisoformat(d.unlock_at)
        dt = dt.astimezone() if dt.tzinfo is None else dt
        print(f"unlocks: {dt.isoformat()}")
    else:
        print("unlocks: not set (pass --unlock at init or seal)")
    if d.note:
        print(f"note:    {d.note}")
    print(f"output:  {d.out}")
    print()

    if not d.staged:
        print("nothing staged. use: magicicapsula add <files>")
        return

    gone = set(draft.missing(d))
    print("staged:")
    for p in d.staged:
        print(f"  {p}{_style.red('  (missing)') if p in gone else ''}")
    print(f"\n{len(d.staged)} item(s) staged", end="")
    present = [p for p in d.staged if p not in gone]
    total_size = 0
    for p in present:
        with contextlib.suppress(OSError):
            total_size += os.path.getsize(p)
    if present:
        print(f", {_fmt_size(total_size)}")
    else:
        print()
    if gone:
        print(_style.yellow("warning: some staged files no longer exist; fix before sealing"))
