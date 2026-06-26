"""shared fixtures.

these keep config and the draft state hermetic: every test gets its own
XDG_CONFIG_HOME and cwd under tmp_path, so nothing touches the real machine.
"""

import argparse
from datetime import datetime, timedelta, timezone

import pytest

from magicicapsula.core import capsule


@pytest.fixture
def ns():
    """Build an argparse.Namespace the way the cli would hand one to run()."""
    return lambda **kw: argparse.Namespace(**kw)


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """Point the config file at a throwaway dir and clear the env override."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.delenv("MAGICICAPSULA_PASSWORD", raising=False)
    return tmp_path / "xdg"


@pytest.fixture
def in_tmp(tmp_path, monkeypatch):
    """Run the test with cwd inside an empty tmp dir."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def sample_files(tmp_path):
    """A couple of real files on disk to seal."""
    a = tmp_path / "letter.txt"
    a.write_text("dear future me\n", encoding="utf-8")
    b = tmp_path / "note.txt"
    b.write_text("second\n", encoding="utf-8")
    return [str(a), str(b)]


@pytest.fixture
def past():
    return datetime.now(timezone.utc) - timedelta(days=1)


@pytest.fixture
def future():
    return datetime.now(timezone.utc) + timedelta(days=30)


@pytest.fixture
def make_capsule(sample_files):
    """Seal `sample_files` into a blob; defaults to an already-unlocked capsule."""

    def build(password="hunter2", unlock_at=None, note="", paths=None):
        unlock_at = unlock_at or (datetime.now(timezone.utc) - timedelta(days=1))
        return capsule.seal(paths or sample_files, password, unlock_at, note=note)

    return build


@pytest.fixture
def capsule_file(tmp_path, make_capsule):
    """A sealed, unlocked capsule written to disk; returns (path, password)."""
    blob = make_capsule()
    path = tmp_path / "capsule.mcap"
    path.write_bytes(blob)
    return str(path), "hunter2"
