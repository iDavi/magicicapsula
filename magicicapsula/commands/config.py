import os

from magicicapsula.core import config
from magicicapsula.commands import _style


def register(sub):
    p = sub.add_parser("config", help="show or edit configuration")
    p.add_argument("action", nargs="?", default="list",
                   choices=["list", "get", "set", "unset"],
                   help="list (default), get, set, or unset a setting")
    p.add_argument("key", nargs="?", help="setting name")
    p.add_argument("value", nargs="?", help="value, for set")
    p.add_argument("--reveal", action="store_true", help="show secret values instead of masking")
    p.set_defaults(func=run)


def _require_key(args):
    if not args.key:
        raise SystemExit(f"error: {args.action} needs a key (one of: {', '.join(config.keys())})")
    if not config.is_known(args.key):
        raise SystemExit(f"error: unknown setting {args.key!r} (known: {', '.join(config.keys())})")


def run(args):
    if args.action == "list":
        _list(args.reveal)
    elif args.action == "get":
        _require_key(args)
        value, source = config.resolve(args.key)
        print(f"{config.display(args.key, value, args.reveal)}  {_style.dim('(' + source + ')')}")
    elif args.action == "set":
        _require_key(args)
        if args.value is None:
            raise SystemExit("error: set needs a value (usage: config set <key> <value>)")
        config.set_value(args.key, args.value)
        print(_style.green(f"set {args.key} in {config.config_path()}"))
    elif args.action == "unset":
        _require_key(args)
        if config.unset(args.key):
            print(_style.green(f"unset {args.key}"))
        else:
            print(_style.dim(f"{args.key} was not set in the config file"))


def _list(reveal):
    path = config.config_path()
    print(f"config file: {path}")
    print(_style.dim("             " + ("found" if os.path.exists(path) else "not present")))
    print()
    for key in config.keys():
        value, source = config.resolve(key)
        print(f"  {key} = {config.display(key, value, reveal)}  {_style.dim('(' + source + ')')}")
