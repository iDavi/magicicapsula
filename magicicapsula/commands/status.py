import os
from datetime import datetime

from magicicapsula.core import draft
from magicicapsula.commands import _style


def _fmt_size(n: int) -> str:
    size: float = n
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
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
    total_size = 0
    for p in d.staged:
        if p not in gone:
            try:
                total_size += os.path.getsize(p)
            except OSError:
                pass
    if total_size > 0:
        print(f", {_fmt_size(total_size)}")
    else:
        print()
    if gone:
        print(_style.yellow("warning: some staged files no longer exist; fix before sealing"))
