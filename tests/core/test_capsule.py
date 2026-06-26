"""spec: the .mcap container — seal, inspect, verify, open.

the header is plaintext (inspect needs no password); the contents are inside
the ciphertext. for v2 the header is bound as aad, so tampering is caught.
the reader accepts versions in [MIN_READ_VERSION, VERSION] and rejects the
rest with InvalidCapsule instead of misparsing.
"""

import base64
import io
import json
import struct
import tarfile
from datetime import datetime, timedelta, timezone

import pytest

from magicicapsula.core import capsule, crypto
from magicicapsula.core.errors import (
    CapsuleLocked,
    InvalidCapsule,
    WrongPasswordOrCorrupt,
)


def _now():
    return datetime.now(timezone.utc)


# --- helpers that build capsule bytes from the *documented wire format* only,
# --- so these tests bind to the format contract, not to capsule's privates.


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _frame(version, header: dict, payload: bytes) -> bytes:
    hb = json.dumps(header).encode()
    return capsule.MAGIC + bytes([version]) + struct.pack(">I", len(hb)) + hb + payload


def _targz(name, text) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        data = text.encode()
        ti = tarfile.TarInfo(name)
        ti.size = len(data)
        tar.addfile(ti, io.BytesIO(data))
    return buf.getvalue()


def test_seal_open_roundtrip_with_password(make_capsule, tmp_path):
    blob = make_capsule(note="hi")
    dest = tmp_path / "out"
    names = capsule.open_capsule(blob, "hunter2", str(dest))
    assert sorted(names) == ["letter.txt", "note.txt"]
    assert (dest / "letter.txt").read_text() == "dear future me\n"


def test_seal_without_password_uses_cipher_none(make_capsule, tmp_path):
    blob = make_capsule(password=None)
    assert capsule.inspect(blob).cipher == "none"
    # no password needed to open
    names = capsule.open_capsule(blob, None, str(tmp_path / "o"))
    assert "letter.txt" in names


def test_inspect_reads_metadata_without_password(make_capsule, future):
    blob = make_capsule(unlock_at=future, note="later")
    info = capsule.inspect(blob)
    assert info.cipher == "aes-256-gcm"
    assert info.note == "later"
    assert not info.is_open()
    assert info.remaining() > timedelta(0)


def test_open_locked_capsule_raises(make_capsule, future, tmp_path):
    blob = make_capsule(unlock_at=future)
    with pytest.raises(CapsuleLocked):
        capsule.open_capsule(blob, "hunter2", str(tmp_path / "o"))


def test_allow_locked_bypasses_the_date(make_capsule, future, tmp_path):
    blob = make_capsule(unlock_at=future)
    names = capsule.open_capsule(blob, "hunter2", str(tmp_path / "o"), allow_locked=True)
    assert "letter.txt" in names


def test_wrong_password_raises(make_capsule, tmp_path):
    blob = make_capsule()
    with pytest.raises(WrongPasswordOrCorrupt):
        capsule.open_capsule(blob, "nope", str(tmp_path / "o"))


def test_password_capsule_needs_a_password(make_capsule, tmp_path):
    blob = make_capsule()
    with pytest.raises(WrongPasswordOrCorrupt, match="needs a password"):
        capsule.open_capsule(blob, None, str(tmp_path / "o"))


def test_tampered_header_is_detected(make_capsule):
    blob = bytearray(make_capsule(note="original"))
    i = blob.find(b"original")
    blob[i : i + len(b"original")] = b"TAMPERED"  # same length, valid json
    with pytest.raises(WrongPasswordOrCorrupt):
        capsule.open_capsule(bytes(blob), "hunter2", "/tmp/should-not-happen", allow_locked=True)


def test_verify_returns_true_then_rejects_bad_password(make_capsule):
    blob = make_capsule()
    assert capsule.verify(blob, "hunter2") is True
    with pytest.raises(WrongPasswordOrCorrupt):
        capsule.verify(blob, "wrong")


def test_bad_magic_rejected():
    with pytest.raises(InvalidCapsule, match="bad magic"):
        capsule.inspect(b"XXXX" + b"\x00" * 20)


def test_too_small_rejected():
    with pytest.raises(InvalidCapsule, match="too small"):
        capsule.inspect(b"MC")


def test_future_version_rejected_with_upgrade_hint():
    with pytest.raises(InvalidCapsule, match="upgrade"):
        capsule.inspect(_frame(capsule.VERSION + 1, {}, b""))


def test_header_length_past_end_rejected():
    body = capsule.MAGIC + bytes([capsule.VERSION]) + struct.pack(">I", 9999)
    with pytest.raises(InvalidCapsule, match="runs past end"):
        capsule.inspect(body)


def test_corrupt_header_json_rejected():
    bad = b"{not json"
    body = capsule.MAGIC + bytes([capsule.VERSION]) + struct.pack(">I", len(bad)) + bad
    with pytest.raises(InvalidCapsule, match="corrupt header"):
        capsule.inspect(body)


def test_missing_required_field_rejected():
    body = _frame(capsule.VERSION, {"unlock_at": _iso(_now())}, b"")  # no created_at
    with pytest.raises(InvalidCapsule, match="missing field"):
        capsule.inspect(body)


def test_seal_rejects_missing_input_file(tmp_path, past):
    with pytest.raises(FileNotFoundError):
        capsule.seal([str(tmp_path / "ghost.txt")], "pw", past)


def test_v1_fernet_capsule_still_opens(tmp_path, past):
    """A hand-built v1 (fernet) capsule must still read, for backward compat.

    Built from the documented wire format + the public crypto API only — the
    .mcap layout is itself a contract ("old files still open"), so binding to
    it here is intentional; binding to capsule's private helpers would not be.
    """
    salt = bytes(range(16))
    params = crypto.KdfParams(n=2**4, r=1, p=1)
    header = {
        "created_at": _iso(_now()),
        "unlock_at": _iso(past),
        "note": "",
        "cipher": "fernet",
        "kdf": {**params.to_dict(), "salt": base64.b64encode(salt).decode()},
    }
    token = crypto.encrypt(_targz("old.txt", "legacy"), "pw", salt, params)
    blob = _frame(1, header, token)

    assert capsule.inspect(blob).cipher == "fernet"
    assert capsule.open_capsule(blob, "pw", str(tmp_path / "o")) == ["old.txt"]


def test_unknown_cipher_rejected(tmp_path, past):
    header = {"created_at": _iso(_now()), "unlock_at": _iso(past), "cipher": "rot13"}
    with pytest.raises(InvalidCapsule, match="unknown cipher"):
        capsule.open_capsule(_frame(capsule.VERSION, header, b"junk"), "pw", str(tmp_path / "o"), allow_locked=True)


def test_list_names_on_corrupt_payload_raises():
    with pytest.raises(WrongPasswordOrCorrupt):
        capsule.list_names(b"not a tar")
