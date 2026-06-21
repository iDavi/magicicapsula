"""the staging area ("draft") for building a capsule.

state lives in a .capsule/ directory, found by walking up from the cwd.
init creates it, add stages paths, status reports, and seal packs the
staged paths into a .mcap file.

staged entries are absolute paths to the current files on disk; their
contents are read at seal time, not copied when you add them.

no argparse, no printing here.
"""

import json
import os
from dataclasses import dataclass, field

from .errors import NoDraft

DRAFT_DIR = ".capsule"
CONFIG = "config.json"
VERSION = 1


@dataclass
class Draft:
    root: str                       # directory containing .capsule/
    unlock_at: str | None = None    # ISO date/datetime as typed by the user
    note: str = ""
    out: str = "capsule.mcap"
    staged: list[str] = field(default_factory=list)  # absolute paths

    @property
    def dir(self) -> str:
        return os.path.join(self.root, DRAFT_DIR)

    @property
    def config_path(self) -> str:
        return os.path.join(self.dir, CONFIG)


def find_root(start: str | None = None) -> str:
    path = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.isdir(os.path.join(path, DRAFT_DIR)):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            raise NoDraft("no capsule here (run `magicicapsula init` first)")
        path = parent


def init(root: str | None = None) -> Draft:
    root = os.path.abspath(root or os.getcwd())
    draft = Draft(root=root)
    if os.path.exists(draft.dir):
        raise FileExistsError(draft.dir)
    os.makedirs(draft.dir)
    save(draft)
    return draft


def load(root: str | None = None) -> Draft:
    root = root or find_root()
    draft = Draft(root=root)
    with open(draft.config_path, encoding="utf-8") as fh:
        data = json.load(fh)
    draft.unlock_at = data.get("unlock_at")
    draft.note = data.get("note", "")
    draft.out = data.get("out", "capsule.mcap")
    draft.staged = data.get("staged", [])
    return draft


def save(draft: Draft) -> None:
    data = {
        "v": VERSION,
        "unlock_at": draft.unlock_at,
        "note": draft.note,
        "out": draft.out,
        "staged": draft.staged,
    }
    with open(draft.config_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def add(draft: Draft, paths) -> list[str]:
    added = []
    for p in paths:
        ap = os.path.abspath(p)
        if not os.path.exists(ap):
            raise FileNotFoundError(p)
        if ap not in draft.staged:
            draft.staged.append(ap)
            added.append(ap)
    save(draft)
    return added


def remove(draft: Draft, paths) -> list[str]:
    targets = {os.path.abspath(p) for p in paths}
    removed = [s for s in draft.staged if s in targets]
    draft.staged = [s for s in draft.staged if s not in targets]
    save(draft)
    return removed


def missing(draft: Draft) -> list[str]:
    return [p for p in draft.staged if not os.path.exists(p)]
