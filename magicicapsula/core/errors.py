"""errors raised by the core library.

the cli catches CapsuleError and prints a short message, so callers
never have to know the internals.
"""


class CapsuleError(Exception):
    """base class for anything that can go wrong with a capsule."""


class InvalidCapsule(CapsuleError):
    """the bytes are not a valid capsule (bad magic, version, or header)."""


class WrongPasswordOrCorrupt(CapsuleError):
    """decryption failed: wrong password, or the data was altered."""


class NoDraft(CapsuleError):
    """no capsule draft found here (run init first)."""


class CapsuleLocked(CapsuleError):
    """the unlock date has not arrived yet."""

    def __init__(self, unlock_at):
        self.unlock_at = unlock_at
        super().__init__(f"capsule is locked until {unlock_at.isoformat()}")
