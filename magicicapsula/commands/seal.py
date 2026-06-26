import os
import sys
from datetime import datetime, timezone

from magicicapsula.commands import _style
from magicicapsula.commands._util import ask_password, parse_unlock
from magicicapsula.core import capsule, draft


def register(sub):
    p = sub.add_parser("seal", help="seal everything staged into a capsule file")
    p.add_argument("-u", "--unlock", metavar="DATE", help="unlock date, overrides the draft's")
    p.add_argument("-o", "--out", metavar="FILE", help="output capsule file, overrides the draft's")
    p.add_argument("-n", "--note", help="plaintext note, overrides the draft's")
    p.add_argument("-f", "--force", action="store_true", help="overwrite the output if it exists")
    p.add_argument(
        "-P", "--no-password", action="store_true", help="seal without a password (anyone can open it after the date)"
    )
    p.set_defaults(func=run)


def run(args):
    d = draft.load()

    # flags override the draft and stick, so status keeps showing the right thing.
    # relative dates are resolved to absolute here, anchored to now.
    if args.unlock is not None:
        d.unlock_at = parse_unlock(args.unlock).isoformat()
    if args.note is not None:
        d.note = args.note
    if args.out is not None:
        d.out = args.out
    draft.save(d)

    if not d.unlock_at:
        raise SystemExit("error: no unlock date set (use --unlock, or set one at init)")
    if not d.staged:
        raise SystemExit("error: nothing staged (use: magicicapsula add <files>)")
    gone = draft.missing(d)
    if gone:
        raise SystemExit("error: staged files no longer exist:\n  " + "\n  ".join(gone))

    unlock_at = parse_unlock(d.unlock_at)
    if unlock_at <= datetime.now(timezone.utc):
        print("warning: unlock date is not in the future", file=sys.stderr)

    out = d.out if os.path.isabs(d.out) else os.path.join(d.root, d.out)
    if os.path.exists(out) and not args.force:
        raise SystemExit(f"error: {out} already exists (use --force to overwrite)")

    pw = None if args.no_password else ask_password(confirm=True)
    blob = capsule.seal(d.staged, pw, unlock_at, note=d.note)
    with open(out, "wb") as fh:
        fh.write(blob)

    print(_style.logo())
    print(_style.green(f"sealed {len(d.staged)} item(s) into {out}"))
    print(f"unlocks: {unlock_at.astimezone().isoformat()}")
    if pw is None:
        print(_style.dim("no password set, so anyone can open it after that date"))
