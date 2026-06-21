from magicicapsula import __version__
from magicicapsula.commands import _style


def register(sub):
    p = sub.add_parser("version", help="show the version and logo")
    p.set_defaults(func=run)


def run(args):
    print(_style.logo())
    print()
    print(f"  {_style.bold('magicicapsula')} {__version__}")
    print(f"  {_style.dim('seal files now, open them later')}")
