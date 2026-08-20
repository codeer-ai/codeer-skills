from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from codeer_cli import agents
from codeer_cli.commands import agent as agent_cmd


MODEL_ID = "openai/gpt-5.6-luna"
MODEL_SETTINGS = {MODEL_ID: {"thinking": "xhigh"}}


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def post(self, path: str, **kwargs):
        self.calls.append(("POST", path, kwargs))
        return {"id": "agent-1"}

    def patch(self, path: str, **kwargs):
        self.calls.append(("PATCH", path, kwargs))
        return {"id": "agent-1"}


class AgentModelSettingsPayloadTests(unittest.TestCase):
    def test_create_forwards_model_settings(self) -> None:
        client = FakeClient()

        agents.create(
            client,  # type: ignore[arg-type]
            workspace_id="workspace-1",
            name="Agent",
            system_prompt="Help safely.",
            llm_model=MODEL_ID,
            llm_model_settings=MODEL_SETTINGS,
        )

        self.assertEqual(client.calls[0][0:2], ("POST", "/external/agents"))
        self.assertEqual(
            client.calls[0][2]["json"]["llm_model_settings"],
            MODEL_SETTINGS,
        )

    def test_update_forwards_model_settings(self) -> None:
        client = FakeClient()

        agents.update(
            client,  # type: ignore[arg-type]
            "agent-1",
            name="Agent",
            system_prompt="Help safely.",
            unified_tools=[],
            use_search=False,
            llm_model=MODEL_ID,
            llm_model_settings=MODEL_SETTINGS,
        )

        self.assertEqual(
            client.calls[0][0:2],
            ("PATCH", "/external/agents/agent-1"),
        )
        self.assertEqual(
            client.calls[0][2]["json"]["llm_model_settings"],
            MODEL_SETTINGS,
        )

    def test_update_forwards_empty_map_to_clear_settings(self) -> None:
        client = FakeClient()

        agents.update(
            client,  # type: ignore[arg-type]
            "agent-1",
            name="Agent",
            system_prompt="Help safely.",
            unified_tools=[],
            use_search=False,
            llm_model_settings={},
        )

        self.assertEqual(client.calls[0][2]["json"]["llm_model_settings"], {})

    def test_update_omits_model_settings_when_unspecified(self) -> None:
        client = FakeClient()

        agents.update(
            client,  # type: ignore[arg-type]
            "agent-1",
            name="Agent",
            system_prompt="Help safely.",
            unified_tools=[],
            use_search=False,
        )

        self.assertNotIn("llm_model_settings", client.calls[0][2]["json"])


class AgentModelSettingsCommandTests(unittest.TestCase):
    def _run_apply(
        self,
        payload: dict,
        *,
        agent_id: str | None = None,
        dry_run: bool = False,
    ) -> tuple[int, dict]:
        with tempfile.TemporaryDirectory() as tmpdir:
            payload_path = Path(tmpdir) / "agent.json"
            payload_path.write_text(json.dumps(payload))
            args = SimpleNamespace(
                payload=str(payload_path),
                agent_id=agent_id,
                dry_run=dry_run,
                note="settings regression",
                out=None,
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                status = agent_cmd.run_apply(args, object())
        return status, json.loads(stdout.getvalue()) if stdout.getvalue() else {}

    def test_apply_create_forwards_model_settings(self) -> None:
        payload = {
            "workspace_id": "workspace-1",
            "name": "Agent",
            "system_prompt": "Help safely.",
            "llm_model": MODEL_ID,
            "llm_model_settings": MODEL_SETTINGS,
        }
        history = [{"id": "history-1", "version_number": 1, "status": "draft"}]

        with (
            patch.object(
                agent_cmd.agents_mod,
                "create",
                return_value={"id": "agent-1"},
            ) as create,
            patch.object(agent_cmd.agents_mod, "list_versions", return_value=history),
        ):
            status, _ = self._run_apply(payload)

        self.assertEqual(status, 0)
        self.assertEqual(
            create.call_args.kwargs["llm_model_settings"],
            MODEL_SETTINGS,
        )

    def test_apply_update_preserves_present_and_empty_settings(self) -> None:
        history = [{"id": "history-2", "version_number": 2, "status": "draft"}]

        for model_settings in (MODEL_SETTINGS, {}):
            with self.subTest(model_settings=model_settings):
                payload = {
                    "name": "Agent",
                    "system_prompt": "Help safely.",
                    "llm_model_settings": model_settings,
                }
                with (
                    patch.object(agent_cmd.agents_mod, "update") as update,
                    patch.object(
                        agent_cmd.agents_mod,
                        "list_versions",
                        return_value=history,
                    ),
                ):
                    status, _ = self._run_apply(payload, agent_id="agent-1")

                self.assertEqual(status, 0)
                self.assertEqual(
                    update.call_args.kwargs["llm_model_settings"],
                    model_settings,
                )

    def test_apply_update_does_not_supply_omitted_settings(self) -> None:
        payload = {
            "name": "Agent",
            "system_prompt": "Help safely.",
        }
        history = [{"id": "history-2", "version_number": 2, "status": "draft"}]

        with (
            patch.object(agent_cmd.agents_mod, "update") as update,
            patch.object(agent_cmd.agents_mod, "list_versions", return_value=history),
        ):
            status, _ = self._run_apply(payload, agent_id="agent-1")

        self.assertEqual(status, 0)
        self.assertNotIn("llm_model_settings", update.call_args.kwargs)

    def test_apply_dry_run_distinguishes_settings_states(self) -> None:
        cases = (
            (MODEL_SETTINGS, True, MODEL_SETTINGS),
            ({}, True, {}),
            (None, False, None),
        )

        for model_settings, expected_provided, expected_settings in cases:
            with self.subTest(model_settings=model_settings):
                payload: dict[str, object] = {
                    "name": "Agent",
                    "system_prompt": "Help safely.",
                }
                if expected_provided:
                    payload["llm_model_settings"] = model_settings

                status, result = self._run_apply(
                    payload,
                    agent_id="agent-1",
                    dry_run=True,
                )

                self.assertEqual(status, 0)
                self.assertEqual(
                    result["llm_model_settings_provided"],
                    expected_provided,
                )
                self.assertEqual(
                    result["llm_model_settings"],
                    expected_settings,
                )


if __name__ == "__main__":
    unittest.main()
