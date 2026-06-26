"""spec: color is opt-in to a real terminal and stripped otherwise.

NO_COLOR / a non-tty / TERM=dumb must yield plain text, so piped output stays
clean. the logo loads from package assets either way.
"""

from magicicapsula.commands import _style


def test_no_color_when_not_a_tty(monkeypatch):
    # capsys/pytest already make stdout a non-tty, but be explicit.
    monkeypatch.setattr("sys.stdout.isatty", lambda: False, raising=False)
    assert _style.red("x") == "x"
    assert not _style.enabled()


def test_color_codes_applied_when_enabled(monkeypatch):
    monkeypatch.setattr(_style, "enabled", lambda: True)
    assert _style.green("hi") == "\x1b[32mhi\x1b[0m"
    assert _style.bold("hi") == "\x1b[1mhi\x1b[0m"


def test_no_color_env_disables(monkeypatch):
    monkeypatch.setattr("sys.stdout.isatty", lambda: True, raising=False)
    monkeypatch.setenv("NO_COLOR", "1")
    assert not _style.enabled()


def test_logo_loads_and_is_plain_without_color():
    logo = _style.logo()
    assert isinstance(logo, str) and logo.strip()
    assert "\x1b[" not in logo  # ansi stripped for non-tty
