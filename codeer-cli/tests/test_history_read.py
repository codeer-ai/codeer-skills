from __future__ import annotations

import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import httpx

from codeer_cli import histories
from codeer_cli.client import CodeerClient
from codeer_cli.commands import history as history_cmd


class FakeClient:
    def resolve_scope(self) -> tuple[str, str]:
        return "workspace-1", "organization-1"


class HistoryReadTests(unittest.TestCase):
    def test_run_conversations_uses_management_export_and_writes_unmodified_parts(self) -> None:
        client = FakeClient()
        response = {
            "chat_id": 18649,
            "export_contract": "history-parts-v1",
            "part_revision": "revision-1",
            "messages": [
                {
                    "id": 10,
                    "conversation_group_id": "group-1",
                    "sequence": 1,
                    "part_kind": "user-prompt",
                    "content": {"content": "Question"},
                    "metadata": {"agent_history_id": "version-1"},
                    "source": "stack",
                    "attached_files": [],
                    "feedbacks": [],
                },
                {
                    "id": 11,
                    "conversation_group_id": "group-1",
                    "sequence": 2,
                    "part_kind": "tool-return",
                    "content": {
                        "tool_name": "http_request",
                        "tool_call_id": "call-1",
                        "content": {"owner": "Ada", "members": ["Grace"]},
                        "outcome": "success",
                    },
                    "metadata": {"reasoning_step_type": "consultant_http_request"},
                    "source": "stack",
                    "attached_files": [],
                    "feedbacks": [],
                },
            ],
        }
        args = SimpleNamespace(
            history_id=18649,
            full=False,
            out=None,
            client_visible=False,
            user=None,
        )

        with TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "history.json"
            args.out = str(out_path)
            stdout = StringIO()
            with (
                patch.object(history_cmd.hist_mod, "list_messages", return_value=response) as list_messages,
                redirect_stdout(stdout),
            ):
                result = history_cmd.run_conversations(args, client)

            artifact = json.loads(out_path.read_text())

        self.assertEqual(result, 0)
        list_messages.assert_called_once_with(client, 18649)
        self.assertEqual(artifact, response)
        self.assertEqual(artifact["messages"][1]["content"]["content"]["owner"], "Ada")
        summary = json.loads(stdout.getvalue())
        self.assertEqual(summary["turn_count"], 1)
        self.assertEqual(summary["part_count"], 2)
        self.assertTrue(summary["stdout_is_summary"])
        self.assertEqual(summary["export_mode"], "management")
        self.assertEqual(summary["export_contract"], "history-parts-v1")
        self.assertEqual(summary["parts"][1]["part_kind"], "tool-return")
        self.assertEqual(summary["parts"][1]["tool_name"], "http_request")
        self.assertNotIn("Ada", stdout.getvalue())

    def test_run_conversations_client_visible_requires_user_and_uses_v2(self) -> None:
        client = FakeClient()
        args = SimpleNamespace(
            history_id=18649,
            full=False,
            out=None,
            client_visible=True,
            user="user-1",
        )
        response = {"chat_id": 18649, "messages": []}

        with (
            patch.object(history_cmd.chats_mod, "list_messages", return_value=response) as list_messages,
            redirect_stdout(StringIO()),
        ):
            result = history_cmd.run_conversations(args, client)

        self.assertEqual(result, 0)
        list_messages.assert_called_once_with(client, 18649, external_user_id="user-1")

        args.user = None
        with redirect_stdout(StringIO()):
            result = history_cmd.run_conversations(args, client)
        self.assertEqual(result, 2)

    def test_run_conversations_bounds_stdout_part_summaries(self) -> None:
        client = FakeClient()
        args = SimpleNamespace(
            history_id=18649,
            full=False,
            out=None,
            client_visible=False,
            user=None,
        )
        response = {
            "chat_id": 18649,
            "export_contract": "history-parts-v1",
            "part_revision": "revision-1",
            "messages": [
                {
                    "id": part_id,
                    "conversation_group_id": f"group-{part_id}",
                    "part_kind": "text",
                    "content": {"content": f"Part {part_id}"},
                }
                for part_id in range(25)
            ],
        }

        stdout = StringIO()
        with (
            patch.object(history_cmd.hist_mod, "list_messages", return_value=response),
            redirect_stdout(stdout),
        ):
            result = history_cmd.run_conversations(args, client)

        summary = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(summary["part_count"], 25)
        self.assertEqual(summary["part_summaries_shown"], 20)
        self.assertTrue(summary["part_summaries_truncated"])

    def test_management_export_follows_server_pages_and_preserves_parts(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            offset = int(request.url.params["offset"])
            parts = [
                {
                    "id": part_id,
                    "conversation_group_id": "group-1",
                    "sequence": part_id,
                    "part_kind": "tool-return" if part_id == 2 else "text",
                    "content": {"content": {"part": part_id}},
                }
                for part_id in range(offset + 1, min(offset + 2, 3) + 1)
            ]
            payload = {
                "chat_id": 18649,
                "messages": parts,
                "export_contract": "history-parts-v1",
                "provider_raw_trace": "not_included",
                "system_prompts": "not_included",
                "missing_parts_do_not_prove_non_execution": True,
                "legacy_tool_outcomes": "not_recorded",
                "page": {"limit": 2, "offset": offset, "total_records": 3},
                "part_revision": "revision-1",
            }
            return httpx.Response(200, json={"error_code": 0, "data": payload})

        client = CodeerClient(base_url="https://api.codeer.ai", api_key="test-key")
        client._client.close()
        client._client = httpx.Client(
            base_url=client.base_url,
            transport=httpx.MockTransport(handler),
        )
        try:
            result = histories.list_messages(client, 18649, limit=500)
        finally:
            client.close()

        self.assertEqual([part["id"] for part in result["messages"]], [1, 2, 3])
        self.assertEqual(result["pages_fetched"], 2)
        self.assertEqual(result["page"]["total_records"], 3)
        self.assertEqual(
            [request.url.path for request in requests],
            [
                "/api/v1/external/histories/18649/messages",
                "/api/v1/external/histories/18649/messages",
            ],
        )
        self.assertEqual([request.url.params["offset"] for request in requests], ["0", "2"])

    def test_management_export_rejects_cross_page_revision_change(self) -> None:
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            offset = int(request.url.params["offset"])
            payload = {
                "chat_id": 18649,
                "messages": [{"id": offset + 1}],
                "export_contract": "history-parts-v1",
                "page": {"limit": 1, "offset": offset, "total_records": 2},
                "part_revision": f"revision-{call_count}",
            }
            return httpx.Response(200, json={"error_code": 0, "data": payload})

        client = CodeerClient(base_url="https://api.codeer.ai", api_key="test-key")
        client._client.close()
        client._client = httpx.Client(base_url=client.base_url, transport=httpx.MockTransport(handler))
        try:
            with self.assertRaisesRegex(ValueError, "changed while paging"):
                histories.list_messages(client, 18649, limit=1)
        finally:
            client.close()

    def test_negative_feedback_uses_management_parts_and_grouped_user_prompt(self) -> None:
        client = FakeClient()
        history_rows = [{
            "id": 18649,
            "name": "Support chat",
            "external_user_id": "user-1",
            "created_at": "2026-08-10T00:00:00Z",
        }]
        parts = {
            "chat_id": 18649,
            "messages": [
                {
                    "id": 1,
                    "conversation_group_id": "group-1",
                    "part_kind": "user-prompt",
                    "content": {"content": "Why did this fail?"},
                },
                {
                    "id": 2,
                    "conversation_group_id": "group-1",
                    "part_kind": "tool-call",
                    "content": {"tool_name": "http_request", "args": {"path": "/status"}},
                },
                {
                    "id": 3,
                    "conversation_group_id": "group-1",
                    "part_kind": "text",
                    "content": {"content": "The service is healthy."},
                    "feedbacks": [{"type": "sys_improve", "content": "Incorrect"}],
                },
            ],
        }

        with (
            patch.object(histories, "list", return_value=history_rows),
            patch.object(histories, "list_messages", return_value=parts) as list_messages,
        ):
            rows = histories.list_negative_feedback_turns(client, agent_id="agent-1")

        list_messages.assert_called_once_with(client, 18649)
        self.assertEqual(rows, [{
            "history_id": 18649,
            "history_title": "Support chat",
            "external_user_id": "user-1",
            "created_at": "2026-08-10T00:00:00Z",
            "turn_idx": 0,
            "part_idx": 2,
            "conversation_group_id": "group-1",
            "conversation_part_id": 3,
            "feedback_type": "sys_improve",
            "feedback_text": "Incorrect",
            "user_message": "Why did this fail?",
            "assistant_excerpt": "The service is healthy.",
        }])

    def test_negative_feedback_does_not_hide_management_read_failures(self) -> None:
        with (
            patch.object(histories, "list", return_value=[{"id": 18649}]),
            patch.object(histories, "list_messages", side_effect=RuntimeError("read failed")),
        ):
            with self.assertRaisesRegex(RuntimeError, "read failed"):
                histories.list_negative_feedback_turns(FakeClient(), agent_id="agent-1")


if __name__ == "__main__":
    unittest.main()
