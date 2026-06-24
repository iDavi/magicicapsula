import sys

from magicicapsula.core import draft


def register(sub):
    p = sub.add_parser("add", help="stage files or folders to put in the capsule")
    p.add_argument("paths", nargs="*", help="files or folders to stage (use - to read stdin)")
    p.add_argument("--text", metavar="TEXT", help="stage this text directly, no file needed")
    p.add_argument(
        "--name", metavar="NAME", default="note.txt", help="filename for --text or stdin (default: note.txt)"
    )
    p.set_defaults(func=run)


def run(args):
    if not args.paths and args.text is None:
        raise SystemExit("error: nothing to add (give files, --text, or - for stdin)")

    d = draft.load()
    added = []
    if args.text is not None:
        added.append(draft.stage_text(d, args.text, args.name))

    files = []
    for p in args.paths:
        if p == "-":
            added.append(draft.stage_text(d, sys.stdin.buffer.read(), args.name))
        else:
            files.append(p)
    if files:
        added += draft.add(d, files)

    if not added:
        print("nothing new to stage")
        return
    for p in added:
        print(f"  staged {p}")
    print(f"{len(d.staged)} item(s) staged in total")
