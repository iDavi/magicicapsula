"""password-based authenticated encryption for capsule payloads.

kept separate from the capsule format and the cli, so swapping the
cipher later only touches this file. wraps the cryptography package
instead of hand-rolling anything.

password -> scrypt -> 32-byte key -> base64 -> fernet key.
fernet is aes-128-cbc + hmac-sha256, so it detects tampering.
"""

import base64
import hashlib
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken

from .errors import WrongPasswordOrCorrupt

# scrypt cost parameters. Memory cost ~= 128 * r * n bytes (~32 MB here).
SCRYPT_N = 2 ** 15
SCRYPT_R = 8
SCRYPT_P = 1
KEY_LEN = 32
_MAXMEM = 128 * SCRYPT_R * SCRYPT_N * 2  # headroom for hashlib.scrypt


@dataclass(frozen=True)
class KdfParams:
    """Key-derivation parameters, stored (minus the salt) in the header."""

    algo: str = "scrypt"
    n: int = SCRYPT_N
    r: int = SCRYPT_R
    p: int = SCRYPT_P

    def to_dict(self) -> dict:
        return {"algo": self.algo, "n": self.n, "r": self.r, "p": self.p}

    @classmethod
    def from_dict(cls, d: dict) -> "KdfParams":
        return cls(d.get("algo", "scrypt"), d["n"], d["r"], d["p"])


def derive_key(password: str, salt: bytes, params: KdfParams = KdfParams()) -> bytes:
    if params.algo != "scrypt":
        raise ValueError(f"unsupported KDF: {params.algo}")
    raw = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=params.n,
        r=params.r,
        p=params.p,
        dklen=KEY_LEN,
        maxmem=_MAXMEM,
    )
    return base64.urlsafe_b64encode(raw)


def encrypt(data: bytes, password: str, salt: bytes, params: KdfParams = KdfParams()) -> bytes:
    return Fernet(derive_key(password, salt, params)).encrypt(data)


def decrypt(token: bytes, password: str, salt: bytes, params: KdfParams = KdfParams()) -> bytes:
    try:
        return Fernet(derive_key(password, salt, params)).decrypt(token)
    except InvalidToken as exc:
        raise WrongPasswordOrCorrupt(
            "wrong password, or the capsule has been altered/corrupted"
        ) from exc
