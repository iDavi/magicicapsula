"""spec: password -> scrypt key -> authenticated encryption.

v2 is aes-256-gcm binding the header as aad; v1 is fernet with no aad. both
must round-trip, and both must reject a wrong password or altered bytes with
WrongPasswordOrCorrupt rather than leaking a raw crypto exception.
"""

import os

import pytest

from magicicapsula.core import crypto
from magicicapsula.core.errors import WrongPasswordOrCorrupt

# tiny scrypt cost so the suite stays fast; correctness is independent of n.
FAST = crypto.KdfParams(n=2**4, r=1, p=1)


def test_kdf_params_roundtrip_through_dict():
    p = crypto.KdfParams(n=1024, r=4, p=2)
    assert crypto.KdfParams.from_dict(p.to_dict()) == p


def test_kdf_params_from_dict_defaults_algo():
    assert crypto.KdfParams.from_dict({"n": 16, "r": 1, "p": 1}).algo == "scrypt"


def test_gcm_roundtrip_with_aad():
    salt, aad = os.urandom(16), b"the-header"
    token = crypto.encrypt_gcm(b"secret", "pw", salt, aad, FAST)
    assert crypto.decrypt_gcm(token, "pw", salt, aad, FAST) == b"secret"


def test_gcm_wrong_password_raises():
    salt = os.urandom(16)
    token = crypto.encrypt_gcm(b"secret", "right", salt, b"h", FAST)
    with pytest.raises(WrongPasswordOrCorrupt):
        crypto.decrypt_gcm(token, "wrong", salt, b"h", FAST)


def test_gcm_altered_aad_raises():
    salt = os.urandom(16)
    token = crypto.encrypt_gcm(b"secret", "pw", salt, b"header", FAST)
    with pytest.raises(WrongPasswordOrCorrupt):
        crypto.decrypt_gcm(token, "pw", salt, b"HEADER", FAST)


def test_gcm_altered_ciphertext_raises():
    salt = os.urandom(16)
    token = bytearray(crypto.encrypt_gcm(b"secret", "pw", salt, b"h", FAST))
    token[-1] ^= 0x01
    with pytest.raises(WrongPasswordOrCorrupt):
        crypto.decrypt_gcm(bytes(token), "pw", salt, b"h", FAST)


def test_fernet_roundtrip():
    salt = os.urandom(16)
    token = crypto.encrypt(b"v1 data", "pw", salt, FAST)
    assert crypto.decrypt(token, "pw", salt, FAST) == b"v1 data"


def test_fernet_wrong_password_raises():
    salt = os.urandom(16)
    token = crypto.encrypt(b"v1 data", "right", salt, FAST)
    with pytest.raises(WrongPasswordOrCorrupt):
        crypto.decrypt(token, "wrong", salt, FAST)


def test_derive_key_is_urlsafe_base64_of_32_bytes():
    import base64

    key = crypto.derive_key("pw", os.urandom(16), FAST)
    assert len(base64.urlsafe_b64decode(key)) == crypto.KEY_LEN


def test_unsupported_kdf_algo_rejected():
    # surfaced through the public encrypt path, not by poking _scrypt directly.
    with pytest.raises(ValueError, match="unsupported KDF"):
        crypto.encrypt_gcm(b"x", "pw", os.urandom(16), b"h", crypto.KdfParams(algo="argon2"))
