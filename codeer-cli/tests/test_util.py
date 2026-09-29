from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from codeer_cli.commands import eval_cmd, history, kb, model
from codeer_cli.commands._util import NOISY_KEYS, strip_noisy_fields, write_json


class StripMetadataTests(unittest.TestCase):
    def test_only_resource_metadata_is_simplified(self) -> None:
        content = {
            key: [{"workspace": {"owner": key, "custom": None}}]
            for key in NOISY_KEYS | {"workspace"}
        }
        record = {
            **{key: "server metadata" for key in NOISY_KEYS},
            "workspace": {
                "id": "ws",
                "name": "Team",
                "organization_id": "org",
                "members": [],
            },
            "id": "resource",
            **{
                key: content
                for key in (
                    "payload",
                    "schema",
                    "template",
                    "input_contracts",
                    "meta",
                    "data",
                    "content",
                )
            },
        }
        expected = {
            key: value for key, value in record.items() if key not in NOISY_KEYS
        }
        expected["workspace"] = {"id": "ws", "name": "Team", "organization_id": "org"}
        self.assertEqual(strip_noisy_fields(record), expected)
        self.assertEqual(strip_noisy_fields([record]), [expected])
        self.assertIn("members", record["workspace"])
        self.assertTrue(NOISY_KEYS <= record.keys())

    def test_non_resource_values_are_preserved(self) -> None:
        for value in (None, False, 1, "text"):
            self.assertEqual(strip_noisy_fields(value), value)

    def test_shared_read_exports_keep_nested_content(self) -> None:
        content = {
            "owner": "Ada",
            "profile": {"members": ["Grace"]},
            "workspace": {"custom": False},
        }
        record = {"id": "resource", "owner": "server metadata", "content": content}
        cases = [
            (history.run_get, history.hist_mod, "get", record, {"history_id": 1}),
            (kb.run_files, kb.kb_mod, "list_nodes", [record], {"kb_id": "kb-1"}),
            (
                eval_cmd.run_list,
                eval_cmd.eval_mod,
                "list_cases",
                [record],
                {"agent": "agent-1", "all": True, "limit": 20},
            ),
            (
                model.run_list,
                model.models_mod,
                "list_available",
                [record],
                {"type": "text"},
            ),
        ]
        for run, module, method, response, options in cases:
            with (
                self.subTest(command=run.__module__),
                tempfile.TemporaryDirectory() as tmp,
            ):
                path = Path(tmp) / "export.json"
                args = SimpleNamespace(full=True, out=str(path), **options)
                client = Mock()
                client.resolve_scope.return_value = ("ws", "org")
                with (
                    patch.object(module, method, return_value=response),
                    redirect_stdout(StringIO()),
                    redirect_stderr(StringIO()),
                ):
                    self.assertEqual(run(args, client), 0)
                artifact = json.loads(path.read_text())
                row = artifact[0] if isinstance(artifact, list) else artifact
                self.assertNotIn("owner", row)
                self.assertEqual(row["content"], content)


class WriteJsonTests(unittest.TestCase):
    def test_write_json_creates_parent_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "nested" / "artifact.json"

            write_json(str(out), {"ok": True})

            self.assertEqual(json.loads(out.read_text()), {"ok": True})


if __name__ == "__main__":
    unittest.main()
