"""Tests for the guided setup helpers. The wizard itself is interactive and is not run here."""

import builtins
import py_compile
from pathlib import Path

import setup_wizard as w


def test_wizard_compiles():
    py_compile.compile(str(Path(w.__file__)), doraise=True)


def test_ask_uses_default_on_empty(monkeypatch):
    monkeypatch.setattr(builtins, "input", lambda _="": "")
    assert w.ask("x", "fallback") == "fallback"


def test_ask_returns_typed_value(monkeypatch):
    monkeypatch.setattr(builtins, "input", lambda _="": "  hello ")
    assert w.ask("x", "fallback") == "hello"


def test_yes_defaults(monkeypatch):
    monkeypatch.setattr(builtins, "input", lambda _="": "")
    assert w.yes("q", True) is True
    assert w.yes("q", False) is False


def test_yes_answers(monkeypatch):
    monkeypatch.setattr(builtins, "input", lambda _="": "No")
    assert w.yes("q", True) is False
    monkeypatch.setattr(builtins, "input", lambda _="": "y")
    assert w.yes("q", False) is True
