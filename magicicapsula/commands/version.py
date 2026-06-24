import argparse
from magicicapsula import __version__
from magicicapsula.commands import _style


def register(sub):
    p = sub.add_parser("version", help="show the version and logo")
    p.set_defaults(func=run)


def run(arg=None):
    print(_style.logo())
    print()
    print(f"  {_style.bold('magicicapsula')} {__version__}")
    print(f"  {_style.dim('seal files now, open them later')}")


class VersionPrintAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        run()
        parser.exit(0)
