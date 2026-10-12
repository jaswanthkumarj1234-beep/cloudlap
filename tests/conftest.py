"""Shared test setup: keep the two-factor lock off unless a test turns it on."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def _auth_off_by_default(request):
    import server

    original = dict(server.config)
    if "test_auth" not in request.module.__name__:
        server.config["totp_secret"] = ""
    yield
    server.config.clear()
    server.config.update(original)
