"""spec: init/add/rm/status print the right thing, with draft core mocked."""

from types import SimpleNamespace

import pytest

from magicicapsula.commands import add as add_cmd
from magicicapsula.commands import init as init_cmd
from magicicapsula.commands import rm as rm_cmd
from magicicapsula.commands import status as status_cmd


def _draft(**kw):
    base = dict(unlock_at=None, note="", out="capsule.mcap", staged=[], root="/r")
    base.update(kw)
    d = SimpleNamespace(**base)
    d.dir = "/r/.capsule"
    return d


# --- init ---------------------------------------------------------------


def test_init_creates_and_reports(monkeypatch, capsys):
    d = _draft()
    monkeypatch.setattr(init_cmd.draft, "init", lambda: d)
    monkeypatch.setattr(init_cmd.draft, "save", lambda d: None)
    init_cmd.run(SimpleNamespace(unlock=None, note="hi", out="x.mcap"))
    out = capsys.readouterr().out
    assert "new capsule draft" in out
    assert d.note == "hi" and d.out == "x.mcap"


def test_init_resolves_unlock(monkeypatch, capsys):
    from datetime import datetime, timezone

    d = _draft()
    monkeypatch.setattr(init_cmd.draft, "init", lambda: d)
    monkeypatch.setattr(init_cmd.draft, "save", lambda d: None)
    monkeypatch.setattr(init_cmd, "parse_unlock", lambda s: datetime(2030, 1, 1, tzinfo=timezone.utc))
    init_cmd.run(SimpleNamespace(unlock="+1y", note="", out="c.mcap"))
    assert d.unlock_at.startswith("2030-01-01")


def test_init_existing_draft_errors(monkeypatch):
    def boom():
        raise FileExistsError("/r/.capsule")

    monkeypatch.setattr(init_cmd.draft, "init", boom)
    with pytest.raises(SystemExit, match="already exists"):
        init_cmd.run(SimpleNamespace(unlock=None, note="", out="c.mcap"))


# --- add ----------------------------------------------------------------


def test_add_nothing_errors(monkeypatch):
    with pytest.raises(SystemExit, match="nothing to add"):
        add_cmd.run(SimpleNamespace(paths=[], text=None, name="note.txt"))


def test_add_files_reports_total(monkeypatch, capsys):
    d = _draft(staged=["/r/a", "/r/b"])
    monkeypatch.setattr(add_cmd.draft, "load", lambda: d)
    monkeypatch.setattr(add_cmd.draft, "add", lambda d, files: ["/r/a", "/r/b"])
    add_cmd.run(SimpleNamespace(paths=["a", "b"], text=None, name="note.txt"))
    out = capsys.readouterr().out
    assert "staged /r/a" in out
    assert "2 item(s) staged in total" in out


def test_add_text_stages_inline(monkeypatch, capsys):
    d = _draft(staged=["/r/.capsule/files/note.txt"])
    monkeypatch.setattr(add_cmd.draft, "load", lambda: d)
    monkeypatch.setattr(add_cmd.draft, "stage_text", lambda d, content, name: "/r/.capsule/files/note.txt")
    add_cmd.run(SimpleNamespace(paths=[], text="dear future me", name="note.txt"))
    assert "staged /r/.capsule/files/note.txt" in capsys.readouterr().out


def test_add_stdin(monkeypatch, capsys):
    import io

    d = _draft(staged=["/r/.capsule/files/in.txt"])
    monkeypatch.setattr(add_cmd.draft, "load", lambda: d)
    monkeypatch.setattr(add_cmd.draft, "stage_text", lambda d, content, name: "/r/.capsule/files/in.txt")
    monkeypatch.setattr("sys.stdin", SimpleNamespace(buffer=io.BytesIO(b"piped")))
    add_cmd.run(SimpleNamespace(paths=["-"], text=None, name="in.txt"))
    assert "staged" in capsys.readouterr().out


def test_add_nothing_new(monkeypatch, capsys):
    d = _draft(staged=["/r/a"])
    monkeypatch.setattr(add_cmd.draft, "load", lambda: d)
    monkeypatch.setattr(add_cmd.draft, "add", lambda d, files: [])
    add_cmd.run(SimpleNamespace(paths=["a"], text=None, name="note.txt"))
    assert "nothing new to stage" in capsys.readouterr().out


# --- rm -----------------------------------------------------------------


def test_rm_reports_unstaged(monkeypatch, capsys):
    monkeypatch.setattr(rm_cmd.draft, "load", lambda: _draft())
    monkeypatch.setattr(rm_cmd.draft, "remove", lambda d, paths: ["/r/a"])
    rm_cmd.run(SimpleNamespace(paths=["a"]))
    assert "unstaged /r/a" in capsys.readouterr().out


def test_rm_nothing_matched(monkeypatch, capsys):
    monkeypatch.setattr(rm_cmd.draft, "load", lambda: _draft())
    monkeypatch.setattr(rm_cmd.draft, "remove", lambda d, paths: [])
    rm_cmd.run(SimpleNamespace(paths=["a"]))
    assert "none of those were staged" in capsys.readouterr().out


# --- status -------------------------------------------------------------


def test_status_empty_draft(monkeypatch, capsys):
    monkeypatch.setattr(status_cmd.draft, "load", lambda: _draft())
    status_cmd.run(SimpleNamespace())
    out = capsys.readouterr().out
    assert "not set" in out and "nothing staged" in out


def test_status_with_staged_files(tmp_path, monkeypatch, capsys):
    f = tmp_path / "a.txt"
    f.write_text("hello")
    d = _draft(unlock_at="2030-01-01T00:00:00", note="hi", staged=[str(f)])
    monkeypatch.setattr(status_cmd.draft, "load", lambda: d)
    monkeypatch.setattr(status_cmd.draft, "missing", lambda d: [])
    status_cmd.run(SimpleNamespace())
    out = capsys.readouterr().out
    assert "note:    hi" in out
    assert "1 item(s) staged" in out
    assert str(f) in out


def test_status_warns_about_missing_files(monkeypatch, capsys):
    d = _draft(unlock_at="2030-01-01T00:00:00", staged=["/r/gone"])
    monkeypatch.setattr(status_cmd.draft, "load", lambda: d)
    monkeypatch.setattr(status_cmd.draft, "missing", lambda d: ["/r/gone"])
    status_cmd.run(SimpleNamespace())
    out = capsys.readouterr().out
    assert "(missing)" in out and "warning" in out


def test_fmt_size_units():
    assert status_cmd._fmt_size(0) == "0 B"
    assert status_cmd._fmt_size(2048) == "2.0 KB"
    assert status_cmd._fmt_size(5 * 1024**4) == "5.0 TB"
    assert status_cmd._fmt_size(3 * 1024**5) == "3.0 PB"  # beyond TB falls back to PB
