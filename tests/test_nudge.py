"""Tests for the first-call session nudge."""

import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))


def _reset(server):
    server._last_tool_call = None


class TestSessionNudge:
    def test_first_call_lists_saved_projects(self):
        import server
        _reset(server)
        with patch.object(server, "_saved_project_names", return_value=["alpha", "beta"]):
            text = server._nudge_text("run_command")
        assert "alpha" in text and "beta" in text
        assert "load_context" in text

    def test_second_call_is_quiet(self):
        import server
        _reset(server)
        with patch.object(server, "_saved_project_names", return_value=["alpha"]):
            server._nudge_text("run_command")
            assert server._nudge_text("run_command") == ""

    def test_nudge_returns_after_idle_gap(self):
        import server
        _reset(server)
        server._last_tool_call = time.time() - server.NUDGE_IDLE_SECONDS - 5
        with patch.object(server, "_saved_project_names", return_value=["alpha"]):
            assert "alpha" in server._nudge_text("read_file")

    def test_no_nudge_without_saved_projects(self):
        import server
        _reset(server)
        with patch.object(server, "_saved_project_names", return_value=[]):
            assert server._nudge_text("run_command") == ""

    def test_no_nudge_on_load_or_save_context(self):
        import server
        for name in ("load_context", "save_context"):
            _reset(server)
            with patch.object(server, "_saved_project_names", return_value=["alpha"]):
                assert server._nudge_text(name) == ""

    def test_decorator_appends_to_string_result(self):
        import server
        _reset(server)

        @server._nudged
        async def fake_tool():
            return "ok"

        with patch.object(server, "_saved_project_names", return_value=["alpha"]):
            result = asyncio.run(fake_tool())
        assert result.startswith("ok")
        assert "alpha" in result

    def test_decorator_leaves_non_strings_alone(self):
        import server
        _reset(server)

        @server._nudged
        async def fake_tool():
            return {"a": 1}

        with patch.object(server, "_saved_project_names", return_value=["alpha"]):
            assert asyncio.run(fake_tool()) == {"a": 1}
