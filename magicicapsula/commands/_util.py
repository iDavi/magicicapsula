"""small helpers shared by the commands. underscore name so it isn't a command."""

import getpass
from datetime import timedelta


def read_capsule(path):
    with open(path, "rb") as fh:
        return fh.read()


def ask_password(confirm=False):
    pw = getpass.getpass("password: ")
    if not pw:
        raise SystemExit("error: empty password")
    if confirm and pw != getpass.getpass("confirm password: "):
        raise SystemExit("error: passwords do not match")
    return pw


def fmt_remaining(delta: timedelta) -> str:
    secs = max(int(delta.total_seconds()), 0)
    days, secs = divmod(secs, 86400)
    hours, secs = divmod(secs, 3600)
    mins = secs // 60
    return f"{days}d {hours}h {mins}m"
