"""spec: the `config` command's list/get/set/unset and `version` output."""

from types import SimpleNamespace

import pytest

from magicicapsula.commands import config as config_cmd
from magicicapsula.commands import version as version_cmd


def test_config_list(isolated_config, capsys):
    config_cmd.run(SimpleNamespace(action="list", key=None, value=None, reveal=False))
    out = capsys.readouterr().out
    assert "config file:" in out
    assert "password = (not set)" in out


def test_config_set_then_get(isolated_config, capsys):
    config_cmd.run(SimpleNamespace(action="set", key="password", value="s3cret", reveal=False))
    config_cmd.run(SimpleNamespace(action="get", key="password", value=None, reveal=True))
    out = capsys.readouterr().out
    assert "set password" in out
    assert "s3cret" in out  # revealed


def test_config_get_masks_by_default(isolated_config, capsys):
    config_cmd.run(SimpleNamespace(action="set", key="password", value="s3cret", reveal=False))
    capsys.readouterr()
    config_cmd.run(SimpleNamespace(action="get", key="password", value=None, reveal=False))
    assert "***" in capsys.readouterr().out


def test_config_unset(isolated_config, capsys):
    config_cmd.run(SimpleNamespace(action="set", key="password", value="x", reveal=False))
    capsys.readouterr()
    config_cmd.run(SimpleNamespace(action="unset", key="password", value=None, reveal=False))
    assert "unset password" in capsys.readouterr().out


def test_config_unset_absent(isolated_config, capsys):
    config_cmd.run(SimpleNamespace(action="unset", key="password", value=None, reveal=False))
    assert "was not set" in capsys.readouterr().out


def test_config_requires_key(isolated_config):
    with pytest.raises(SystemExit, match="needs a key"):
        config_cmd.run(SimpleNamespace(action="get", key=None, value=None, reveal=False))


def test_config_unknown_key(isolated_config):
    with pytest.raises(SystemExit, match="unknown setting"):
        config_cmd.run(SimpleNamespace(action="get", key="ghost", value=None, reveal=False))


def test_config_set_needs_value(isolated_config):
    with pytest.raises(SystemExit, match="needs a value"):
        config_cmd.run(SimpleNamespace(action="set", key="password", value=None, reveal=False))


def test_version_prints_name_and_number(capsys):
    version_cmd.run()
    out = capsys.readouterr().out
    from magicicapsula import __version__

    assert __version__ in out
    assert "magicicapsula" in out


def test_version_action_exits(capsys):
    import argparse

    parser = argparse.ArgumentParser()
    action = version_cmd.VersionPrintAction(option_strings=["--version"], dest="version", nargs=0)
    with pytest.raises(SystemExit):
        action(parser, argparse.Namespace(), None, None)
    assert "magicicapsula" in capsys.readouterr().out
