import argparse
import importlib
import pkgutil
import sys

from magicicapsula import commands
from magicicapsula.commands import _style
from magicicapsula.core.errors import CapsuleError


def build_parser():
    parser = argparse.ArgumentParser(
        prog="magicicapsula",
        description="seal files now, open them later",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    # every non-underscore module in commands/ with a register() becomes a command.
    # drop in a new file and it shows up, nothing else to wire.
    for _, name, _ in pkgutil.iter_modules(commands.__path__):
        if name.startswith("_"):
            continue
        mod = importlib.import_module(f"magicicapsula.commands.{name}")
        if hasattr(mod, "register"):
            mod.register(sub)

    return parser


def main():
    args = build_parser().parse_args()
    try:
        args.func(args)
    except CapsuleError as exc:
        sys.exit(_style.red(f"error: {exc}"))
    except FileNotFoundError as exc:
        sys.exit(_style.red(f"error: no such file: {exc}"))
