import os
from datetime import datetime, timezone

from magicicapsula.commands import _style
from magicicapsula.commands._util import fmt_remaining, read_capsule
from magicicapsula.core import capsule, ics


def register(sub):
    p = sub.add_parser(
        "remind",
        help="write a calendar (.ics) reminder for a capsule's unlock date",
    )
    p.add_argument("file", help="capsule file")
    p.add_argument("-o", "--out", metavar="FILE", help="output .ics path (default: <capsule>.ics)")
    p.add_argument(
        "-b",
        "--before",
        type=int,
        default=0,
        metavar="DAYS",
        help="remind this many days before the unlock date (default: on the day)",
    )
    p.add_argument("-f", "--force", action="store_true", help="overwrite the output if it exists")
    p.set_defaults(func=run)


def run(args):
    if args.before < 0:
        raise SystemExit("error: --before cannot be negative")

    info = capsule.inspect(read_capsule(args.file))
    name = os.path.basename(args.file)
    out = args.out or (os.path.splitext(args.file)[0] + ".ics")
    if os.path.exists(out) and not args.force:
        raise SystemExit(f"error: {out} already exists (use -f to overwrite)")

    text = ics.build(name, info.unlock_at, note=info.note, before_days=args.before)
    # newline="" keeps the rfc 5545 CRLF line endings exactly as written.
    with open(out, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)

    now = datetime.now(timezone.utc)
    print(f"reminder written to {out}")
    if info.is_open(now):
        print(_style.dim("          this capsule is already open"))
    else:
        print(_style.dim(f"          unlocks in {fmt_remaining(info.unlock_at - now)}"))
    print("import it into your calendar (google, apple, outlook, …)")
