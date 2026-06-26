"""password-based authenticated encryption for capsule payloads.

kept separate from the capsule format and the cli, so swapping the cipher
later only touches this file. wraps the cryptography package instead of
hand-rolling anything.

password -> scrypt -> 32-byte key.

v2 capsules use aes-256-gcm with the plaintext header bound in as additional
authenticated data (aad), so altering the header (unlock date, note, kdf
params) or the ciphertext is detected on open. v1 capsules used fernet
(aes-128-cbc + hmac-sha256, no aad); that path stays here so old capsules
still open.
"""

import base64
import hashlib
import os
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .errors import WrongPasswordOrCorrupt

# scrypt cost parameters. Memory cost ~= 128 * r * n bytes (~32 MB here).
SCRYPT_N = 2**15
SCRYPT_R = 8
SCRYPT_P = 1
KEY_LEN = 32
GCM_NONCE_LEN = 12  # 96-bit nonce, the size aes-gcm is defined for
_MAXMEM = 128 * SCRYPT_R * SCRYPT_N * 2  # headroom for hashlib.scrypt

_TAMPERED = "wrong password, or the capsule has been altered/corrupted"


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


def _scrypt(password: str, salt: bytes, params: KdfParams) -> bytes:
    """The raw 32-byte key. Fernet wants it base64-wrapped, aes-gcm wants it raw."""
    if params.algo != "scrypt":
        raise ValueError(f"unsupported KDF: {params.algo}")
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=params.n,
        r=params.r,
        p=params.p,
        dklen=KEY_LEN,
        maxmem=_MAXMEM,
    )


# --- v2: aes-256-gcm with authenticated header -----------------------------


def encrypt_gcm(data: bytes, password: str, salt: bytes, aad: bytes, params: KdfParams = KdfParams()) -> bytes:
    """Encrypt, authenticating `aad` (the header) alongside. Output is nonce + ciphertext."""
    nonce = os.urandom(GCM_NONCE_LEN)
    return nonce + AESGCM(_scrypt(password, salt, params)).encrypt(nonce, data, aad)


def decrypt_gcm(token: bytes, password: str, salt: bytes, aad: bytes, params: KdfParams = KdfParams()) -> bytes:
    """Decrypt and verify both the ciphertext and `aad`. Raises if either was altered."""
    nonce, ct = token[:GCM_NONCE_LEN], token[GCM_NONCE_LEN:]
    try:
        return AESGCM(_scrypt(password, salt, params)).decrypt(nonce, ct, aad)
    except InvalidTag as exc:
        raise WrongPasswordOrCorrupt(_TAMPERED) from exc


# --- v1: fernet, kept so old capsules still open ---------------------------


def derive_key(password: str, salt: bytes, params: KdfParams = KdfParams()) -> bytes:
    return base64.urlsafe_b64encode(_scrypt(password, salt, params))


def encrypt(data: bytes, password: str, salt: bytes, params: KdfParams = KdfParams()) -> bytes:
    return Fernet(derive_key(password, salt, params)).encrypt(data)


def decrypt(token: bytes, password: str, salt: bytes, params: KdfParams = KdfParams()) -> bytes:
    try:
        return Fernet(derive_key(password, salt, params)).decrypt(token)
    except InvalidToken as exc:
        raise WrongPasswordOrCorrupt(_TAMPERED) from exc
