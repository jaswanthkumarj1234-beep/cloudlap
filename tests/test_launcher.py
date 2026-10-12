"""Tests for the launcher's pure helper functions. The window itself is not opened."""

import importlib.machinery
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("tkinter")
pytest.importorskip("psutil")


def _load():
    path = Path(__file__).resolve().parent.parent / "launcher.pyw"
    loader = importlib.machinery.SourceFileLoader("cloudlap_launcher", str(path))
    spec = importlib.util.spec_from_loader("cloudlap_launcher", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


L = _load()


def test_clean_domain():
    assert L.clean_domain("https://a.ngrok-free.dev/") == "a.ngrok-free.dev"
    assert L.clean_domain(" a.ngrok-free.dev ") == "a.ngrok-free.dev"


def test_connector_url():
    assert L.connector_url({"ngrok_domain": "a.ngrok-free.dev"}) == "https://a.ngrok-free.dev/mcp"
    assert L.connector_url({}) == ""


def test_lock_enabled():
    assert L.lock_enabled({"totp_secret": "abc"}) is True
    assert L.lock_enabled({}) is False


def test_audit_line_never_shows_arguments():
    line = '{"ts": "2026-10-12T14:33:01", "tool": "run_command", "status": "OK", "args": {"command": "SECRET"}}'
    out = L.format_audit_line(line)
    assert out == "14:33:01  run_command  OK"
    assert "SECRET" not in out


def test_audit_line_bad_json():
    assert L.format_audit_line("not json") == ""


def test_port_closed():
    assert L.port_open(1) is False
