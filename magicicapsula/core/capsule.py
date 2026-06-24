"""the .mcap capsule format: pack files, seal, inspect, open.

one portable binary file you can store anywhere:

    b"MCAP"            4 bytes   magic
    version           1 byte    container version (the source of truth)
    header length     4 bytes   uint32, big-endian
    header            N bytes   json, utf-8 (dates, kdf params, salt, note)
    ciphertext        rest      encrypted .tar.gz of the contents

the header is plaintext so inspect() can show dates without a password.
the contents, file names included, live only inside the ciphertext.

for password capsules (v2) the cipher is aes-256-gcm and the whole plaintext
preamble -- magic, version, length, and header -- is fed in as additional
authenticated data, so altering the unlock date, note, or framing is caught
on open. v1 used fernet, which has no aad; that path still reads. capsules
sealed without a password carry no authentication of the header (there is no
key), matching the "anyone can open after the date" promise.

forward/backward compatibility
------------------------------
seal() always writes VERSION. the reader accepts any version in
[MIN_READ_VERSION, VERSION], so newer builds keep reading older files; a
version greater than VERSION is rejected with an "upgrade" message instead
of being misparsed. within a version the header schema is additive only:
new fields are optional and read with .get() defaults, existing fields are
never removed or repurposed -- so old readers ignore unknown fields and new
readers tolerate their absence. a genuinely incompatible layout bumps
VERSION and branches on it in _read_info().
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
VERSION = 2  # the container version seal() writes (v2: aes-256-gcm + aad)
MIN_READ_VERSION = 1  # oldest version this build can still read
_HEADER_START = 9  # magic(4) + version(1) + header length(4)


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
        "created_at": _iso(datetime.now(timezone.utc)),
        "unlock_at": _iso(unlock_at),
        "note": note,
    }
    if password:
        salt = os.urandom(16)
        params = crypto.KdfParams()
        header["cipher"] = "aes-256-gcm"
        header["kdf"] = {**params.to_dict(), "salt": base64.b64encode(salt).decode()}
    else:
        header["cipher"] = "none"
    hb = json.dumps(header).encode("utf-8")
    # the preamble is built before the ciphertext so it can be authenticated
    # as aad: the header it carries is then tamper-evident on open.
    preamble = MAGIC + bytes([VERSION]) + struct.pack(">I", len(hb)) + hb
    if password:
        payload = crypto.encrypt_gcm(payload, password, salt, preamble, params)
    return preamble + payload


def _split(blob: bytes):
    """Validate the framing and return (version, header dict, payload bytes)."""
    if len(blob) < _HEADER_START:
        raise InvalidCapsule("file is too small to be a capsule")
    if blob[:4] != MAGIC:
        raise InvalidCapsule("not a magicicapsula capsule (bad magic bytes)")
    version = blob[4]
    if version > VERSION:
        raise InvalidCapsule(
            f"capsule version {version} is newer than this build supports "
            f"(up to {VERSION}); upgrade magicicapsula to open it"
        )
    if version < MIN_READ_VERSION:
        raise InvalidCapsule(f"capsule version {version} is no longer supported")
    (hlen,) = struct.unpack(">I", blob[5:9])
    end = _HEADER_START + hlen
    if end > len(blob):
        raise InvalidCapsule("corrupt header (length runs past end of file)")
    try:
        header = json.loads(blob[_HEADER_START:end])
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise InvalidCapsule("corrupt header") from exc
    # blob[:end] is the authenticated preamble (aad) for v2 capsules.
    return version, header, blob[end:], blob[:end]


def _read_info(version: int, header: dict) -> CapsuleInfo:
    """Turn a header of the given version into CapsuleInfo.

    Every field is read with a default so older capsules missing newer fields
    still load. When VERSION grows past 1, branch on `version` here.
    """
    return CapsuleInfo(
        created_at=_parse_iso(header["created_at"]),
        unlock_at=_parse_iso(header["unlock_at"]),
        cipher=header.get("cipher", "fernet"),
        note=header.get("note", ""),
    )


def inspect(blob: bytes) -> CapsuleInfo:
    version, header, _, _ = _split(blob)
    try:
        return _read_info(version, header)
    except KeyError as exc:
        raise InvalidCapsule(f"corrupt header (missing field {exc})") from exc


def _payload(blob: bytes, password) -> bytes:
    _version, header, token, aad = _split(blob)
    cipher = header.get("cipher", "fernet")
    if cipher == "none":
        return token
    if cipher not in ("fernet", "aes-256-gcm"):
        raise InvalidCapsule(f"unknown cipher: {cipher}")
    if not password:
        raise WrongPasswordOrCorrupt("this capsule needs a password")
    kdf = header["kdf"]
    salt = base64.b64decode(kdf["salt"])
    params = crypto.KdfParams.from_dict(kdf)
    if cipher == "fernet":  # v1
        return crypto.decrypt(token, password, salt, params)
    return crypto.decrypt_gcm(token, password, salt, aad, params)


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
