from magicicapsula.core import draft


def register(sub):
    p = sub.add_parser("rm", help="unstage files (does not delete them from disk)")
    p.add_argument("paths", nargs="+", help="staged paths to drop from the capsule")
    p.set_defaults(func=run)


def run(args):
    d = draft.load()
    removed = draft.remove(d, args.paths)
    if not removed:
        print("none of those were staged")
        return
    for p in removed:
        print(f"  unstaged {p}")
