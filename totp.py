"""Minimal RFC 6238 TOTP (SHA-1, 6 digits, 30 s steps) using only the standard library.

Compatible with Google Authenticator, Microsoft Authenticator, Authy and similar apps.
"""

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote


def new_secret() -> str:
    """Return a fresh random 160-bit secret, base32 encoded without padding."""
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _hotp(secret_b32: str, counter: int, digits: int = 6) -> str:
    pad = "=" * (-len(secret_b32) % 8)
    key = base64.b32decode(secret_b32.upper() + pad)
    mac = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    value = struct.unpack(">I", mac[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(value % (10 ** digits)).zfill(digits)


def code_at(secret_b32: str, t: float = None, step: int = 30, digits: int = 6) -> str:
    """The code an authenticator app would show at time t (default: now)."""
    t = time.time() if t is None else t
    return _hotp(secret_b32, int(t // step), digits)


def verify(secret_b32: str, code: str, t: float = None, step: int = 30,
           window: int = 1, digits: int = 6):
    """Check a code. Returns the matching time-step counter, or None.

    Accepts +/- `window` steps to tolerate small clock drift. The counter lets the
    caller reject a code that was already used.
    """
    code = "".join(ch for ch in str(code) if ch.isdigit())
    if len(code) != digits:
        return None
    t = time.time() if t is None else t
    base = int(t // step)
    match = None
    for counter in range(base - window, base + window + 1):
        if hmac.compare_digest(_hotp(secret_b32, counter, digits), code):
            match = counter
    return match


def otpauth_uri(secret_b32: str, account: str, issuer: str = "CloudLap") -> str:
    """The otpauth:// URI that authenticator apps read from a QR code."""
    return (
        f"otpauth://totp/{quote(issuer)}:{quote(account)}"
        f"?secret={secret_b32}&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30"
    )
