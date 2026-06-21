"""the .mcap capsule format: pack files, seal, inspect, open.

one portable binary file you can store anywhere:

    b"MCAP"            4 bytes   magic
    version           1 byte
    header length     4 bytes   uint32, big-endian
    header            N bytes   json, utf-8 (dates, kdf params, salt, note)
    ciphertext        rest      fernet token of a .tar.gz of the contents

the header is plaintext so inspect() can show dates without a password.
the contents, file names included, live only inside the ciphertext.
"""

import base64
import io
import json
import os
import struct
import tarfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from . import crypto
from .errors import CapsuleLocked, InvalidCapsule, WrongPasswordOrCorrupt

MAGIC = b"MCAP"
VERSION = 1


@dataclass
class CapsuleInfo:
    """Non-secret metadata readable without the password."""

    created_at: datetime
    unlock_at: datetime
    cipher: str
    note: str

    def is_open(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        return now >= self.unlock_at

    def remaining(self, now: datetime | None = None) -> timedelta:
        now = now or datetime.now(timezone.utc)
        return max(self.unlock_at - now, timedelta(0))


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _parse_iso(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _pack(paths) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path in paths:
            path = os.path.normpath(path)
            if not os.path.exists(path):
                raise FileNotFoundError(path)
            tar.add(path, arcname=os.path.basename(path))
    return buf.getvalue()


def _unpack(blob: bytes, dest: str) -> list[str]:
    os.makedirs(dest, exist_ok=True)
    try:
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
            names = tar.getnames()
            tar.extractall(dest, filter="data")  # filter blocks path traversal
    except tarfile.TarError as exc:
        raise WrongPasswordOrCorrupt("the capsule is corrupted") from exc
    return names


def list_names(blob: bytes) -> list[str]:
    try:
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
            return tar.getnames()
    except tarfile.TarError as exc:
        raise WrongPasswordOrCorrupt("the capsule is corrupted") from exc


def seal(paths, password, unlock_at: datetime, note: str = "") -> bytes:
    if unlock_at.tzinfo is None:
        unlock_at = unlock_at.replace(tzinfo=timezone.utc)
    payload = _pack(paths)
    header = {
        "v": VERSION,
        "created_at": _iso(datetime.now(timezone.utc)),
        "unlock_at": _iso(unlock_at),
        "note": note,
    }
    if password:
        salt = os.urandom(16)
        params = crypto.KdfParams()
        payload = crypto.encrypt(payload, password, salt, params)
        header["cipher"] = "fernet"
        header["kdf"] = {**params.to_dict(), "salt": base64.b64encode(salt).decode()}
    else:
        header["cipher"] = "none"
    hb = json.dumps(header).encode("utf-8")
    return MAGIC + bytes([VERSION]) + struct.pack(">I", len(hb)) + hb + payload


def _split(blob: bytes):
    if blob[:4] != MAGIC:
        raise InvalidCapsule("not a magicicapsula capsule (bad magic bytes)")
    version = blob[4]
    if version != VERSION:
        raise InvalidCapsule(f"unsupported capsule version: {version}")
    (hlen,) = struct.unpack(">I", blob[5:9])
    try:
        header = json.loads(blob[9:9 + hlen])
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise InvalidCapsule("corrupt header") from exc
    return header, blob[9 + hlen:]


def inspect(blob: bytes) -> CapsuleInfo:
    header, _ = _split(blob)
    return CapsuleInfo(
        created_at=_parse_iso(header["created_at"]),
        unlock_at=_parse_iso(header["unlock_at"]),
        cipher=header.get("cipher", "fernet"),
        note=header.get("note", ""),
    )


def _payload(blob: bytes, password) -> bytes:
    header, token = _split(blob)
    cipher = header.get("cipher", "fernet")
    if cipher == "none":
        return token
    if cipher != "fernet":
        raise InvalidCapsule(f"unknown cipher: {cipher}")
    if not password:
        raise WrongPasswordOrCorrupt("this capsule needs a password")
    kdf = header["kdf"]
    salt = base64.b64decode(kdf["salt"])
    return crypto.decrypt(token, password, salt, crypto.KdfParams.from_dict(kdf))


def verify(blob: bytes, password) -> bool:
    """Unpack the payload in memory without extracting. Raises on a bad password or corruption."""
    list_names(_payload(blob, password))  # opening the tar catches a corrupt payload too
    return True


def open_capsule(
    blob: bytes,
    password,
    dest: str,
    *,
    now: datetime | None = None,
    allow_locked: bool = False,
) -> list[str]:
    info = inspect(blob)
    if not allow_locked and not info.is_open(now):
        raise CapsuleLocked(info.unlock_at)
    return _unpack(_payload(blob, password), dest)
