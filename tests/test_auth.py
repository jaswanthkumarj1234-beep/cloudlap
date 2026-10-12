"""Tests for the TOTP two-factor lock."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import totp

RFC_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # ASCII "12345678901234567890"


def _reset(server, secret=RFC_SECRET):
    server.config["totp_secret"] = secret
    server.config["unlock_minutes"] = 10  # pinned so tests do not depend on a local config.json
    server.config["max_unlock_failures"] = 3
    server._AUTH.update({"unlocked_until": 0.0, "locked_until": 0.0, "last_counter": -1, "fails": []})


class TestTotp:
    def test_rfc6238_vectors(self):
        # 6-digit tails of the RFC 6238 SHA-1 8-digit test values
        assert totp.code_at(RFC_SECRET, 59) == "287082"
        assert totp.code_at(RFC_SECRET, 1111111109) == "081804"
        assert totp.code_at(RFC_SECRET, 1234567890) == "005924"
        assert totp.code_at(RFC_SECRET, 2000000000) == "279037"

    def test_verify_accepts_adjacent_step_only(self):
        t = 1111111109
        code = totp.code_at(RFC_SECRET, t)
        assert totp.verify(RFC_SECRET, code, t=t) is not None
        assert totp.verify(RFC_SECRET, code, t=t + 30) is not None
        assert totp.verify(RFC_SECRET, code, t=t + 120) is None

    def test_verify_rejects_garbage(self):
        assert totp.verify(RFC_SECRET, "abc", t=59) is None
        assert totp.verify(RFC_SECRET, "12345", t=59) is None

    def test_new_secret_is_valid_base32(self):
        s = totp.new_secret()
        assert len(s) == 32
        assert len(totp.code_at(s)) == 6

    def test_uri_has_no_spaces(self):
        uri = totp.otpauth_uri(RFC_SECRET, "shiva")
        assert uri.startswith("otpauth://totp/CloudLap:shiva?secret=")


class TestLock:
    def test_disabled_without_secret(self):
        import server
        _reset(server, secret="")
        assert server._auth_gate() is None

    def test_locked_by_default_and_tool_refuses(self):
        import server
        _reset(server)
        assert "locked" in server._auth_gate().lower()
        out = asyncio.run(server.run_command("echo hi"))
        assert "locked" in out.lower()

    def test_unlock_then_lock(self):
        import server
        _reset(server)
        now = 1_800_000_000.0
        with patch.object(server._time, "time", return_value=now):
            code = totp.code_at(RFC_SECRET, now)
            assert "Unlocked" in server._try_unlock(code)
            assert server._auth_gate() is None
        with patch.object(server._time, "time", return_value=now + 11 * 60):
            assert server._auth_gate() is not None  # expired after 10 minutes
        server._AUTH["unlocked_until"] = now + 999
        asyncio.run(server.lock())
        assert server._AUTH["unlocked_until"] == 0.0

    def test_replayed_code_is_rejected(self):
        import server
        _reset(server)
        now = 1_800_000_000.0
        with patch.object(server._time, "time", return_value=now):
            code = totp.code_at(RFC_SECRET, now)
            assert "Unlocked" in server._try_unlock(code)
            server._AUTH["unlocked_until"] = 0.0
            assert "Wrong or already used" in server._try_unlock(code)

    def test_three_failures_lock_out_even_a_good_code(self):
        import server
        _reset(server)
        now = 1_800_000_000.0
        with patch.object(server._time, "time", return_value=now):
            server._try_unlock("000000")
            server._try_unlock("000001")
            assert "locked out" in server._try_unlock("000002").lower()
            good = totp.code_at(RFC_SECRET, now)
            assert "Too many" in server._try_unlock(good)
        with patch.object(server._time, "time", return_value=now + 16 * 60):
            good = totp.code_at(RFC_SECRET, now + 16 * 60)
            assert "Unlocked" in server._try_unlock(good)

    def test_get_system_info_stays_open(self):
        import server
        _reset(server)
        out = asyncio.run(server.get_system_info())
        assert "locked" not in out.lower()
