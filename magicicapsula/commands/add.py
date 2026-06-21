from magicicapsula.core import draft


def register(sub):
    p = sub.add_parser("add", help="stage files or folders to put in the capsule")
    p.add_argument("paths", nargs="+", help="files or folders to stage")
    p.set_defaults(func=run)


def run(args):
    d = draft.load()
    added = draft.add(d, args.paths)
    if not added:
        print("nothing new to stage")
        return
    for p in added:
        print(f"  staged {p}")
    print(f"{len(d.staged)} item(s) staged in total")
