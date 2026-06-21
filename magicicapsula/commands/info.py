from datetime import datetime, timezone

from magicicapsula.core import capsule
from magicicapsula.commands import _style
from magicicapsula.commands._util import fmt_remaining, read_capsule


def register(sub):
    p = sub.add_parser("info", help="show a capsule's dates and status (no password needed)")
    p.add_argument("file", help="capsule file")
    p.set_defaults(func=run)


def run(args):
    info = capsule.inspect(read_capsule(args.file))
    now = datetime.now(timezone.utc)
    print(f"created:  {info.created_at.astimezone().isoformat()}")
    print(f"unlocks:  {info.unlock_at.astimezone().isoformat()}")
    print(f"cipher:   {info.cipher}")
    if info.cipher == "none":
        print(_style.dim("          no password, opens for anyone after the unlock date"))
    if info.note:
        print(f"note:     {info.note}")
    if info.is_open(now):
        print(f"status:   {_style.green('open')}, the unlock date has passed")
    else:
        print(f"status:   {_style.yellow('locked')}, {fmt_remaining(info.unlock_at - now)} remaining")
