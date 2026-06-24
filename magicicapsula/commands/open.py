from datetime import datetime, timezone

from magicicapsula.commands import _style
from magicicapsula.commands._util import ask_password, fmt_remaining, read_capsule
from magicicapsula.core import capsule


def register(sub):
    p = sub.add_parser("open", help="open a capsule and extract it once the unlock date has passed")
    p.add_argument("file", help="capsule file")
    p.add_argument("-d", "--dest", default=".", help="directory to extract into")
    p.set_defaults(func=run)


def run(args):
    blob = read_capsule(args.file)
    info = capsule.inspect(blob)
    now = datetime.now(timezone.utc)
    if not info.is_open(now):
        raise SystemExit(
            f"error: locked until {info.unlock_at.astimezone().isoformat()} "
            f"({fmt_remaining(info.unlock_at - now)} remaining)"
        )

    pw = None if info.cipher == "none" else ask_password()
    names = capsule.open_capsule(blob, pw, args.dest)
    print(_style.green(f"opened into {args.dest}/"))
    for name in names:
        print(f"  {_style.dim(name)}")
