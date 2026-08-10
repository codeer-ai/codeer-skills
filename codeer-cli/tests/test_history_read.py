from __future__ import annotations

import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from codeer_cli import histories
from codeer_cli.commands import history as history_cmd


class FakeClient:
    def resolve_scope(self) -> tuple[str, str]:
        return "workspace-1", "organization-1"


class HistoryReadTests(unittest.TestCase):
    def test_run_conversations_uses_v2_and_writes_unmodified_parts(self) -> None:
        client = FakeClient()
        response = {
            "chat_id": 18649,
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
                    "content": {"content": {"owner": "Ada", "members": ["Grace"]}},
                    "metadata": {"reasoning_step_type": "consultant_http_request"},
                    "source": "stack",
                    "attached_files": [],
                    "feedbacks": [],
                },
            ],
        }
        args = SimpleNamespace(history_id=18649, full=False, out=None)

        with TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "history.json"
            args.out = str(out_path)
            stdout = StringIO()
            with (
                patch.object(history_cmd.chats_mod, "list_messages", return_value=response) as list_messages,
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
        self.assertEqual(summary["parts"][1]["part_kind"], "tool-return")

    def test_negative_feedback_uses_v2_part_feedback_and_grouped_user_prompt(self) -> None:
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
            patch("codeer_cli.chats.list_messages", return_value=parts) as list_messages,
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


if __name__ == "__main__":
    unittest.main()
