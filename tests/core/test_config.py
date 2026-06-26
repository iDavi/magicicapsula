"""spec: settings resolve default < config file < environment variable.

every test runs against an isolated XDG_CONFIG_HOME, so the real user config
is never read or written.
"""

import pytest

from magicicapsula.core import config


def test_known_keys(isolated_config):
    assert config.keys() == ["password"]
    assert config.is_known("password")
    assert not config.is_known("nope")


def test_unset_key_resolves_to_default(isolated_config):
    value, source = config.resolve("password")
    assert value is None
    assert source == "default"


def test_file_value_takes_over_default(isolated_config):
    config.set_value("password", "fromfile")
    assert config.resolve("password") == ("fromfile", "file")
    assert config.get("password") == "fromfile"


def test_env_overrides_file(isolated_config, monkeypatch):
    config.set_value("password", "fromfile")
    monkeypatch.setenv("MAGICICAPSULA_PASSWORD", "fromenv")
    assert config.resolve("password") == ("fromenv", "env")


def test_unset_reports_presence(isolated_config):
    assert config.unset("password") is False  # nothing to remove yet
    config.set_value("password", "x")
    assert config.unset("password") is True
    assert config.get("password") is None


def test_set_unknown_key_raises(isolated_config):
    with pytest.raises(KeyError):
        config.set_value("ghost", "x")


def test_unset_unknown_key_raises(isolated_config):
    with pytest.raises(KeyError):
        config.unset("ghost")


def test_display_masks_secret_unless_revealed(isolated_config):
    assert config.display("password", "s3cret") == "***"
    assert config.display("password", "s3cret", reveal=True) == "s3cret"
    assert config.display("password", None) == "(not set)"


def test_corrupt_config_file_is_ignored(isolated_config):
    path = config.config_path()
    path_dir = path.rsplit("/", 1)[0]
    import os

    os.makedirs(path_dir, exist_ok=True)
    with open(path, "w") as fh:
        fh.write("{ not json")
    # a broken file resolves as if empty rather than blowing up
    assert config.resolve("password") == (None, "default")
