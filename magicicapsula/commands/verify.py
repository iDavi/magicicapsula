from magicicapsula.commands import _style
from magicicapsula.commands._util import ask_password, read_capsule
from magicicapsula.core import capsule


def register(sub):
    p = sub.add_parser("verify", help="check a capsule's integrity with the password, without opening")
    p.add_argument("file", help="capsule file")
    p.set_defaults(func=run)


def run(args):
    blob = read_capsule(args.file)
    info = capsule.inspect(blob)
    pw = None if info.cipher == "none" else ask_password()
    capsule.verify(blob, pw)
    tail = "" if pw is None else " and the password is correct"
    print(_style.green(f"ok, capsule is intact{tail}"))
