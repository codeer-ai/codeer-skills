from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from codeer_cli import agents
from codeer_cli._validate import HumanHandoffValidationError, validate_human_handoff
from codeer_cli.commands import agent as agent_cmd


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def post(self, path: str, **kwargs):
        self.calls.append(("POST", path, kwargs))
        return {"id": "agent-1"}

    def patch(self, path: str, **kwargs):
        self.calls.append(("PATCH", path, kwargs))
        return {"id": "agent-1"}


class HumanHandoffValidationTests(unittest.TestCase):
    def test_accepts_enabled_config_without_timeout(self) -> None:
        result = validate_human_handoff({
            "enabled": True,
            "idle_timeout_minutes": None,
            "handoff_instructions": "Hand off when safety approval is required.",
        })

        self.assertEqual(result, {
            "enabled": True,
            "idle_timeout_minutes": None,
            "handoff_instructions": "Hand off when safety approval is required.",
        })

    def test_rejects_non_positive_timeout(self) -> None:
        with self.assertRaises(HumanHandoffValidationError):
            validate_human_handoff({"enabled": True, "idle_timeout_minutes": 0})

    def test_rejects_unknown_fields(self) -> None:
        with self.assertRaises(HumanHandoffValidationError):
            validate_human_handoff({"enabled": True, "unexpected": "value"})


class AgentHumanHandoffPayloadTests(unittest.TestCase):
    def test_create_forwards_human_handoff(self) -> None:
        client = FakeClient()
        handoff = {
            "enabled": True,
            "idle_timeout_minutes": 15,
            "handoff_instructions": "Hand off on request.",
        }

        agents.create(
            client,  # type: ignore[arg-type]
            workspace_id="workspace-1",
            name="Agent",
            system_prompt="Help safely.",
            human_handoff=handoff,
        )

        self.assertEqual(client.calls[0][0:2], ("POST", "/external/agents"))
        self.assertEqual(client.calls[0][2]["json"]["human_handoff"], handoff)

    def test_update_forwards_human_handoff(self) -> None:
        client = FakeClient()
        handoff = {
            "enabled": False,
            "idle_timeout_minutes": None,
            "handoff_instructions": None,
        }

        agents.update(
            client,  # type: ignore[arg-type]
            "agent-1",
            name="Agent",
            system_prompt="Help safely.",
            unified_tools=[],
            use_search=False,
            human_handoff=handoff,
        )

        self.assertEqual(client.calls[0][0:2], ("PATCH", "/external/agents/agent-1"))
        self.assertEqual(client.calls[0][2]["json"]["human_handoff"], handoff)


class AgentHumanHandoffCommandTests(unittest.TestCase):
    def _run_apply(self, payload: dict) -> tuple[int, dict]:
        with tempfile.TemporaryDirectory() as tmpdir:
            payload_path = Path(tmpdir) / "agent.json"
            payload_path.write_text(json.dumps(payload))
            args = SimpleNamespace(
                payload=str(payload_path),
                agent_id=None,
                dry_run=True,
                note=None,
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                status = agent_cmd.run_apply(args, object())
        return status, json.loads(stdout.getvalue()) if stdout.getvalue() else {}

    def test_apply_dry_run_summarizes_human_handoff_without_api_call(self) -> None:
        status, result = self._run_apply({
            "name": "Agent",
            "system_prompt": "Help safely.",
            "human_handoff": {
                "enabled": True,
                "idle_timeout_minutes": 10,
                "handoff_instructions": "Hand off on request.",
            },
        })

        self.assertEqual(status, 0)
        self.assertEqual(result["human_handoff"], {
            "enabled": True,
            "idle_timeout_minutes": 10,
            "instructions_chars": 20,
        })

    def test_apply_dry_run_rejects_invalid_handoff(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            status, result = self._run_apply({
                "name": "Agent",
                "system_prompt": "Help safely.",
                "human_handoff": {"enabled": "yes"},
            })

        self.assertEqual(status, 2)
        self.assertEqual(result, {})
        self.assertIn("human_handoff.enabled must be true or false", stderr.getvalue())

    def test_agent_summary_reads_meta_fallback_safely(self) -> None:
        fallback = agent_cmd._agent_summary({
            "id": "agent-1",
            "meta": {"human_handoff": {"enabled": True}},
        })
        malformed = agent_cmd._agent_summary({"id": "agent-2", "meta": "legacy"})

        self.assertTrue(fallback["human_handoff_enabled"])
        self.assertFalse(malformed["human_handoff_enabled"])


if __name__ == "__main__":
    unittest.main()
