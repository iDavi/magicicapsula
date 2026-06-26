"""spec: the .capsule/ staging area — init, find, add, stage_text, remove.

staged entries are absolute paths to files on disk; contents are read at seal
time, not copied on add. the root is found by walking up from the cwd.
"""

import os

import pytest

from magicicapsula.core import draft
from magicicapsula.core.errors import NoDraft


def test_init_creates_draft_dir(in_tmp):
    d = draft.init()
    assert os.path.isdir(d.dir)
    assert os.path.exists(d.config_path)


def test_init_twice_raises(in_tmp):
    draft.init()
    with pytest.raises(FileExistsError):
        draft.init()


def test_find_root_walks_up_from_subdir(in_tmp):
    draft.init()
    sub = in_tmp / "a" / "b"
    sub.mkdir(parents=True)
    assert draft.find_root(str(sub)) == str(in_tmp)


def test_find_root_without_draft_raises(in_tmp):
    with pytest.raises(NoDraft):
        draft.find_root(str(in_tmp))


def test_load_roundtrips_saved_fields(in_tmp):
    d = draft.init()
    d.unlock_at = "2030-01-01T00:00:00"
    d.note = "hello"
    d.out = "x.mcap"
    draft.save(d)
    loaded = draft.load(str(in_tmp))
    assert (loaded.unlock_at, loaded.note, loaded.out) == ("2030-01-01T00:00:00", "hello", "x.mcap")


def test_add_stages_absolute_paths_and_dedupes(in_tmp):
    d = draft.init()
    f = in_tmp / "f.txt"
    f.write_text("x")
    added = draft.add(d, ["f.txt"])
    assert added == [str(f)]
    # adding the same path again stages nothing new
    assert draft.add(d, ["f.txt"]) == []
    assert d.staged == [str(f)]


def test_add_missing_file_raises(in_tmp):
    d = draft.init()
    with pytest.raises(FileNotFoundError):
        draft.add(d, ["ghost.txt"])


def test_stage_text_writes_and_stages_a_file(in_tmp):
    d = draft.init()
    path = draft.stage_text(d, "dear future me", "letter.txt")
    assert os.path.basename(path) == "letter.txt"
    assert open(path, encoding="utf-8").read() == "dear future me"
    assert path in d.staged


def test_stage_text_accepts_bytes_and_avoids_clobber(in_tmp):
    d = draft.init()
    first = draft.stage_text(d, b"one", "n.txt")
    second = draft.stage_text(d, b"two", "n.txt")
    assert first != second  # _unique picked a fresh name
    assert open(second, "rb").read() == b"two"


def test_stage_text_falls_back_to_default_name(in_tmp):
    d = draft.init()
    path = draft.stage_text(d, "x", name="")
    assert os.path.basename(path) == "note.txt"


def test_remove_unstages_only_matching_paths(in_tmp):
    d = draft.init()
    (in_tmp / "a").write_text("a")
    (in_tmp / "b").write_text("b")
    draft.add(d, ["a", "b"])
    removed = draft.remove(d, ["a", "missing"])
    assert removed == [os.path.abspath("a")]
    assert d.staged == [os.path.abspath("b")]


def test_missing_lists_vanished_files(in_tmp):
    d = draft.init()
    f = in_tmp / "gone.txt"
    f.write_text("x")
    draft.add(d, ["gone.txt"])
    os.remove(f)
    assert draft.missing(d) == [str(f)]
