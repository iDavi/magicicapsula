from magicicapsula.commands._util import parse_unlock
from magicicapsula.core import draft


def register(sub):
    p = sub.add_parser("init", help="start a new capsule draft in the current directory")
    p.add_argument("-u", "--unlock", metavar="DATE", help="unlock date, can also be set at seal")
    p.add_argument("-n", "--note", default="", help="plaintext note shown by info")
    p.add_argument("-o", "--out", default="capsule.mcap", help="output file name")
    p.set_defaults(func=run)


def run(args):
    try:
        d = draft.init()
    except FileExistsError:
        raise SystemExit("error: a capsule draft already exists here (.capsule/)") from None

    if args.unlock:
        d.unlock_at = parse_unlock(args.unlock).isoformat()  # resolve +30d/+1y etc. now
    d.note = args.note
    d.out = args.out
    draft.save(d)

    print(f"new capsule draft in {d.dir}")
    print("next: magicicapsula add <files...>")
