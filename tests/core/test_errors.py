"""spec: the error hierarchy the cli relies on to print short messages."""

from datetime import datetime, timezone

from magicicapsula.core.errors import (
    CapsuleError,
    CapsuleLocked,
    InvalidCapsule,
    NoDraft,
    WrongPasswordOrCorrupt,
)


def test_all_errors_are_capsule_errors():
    for cls in (InvalidCapsule, WrongPasswordOrCorrupt, NoDraft, CapsuleLocked):
        assert issubclass(cls, CapsuleError)


def test_capsule_locked_carries_unlock_date_and_message():
    when = datetime(2030, 1, 1, tzinfo=timezone.utc)
    err = CapsuleLocked(when)
    assert err.unlock_at == when
    assert when.isoformat() in str(err)
