"""spec: the argparse wiring and top-level error handling in cli.main.

main() catches CapsuleError and FileNotFoundError and turns them into a short
`error: ...` exit, so a stack trace never reaches the user.
"""

import pytest

from magicicapsula import cli
from magicicapsula.core.errors import CapsuleError


def test_parser_discovers_subcommands():
    parser = cli.build_parser()
    args = parser.parse_args(["version"])
    assert hasattr(args, "func")


def test_no_command_errors_out(monkeypatch):
    monkeypatch.setattr("sys.argv", ["magicicapsula"])
    with pytest.raises(SystemExit):
        cli.main()


def test_version_runs(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["magicicapsula", "version"])
    cli.main()
    assert "magicicapsula" in capsys.readouterr().out


def test_capsule_error_is_reported_cleanly(monkeypatch):
    parser = cli.build_parser()
    args = parser.parse_args(["version"])

    def boom(_):
        raise CapsuleError("kaboom")

    args.func = boom
    monkeypatch.setattr(cli, "build_parser", lambda: _FixedParser(args))
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert "kaboom" in str(exc.value)


def test_missing_file_is_reported_cleanly(monkeypatch):
    parser = cli.build_parser()
    args = parser.parse_args(["version"])

    def boom(_):
        raise FileNotFoundError("capsule.mcap")

    args.func = boom
    monkeypatch.setattr(cli, "build_parser", lambda: _FixedParser(args))
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert "no such file" in str(exc.value)


class _FixedParser:
    """A stand-in parser whose parse_args ignores argv and returns fixed args."""

    def __init__(self, args):
        self._args = args

    def parse_args(self):
        return self._args
