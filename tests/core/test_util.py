"""spec: shared cli helpers — date parsing, password prompting, formatting."""

from datetime import datetime, timedelta

import pytest

from magicicapsula.commands import _util


def test_parse_absolute_date():
    dt = _util.parse_unlock("2030-01-01")
    assert (dt.year, dt.month, dt.day) == (2030, 1, 1)


def test_parse_absolute_datetime():
    dt = _util.parse_unlock("2030-01-01T08:30")
    assert (dt.hour, dt.minute) == (8, 30)


@pytest.mark.parametrize("unit,attr", [("d", "days"), ("w", "weeks")])
def test_parse_relative_days_and_weeks(unit, attr):
    before = datetime.now().astimezone()
    dt = _util.parse_unlock(f"+3{unit}")
    delta = dt - before
    assert delta >= timedelta(**{attr: 3}) - timedelta(seconds=5)


def test_parse_relative_months_clamps_day():
    # Jan 31 + 1 month must land on a real February day, not overflow.
    base = datetime(2030, 1, 31)
    assert _util._add_months(base, 1).day <= 28


def test_parse_relative_year():
    before = datetime.now().astimezone()
    dt = _util.parse_unlock("+1y")
    assert dt.year >= before.year + 1


def test_parse_bad_date_exits():
    with pytest.raises(SystemExit, match="bad date"):
        _util.parse_unlock("not-a-date")


def test_read_capsule_returns_bytes(tmp_path):
    f = tmp_path / "c.mcap"
    f.write_bytes(b"\x00\x01")
    assert _util.read_capsule(str(f)) == b"\x00\x01"


def test_fmt_remaining_breaks_down_duration():
    assert _util.fmt_remaining(timedelta(days=2, hours=3, minutes=4)) == "2d 3h 4m"


def test_fmt_remaining_floors_negative_to_zero():
    assert _util.fmt_remaining(timedelta(seconds=-10)) == "0d 0h 0m"


def test_ask_password_uses_configured_value(monkeypatch):
    monkeypatch.setattr(_util.config, "get", lambda key: "from-config")
    assert _util.ask_password() == "from-config"


def test_ask_password_prompts_when_unconfigured(monkeypatch):
    monkeypatch.setattr(_util.config, "get", lambda key: None)
    monkeypatch.setattr(_util.getpass, "getpass", lambda *a: "typed")
    assert _util.ask_password() == "typed"


def test_ask_password_rejects_empty(monkeypatch):
    monkeypatch.setattr(_util.config, "get", lambda key: None)
    monkeypatch.setattr(_util.getpass, "getpass", lambda *a: "")
    with pytest.raises(SystemExit, match="empty password"):
        _util.ask_password()


def test_ask_password_confirm_mismatch(monkeypatch):
    monkeypatch.setattr(_util.config, "get", lambda key: None)
    answers = iter(["one", "two"])
    monkeypatch.setattr(_util.getpass, "getpass", lambda *a: next(answers))
    with pytest.raises(SystemExit, match="do not match"):
        _util.ask_password(confirm=True)
