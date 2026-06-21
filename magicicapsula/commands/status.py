from datetime import datetime

from magicicapsula.core import draft
from magicicapsula.commands import _style


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
    print(f"\n{len(d.staged)} item(s) staged")
    if gone:
        print(_style.yellow("warning: some staged files no longer exist; fix before sealing"))
