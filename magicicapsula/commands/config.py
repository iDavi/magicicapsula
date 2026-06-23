import os

from magicicapsula.core import config
from magicicapsula.commands import _style


def register(sub):
    p = sub.add_parser("config", help="show configuration and where each value comes from")
    p.set_defaults(func=run)


def run(args):
    path = config.config_path()
    found = os.path.exists(path)
    print(f"config file: {path}")
    print(_style.dim("             " + ("found" if found else "not present")))
    print()
    for key in config.keys():
        value, source = config.resolve(key)
        print(f"  {key} = {config.display(key, value)}  {_style.dim('(' + source + ')')}")
