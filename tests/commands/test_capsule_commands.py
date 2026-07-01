"""spec: seal/open/info/verify/remind print the right thing.

per the testing strategy, these assert the final printed result with the core
calls mocked out — the command layer's job is wiring and presentation, so
that's exactly the contract under test here.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from magicicapsula.commands import info as info_cmd
from magicicapsula.commands import open as open_cmd
from magicicapsula.commands import remind as remind_cmd
from magicicapsula.commands import seal as seal_cmd
from magicicapsula.commands import verify as verify_cmd


def _info(**kw):
    base = dict(
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        unlock_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        cipher="aes-256-gcm",
        note="",
    )
    base.update(kw)
    is_open = base.pop("_open", False)
    ns = SimpleNamespace(**base)
    ns.is_open = lambda now=None: is_open
    ns.remaining = lambda now=None: timedelta(days=10)
    return ns


# --- seal ---------------------------------------------------------------


def test_seal_writes_blob_and_reports(tmp_path, monkeypatch, capsys):
    d = SimpleNamespace(unlock_at="2030-01-01T00:00:00", note="", out="capsule.mcap", staged=["/a"], root=str(tmp_path))
    monkeypatch.setattr(seal_cmd.draft, "load", lambda: d)
    monkeypatch.setattr(seal_cmd.draft, "save", lambda d: None)
    monkeypatch.setattr(seal_cmd.draft, "missing", lambda d: [])
    monkeypatch.setattr(seal_cmd, "parse_unlock", lambda s: datetime(2030, 1, 1, tzinfo=timezone.utc))
    monkeypatch.setattr(seal_cmd, "ask_password", lambda confirm=False: "pw")
    monkeypatch.setattr(seal_cmd.capsule, "seal", lambda *a, **k: b"BLOB")

    args = SimpleNamespace(unlock=None, note=None, out=None, force=False, no_password=False, rm=False)
    seal_cmd.run(args)

    out = capsys.readouterr().out
    assert "sealed 1 item(s)" in out
    assert (tmp_path / "capsule.mcap").read_bytes() == b"BLOB"


def test_seal_without_password_notes_it(tmp_path, monkeypatch, capsys):
    d = SimpleNamespace(unlock_at="2030-01-01T00:00:00", note="", out="c.mcap", staged=["/a"], root=str(tmp_path))
    monkeypatch.setattr(seal_cmd.draft, "load", lambda: d)
    monkeypatch.setattr(seal_cmd.draft, "save", lambda d: None)
    monkeypatch.setattr(seal_cmd.draft, "missing", lambda d: [])
    monkeypatch.setattr(seal_cmd, "parse_unlock", lambda s: datetime(2030, 1, 1, tzinfo=timezone.utc))
    monkeypatch.setattr(seal_cmd.capsule, "seal", lambda *a, **k: b"B")

    args = SimpleNamespace(unlock=None, note=None, out=None, force=False, no_password=True, rm=False)
    seal_cmd.run(args)
    assert "anyone can open it" in capsys.readouterr().out


def test_seal_applies_flag_overrides(tmp_path, monkeypatch, capsys):
    d = SimpleNamespace(unlock_at=None, note="", out="orig.mcap", staged=["/a"], root=str(tmp_path))
    monkeypatch.setattr(seal_cmd.draft, "load", lambda: d)
    monkeypatch.setattr(seal_cmd.draft, "save", lambda d: None)
    monkeypatch.setattr(seal_cmd.draft, "missing", lambda d: [])
    monkeypatch.setattr(seal_cmd, "parse_unlock", lambda s: datetime(2030, 1, 1, tzinfo=timezone.utc))
    monkeypatch.setattr(seal_cmd.capsule, "seal", lambda *a, **k: b"B")

    args = SimpleNamespace(
        unlock="2030-01-01", note="overridden", out="new.mcap", force=False, no_password=True, rm=False
    )
    seal_cmd.run(args)
    # the flags overrode the draft and stuck
    assert d.note == "overridden" and d.out == "new.mcap"
    assert (tmp_path / "new.mcap").exists()


def test_seal_errors_on_missing_staged_files(tmp_path, monkeypatch):
    d = SimpleNamespace(unlock_at="2030-01-01T00:00:00", note="", out="c.mcap", staged=["/gone"], root=str(tmp_path))
    monkeypatch.setattr(seal_cmd.draft, "load", lambda: d)
    monkeypatch.setattr(seal_cmd.draft, "save", lambda d: None)
    monkeypatch.setattr(seal_cmd.draft, "missing", lambda d: ["/gone"])
    monkeypatch.setattr(seal_cmd, "parse_unlock", lambda s: datetime(2030, 1, 1, tzinfo=timezone.utc))
    with pytest.raises(SystemExit, match="no longer exist"):
        seal_cmd.run(SimpleNamespace(unlock=None, note=None, out=None, force=False, no_password=True, rm=False))


def test_seal_warns_when_unlock_in_the_past(tmp_path, monkeypatch, capsys):
    d = SimpleNamespace(unlock_at="2000-01-01T00:00:00", note="", out="c.mcap", staged=["/a"], root=str(tmp_path))
    monkeypatch.setattr(seal_cmd.draft, "load", lambda: d)
    monkeypatch.setattr(seal_cmd.draft, "save", lambda d: None)
    monkeypatch.setattr(seal_cmd.draft, "missing", lambda d: [])
    monkeypatch.setattr(seal_cmd, "parse_unlock", lambda s: datetime(2000, 1, 1, tzinfo=timezone.utc))
    monkeypatch.setattr(seal_cmd.capsule, "seal", lambda *a, **k: b"B")
    seal_cmd.run(SimpleNamespace(unlock=None, note=None, out=None, force=False, no_password=True, rm=False))
    assert "not in the future" in capsys.readouterr().err


def test_seal_errors_without_unlock_date(tmp_path, monkeypatch):
    d = SimpleNamespace(unlock_at=None, note="", out="c.mcap", staged=["/a"], root=str(tmp_path))
    monkeypatch.setattr(seal_cmd.draft, "load", lambda: d)
    monkeypatch.setattr(seal_cmd.draft, "save", lambda d: None)
    with pytest.raises(SystemExit, match="no unlock date"):
        seal_cmd.run(SimpleNamespace(unlock=None, note=None, out=None, force=False, no_password=True, rm=False))


def test_seal_errors_when_nothing_staged(tmp_path, monkeypatch):
    d = SimpleNamespace(unlock_at="2030-01-01", note="", out="c.mcap", staged=[], root=str(tmp_path))
    monkeypatch.setattr(seal_cmd.draft, "load", lambda: d)
    monkeypatch.setattr(seal_cmd.draft, "save", lambda d: None)
    with pytest.raises(SystemExit, match="nothing staged"):
        seal_cmd.run(SimpleNamespace(unlock=None, note=None, out=None, force=False, no_password=True, rm=False))


def test_seal_refuses_to_clobber_without_force(tmp_path, monkeypatch):
    (tmp_path / "c.mcap").write_bytes(b"old")
    d = SimpleNamespace(unlock_at="2030-01-01T00:00:00", note="", out="c.mcap", staged=["/a"], root=str(tmp_path))
    monkeypatch.setattr(seal_cmd.draft, "load", lambda: d)
    monkeypatch.setattr(seal_cmd.draft, "save", lambda d: None)
    monkeypatch.setattr(seal_cmd.draft, "missing", lambda d: [])
    monkeypatch.setattr(seal_cmd, "parse_unlock", lambda s: datetime(2030, 1, 1, tzinfo=timezone.utc))
    with pytest.raises(SystemExit, match="already exists"):
        seal_cmd.run(SimpleNamespace(unlock=None, note=None, out=None, force=False, no_password=True, rm=False))


def test_seal_verifies_written_size(tmp_path, monkeypatch):
    """A size mismatch after write raises an error."""
    d = SimpleNamespace(unlock_at="2030-01-01T00:00:00", note="", out="c.mcap", staged=["/a"], root=str(tmp_path))
    monkeypatch.setattr(seal_cmd.draft, "load", lambda: d)
    monkeypatch.setattr(seal_cmd.draft, "save", lambda d: None)
    monkeypatch.setattr(seal_cmd.draft, "missing", lambda d: [])
    monkeypatch.setattr(seal_cmd, "parse_unlock", lambda s: datetime(2030, 1, 1, tzinfo=timezone.utc))
    monkeypatch.setattr(seal_cmd, "ask_password", lambda confirm=False: "pw")
    monkeypatch.setattr(seal_cmd.capsule, "seal", lambda *a, **k: b"BLOB")
    # Simulate a write corruption by lying about the file size
    original_getsize = os.path.getsize

    def fake_getsize(path):
        return original_getsize(path) + 99

    monkeypatch.setattr(os.path, "getsize", fake_getsize)

    with pytest.raises(SystemExit, match="corrupted during write"):
        seal_cmd.run(SimpleNamespace(unlock=None, note=None, out=None, force=False, no_password=True, rm=False))


# --- seal with --rm -----------------------------------------------------


def test_seal_with_rm_deletes_staged_files(tmp_path, monkeypatch, capsys):
    """--rm deletes staged files after sealing."""
    f1 = tmp_path / "letter.txt"
    f2 = tmp_path / "diary.txt"
    f1.write_text("hello")
    f2.write_text("world")

    d = SimpleNamespace(
        unlock_at="2030-01-01T00:00:00",
        note="",
        out="c.mcap",
        staged=[str(f1), str(f2)],
        root=str(tmp_path),
    )
    monkeypatch.setattr(seal_cmd.draft, "load", lambda: d)
    monkeypatch.setattr(seal_cmd.draft, "save", lambda d: None)
    monkeypatch.setattr(seal_cmd.draft, "missing", lambda d: [])
    monkeypatch.setattr(seal_cmd, "parse_unlock", lambda s: datetime(2030, 1, 1, tzinfo=timezone.utc))
    monkeypatch.setattr(seal_cmd, "ask_password", lambda confirm=False: "pw")
    monkeypatch.setattr(seal_cmd.capsule, "seal", lambda *a, **k: b"BLOB")

    seal_cmd.run(SimpleNamespace(unlock=None, note=None, out=None, force=False, no_password=False, rm=True))
    assert not f1.exists()
    assert not f2.exists()
    assert "deleted 2 staged file(s)" in capsys.readouterr().out


def test_seal_with_rm_skips_non_existent(tmp_path, monkeypatch, capsys):
    """--rm silently skips files already gone (e.g. draft files inside .capsule/)."""
    existing = tmp_path / "letter.txt"
    existing.write_text("hello")
    gone = str(tmp_path / "already_deleted.txt")

    d = SimpleNamespace(
        unlock_at="2030-01-01T00:00:00",
        note="",
        out="c.mcap",
        staged=[str(existing), gone],
        root=str(tmp_path),
    )
    monkeypatch.setattr(seal_cmd.draft, "load", lambda: d)
    monkeypatch.setattr(seal_cmd.draft, "save", lambda d: None)
    monkeypatch.setattr(seal_cmd.draft, "missing", lambda d: [])
    monkeypatch.setattr(seal_cmd, "parse_unlock", lambda s: datetime(2030, 1, 1, tzinfo=timezone.utc))
    monkeypatch.setattr(seal_cmd, "ask_password", lambda confirm=False: "pw")
    monkeypatch.setattr(seal_cmd.capsule, "seal", lambda *a, **k: b"BLOB")

    seal_cmd.run(SimpleNamespace(unlock=None, note=None, out=None, force=False, no_password=False, rm=True))
    assert not existing.exists()
    assert "deleted 1 staged file(s)" in capsys.readouterr().out

def test_seal_with_rm_skips_output_file(tmp_path, monkeypatch, capsys):
    """--rm does not delete the output capsule file if it happens to be staged."""
    staged = tmp_path / "capsule.mcap"
    staged.write_text("content")

    d = SimpleNamespace(
        unlock_at="2030-01-01T00:00:00",
        note="",
        out="capsule.mcap",
        staged=[str(staged)],
        root=str(tmp_path),
    )
    monkeypatch.setattr(seal_cmd.draft, "load", lambda: d)
    monkeypatch.setattr(seal_cmd.draft, "save", lambda d: None)
    monkeypatch.setattr(seal_cmd.draft, "missing", lambda d: [])
    monkeypatch.setattr(seal_cmd, "parse_unlock", lambda s: datetime(2030, 1, 1, tzinfo=timezone.utc))
    monkeypatch.setattr(seal_cmd, "ask_password", lambda confirm=False: "pw")

    # seal will overwrite it; after seal staged path == out path so it should warn
    monkeypatch.setattr(seal_cmd.capsule, "seal", lambda *a, **k: b"NEW")

    seal_cmd.run(SimpleNamespace(unlock=None, note=None, out=None, force=True, no_password=False, rm=True))
    assert staged.exists()  # capsule output survives
    assert staged.read_bytes() == b"NEW"
    err = capsys.readouterr().err
    assert "warning:" in err
    assert "is the capsule output file" in err


def test_seal_without_rm_does_not_delete(tmp_path, monkeypatch, capsys):
    """Without --rm, staged files remain on disk."""
    f = tmp_path / "letter.txt"
    f.write_text("hello")

    d = SimpleNamespace(
        unlock_at="2030-01-01T00:00:00",
        note="",
        out="c.mcap",
        staged=[str(f)],
        root=str(tmp_path),
    )
    monkeypatch.setattr(seal_cmd.draft, "load", lambda: d)
    monkeypatch.setattr(seal_cmd.draft, "save", lambda d: None)
    monkeypatch.setattr(seal_cmd.draft, "missing", lambda d: [])
    monkeypatch.setattr(seal_cmd, "parse_unlock", lambda s: datetime(2030, 1, 1, tzinfo=timezone.utc))
    monkeypatch.setattr(seal_cmd, "ask_password", lambda confirm=False: "pw")
    monkeypatch.setattr(seal_cmd.capsule, "seal", lambda *a, **k: b"BLOB")

    seal_cmd.run(SimpleNamespace(unlock=None, note=None, out=None, force=False, no_password=False, rm=False))
    assert f.exists()


# --- open ---------------------------------------------------------------


def test_open_extracts_and_lists_names(monkeypatch, capsys):
    monkeypatch.setattr(open_cmd, "read_capsule", lambda f: b"blob")
    monkeypatch.setattr(open_cmd.capsule, "inspect", lambda blob: _info(_open=True, cipher="none"))
    monkeypatch.setattr(open_cmd.capsule, "open_capsule", lambda *a, **k: ["a.txt", "b.txt"])

    open_cmd.run(SimpleNamespace(file="c.mcap", dest="out"))
    out = capsys.readouterr().out
    assert "opened into out/" in out
    assert "a.txt" in out and "b.txt" in out


def test_open_locked_capsule_errors(monkeypatch):
    monkeypatch.setattr(open_cmd, "read_capsule", lambda f: b"blob")
    monkeypatch.setattr(open_cmd.capsule, "inspect", lambda blob: _info(_open=False))
    with pytest.raises(SystemExit, match="locked until"):
        open_cmd.run(SimpleNamespace(file="c.mcap", dest="."))


def test_open_prompts_password_for_encrypted(monkeypatch, capsys):
    seen = {}
    monkeypatch.setattr(open_cmd, "read_capsule", lambda f: b"blob")
    monkeypatch.setattr(open_cmd.capsule, "inspect", lambda blob: _info(_open=True, cipher="aes-256-gcm"))
    monkeypatch.setattr(open_cmd, "ask_password", lambda: "pw")
    monkeypatch.setattr(open_cmd.capsule, "open_capsule", lambda blob, pw, dest: seen.setdefault("pw", pw) or [])
    open_cmd.run(SimpleNamespace(file="c.mcap", dest="."))
    assert seen["pw"] == "pw"


# --- info ---------------------------------------------------------------


def test_info_human_readable_locked(monkeypatch, capsys):
    monkeypatch.setattr(info_cmd, "read_capsule", lambda f: b"blob")
    monkeypatch.setattr(info_cmd.capsule, "inspect", lambda blob: _info(_open=False, note="hi"))
    info_cmd.run(SimpleNamespace(file="c.mcap", json=False))
    out = capsys.readouterr().out
    assert "cipher:" in out and "locked" in out and "note:     hi" in out


def test_info_open_status(monkeypatch, capsys):
    monkeypatch.setattr(info_cmd, "read_capsule", lambda f: b"blob")
    monkeypatch.setattr(info_cmd.capsule, "inspect", lambda blob: _info(_open=True, cipher="none"))
    info_cmd.run(SimpleNamespace(file="c.mcap", json=False))
    out = capsys.readouterr().out
    assert "open" in out and "no password" in out


def test_info_json_output(monkeypatch, capsys):
    monkeypatch.setattr(info_cmd, "read_capsule", lambda f: b"blob")
    monkeypatch.setattr(info_cmd.capsule, "inspect", lambda blob: _info(_open=False, note="n"))
    info_cmd.run(SimpleNamespace(file="c.mcap", json=True))
    payload = json.loads(capsys.readouterr().out)
    assert payload["cipher"] == "aes-256-gcm"
    assert payload["open"] is False
    assert payload["note"] == "n"


# --- verify -------------------------------------------------------------


def test_verify_reports_password_checked(monkeypatch, capsys):
    monkeypatch.setattr(verify_cmd, "read_capsule", lambda f: b"blob")
    monkeypatch.setattr(verify_cmd.capsule, "inspect", lambda blob: _info(cipher="aes-256-gcm"))
    monkeypatch.setattr(verify_cmd, "ask_password", lambda: "pw")
    monkeypatch.setattr(verify_cmd.capsule, "verify", lambda blob, pw: True)
    verify_cmd.run(SimpleNamespace(file="c.mcap"))
    assert "password is correct" in capsys.readouterr().out


def test_verify_without_password(monkeypatch, capsys):
    monkeypatch.setattr(verify_cmd, "read_capsule", lambda f: b"blob")
    monkeypatch.setattr(verify_cmd.capsule, "inspect", lambda blob: _info(cipher="none"))
    monkeypatch.setattr(verify_cmd.capsule, "verify", lambda blob, pw: True)
    verify_cmd.run(SimpleNamespace(file="c.mcap"))
    out = capsys.readouterr().out
    assert "capsule is intact" in out and "password" not in out


# --- remind -------------------------------------------------------------


def test_remind_writes_ics(tmp_path, monkeypatch, capsys):
    out = tmp_path / "c.ics"
    monkeypatch.setattr(remind_cmd, "read_capsule", lambda f: b"blob")
    monkeypatch.setattr(remind_cmd.capsule, "inspect", lambda blob: _info(_open=False))
    monkeypatch.setattr(remind_cmd.ics, "build", lambda *a, **k: "ICSDATA")
    remind_cmd.run(SimpleNamespace(file="c.mcap", out=str(out), before=0, force=False))
    assert out.read_text() == "ICSDATA"
    assert "reminder written" in capsys.readouterr().out


def test_remind_notes_already_open_capsule(tmp_path, monkeypatch, capsys):
    out = tmp_path / "c.ics"
    monkeypatch.setattr(remind_cmd, "read_capsule", lambda f: b"blob")
    monkeypatch.setattr(remind_cmd.capsule, "inspect", lambda blob: _info(_open=True))
    monkeypatch.setattr(remind_cmd.ics, "build", lambda *a, **k: "ICS")
    remind_cmd.run(SimpleNamespace(file="c.mcap", out=str(out), before=0, force=False))
    assert "already open" in capsys.readouterr().out


def test_remind_rejects_negative_before(monkeypatch):
    with pytest.raises(SystemExit, match="cannot be negative"):
        remind_cmd.run(SimpleNamespace(file="c.mcap", out=None, before=-1, force=False))


def test_remind_refuses_to_clobber(tmp_path, monkeypatch):
    out = tmp_path / "c.ics"
    out.write_text("old")
    monkeypatch.setattr(remind_cmd, "read_capsule", lambda f: b"blob")
    monkeypatch.setattr(remind_cmd.capsule, "inspect", lambda blob: _info(_open=False))
    with pytest.raises(SystemExit, match="already exists"):
        remind_cmd.run(SimpleNamespace(file="c.mcap", out=str(out), before=0, force=False))
