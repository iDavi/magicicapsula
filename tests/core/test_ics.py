"""spec: rfc 5545 .ics generation — utc stamps, escaping, line folding, uid.

these assert only on the public contract: the text `build()` returns. escaping
and folding are observable there, so there's no need to reach for the private
`_escape`/`_fold` helpers — that would freeze implementation details the
public output already pins down.
"""

from datetime import datetime, timezone

from magicicapsula.core import ics


def _dt():
    return datetime(2030, 1, 1, 8, 0, tzinfo=timezone.utc)


def test_build_has_calendar_envelope_and_event():
    text = ics.build("capsule.mcap", _dt(), now=_dt())
    assert text.startswith("BEGIN:VCALENDAR\r\n")
    assert text.endswith("END:VCALENDAR\r\n")
    assert "BEGIN:VEVENT" in text
    assert "DTSTART:20300101T080000Z" in text
    assert "DTEND:20300101T083000Z" in text  # +30 min


def test_uid_is_stable_for_same_inputs():
    a = ics.build("c.mcap", _dt(), now=_dt())
    b = ics.build("c.mcap", _dt(), now=_dt())
    assert a == b


def test_uid_changes_with_name():
    assert _uid_line(ics.build("a.mcap", _dt(), now=_dt())) != _uid_line(ics.build("b.mcap", _dt(), now=_dt()))


def test_default_trigger_fires_on_the_day():
    assert "TRIGGER:PT0S" in ics.build("c.mcap", _dt(), now=_dt())


def test_before_days_sets_negative_trigger():
    assert "TRIGGER:-P3D" in ics.build("c.mcap", _dt(), before_days=3, now=_dt())


def test_note_overrides_description():
    text = ics.build("c.mcap", _dt(), note="open me gently", now=_dt())
    assert "DESCRIPTION:open me gently" in text


def test_special_characters_are_escaped_in_output():
    text = ics.build("c.mcap", _dt(), note="a;b,c\\d", now=_dt())
    assert r"DESCRIPTION:a\;b\,c\\d" in text


def test_long_value_is_folded_within_the_octet_limit():
    text = ics.build("c.mcap", _dt(), note="z" * 200, now=_dt())
    assert "\r\n " in text  # a continuation line was produced
    for i, physical in enumerate(text.split("\r\n")):
        # first line caps at 75 octets; folded lines add one for the leading space
        assert len(physical.encode("utf-8")) <= (75 if i == 0 else 76)


def test_folding_never_corrupts_a_multibyte_char():
    text = ics.build("c.mcap", _dt(), note="é" * 80, now=_dt())  # 2 octets each
    unfolded = text.replace("\r\n ", "")
    assert "DESCRIPTION:" + "é" * 80 in unfolded


def _uid_line(text):
    return next(line for line in text.split("\r\n") if line.startswith("UID:"))
