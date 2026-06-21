"""colors and the logo. presentation only, so it stays in the cli layer.

colors switch off automatically when output isn't a terminal, or when
NO_COLOR is set, so piped/redirected output stays clean.
"""

import os
import re
import sys
from importlib import resources

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def enabled():
    return (
        sys.stdout.isatty()
        and os.environ.get("NO_COLOR") is None
        and os.environ.get("TERM") != "dumb"
    )


def paint(text, code):
    return f"\x1b[{code}m{text}\x1b[0m" if enabled() else text


def bold(t):
    return paint(t, "1")


def dim(t):
    return paint(t, "2")


def red(t):
    return paint(t, "31")


def green(t):
    return paint(t, "32")


def yellow(t):
    return paint(t, "33")


def cyan(t):
    return paint(t, "36")


def logo():
    text = resources.files("magicicapsula").joinpath("assets/logo.txt").read_text(encoding="utf-8")
    lines = text.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    text = "\n".join(lines)
    return text if enabled() else _ANSI.sub("", text)
