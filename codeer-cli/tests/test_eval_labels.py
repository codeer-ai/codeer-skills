from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from codeer_cli import eval_ as eval_mod
from codeer_cli.commands.eval_cmd import (
    _resolve_case_label_ids,
    run_cases_apply,
    run_label_create,
)


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def get(self, path: str):
        self.calls.append(("GET", path, {}))
        return []

    def post(self, path: str, **kwargs):
        self.calls.append(("POST", path, kwargs))
        return {"id": "created"}

    def put(self, path: str, **kwargs):
        self.calls.append(("PUT", path, kwargs))
        return {"id": "updated"}

    def delete(self, path: str, **kwargs):
        self.calls.append(("DELETE", path, kwargs))
        return {"ok": True}

    def resolve_scope(self):
        return "ws-1", "org-1"


class CasesApplyFakeClient(FakeClient):
    def resolve_scope(self):
        return "ws-1", None

    def get(self, path: str):
        self.calls.append(("GET", path, {}))
        if path == "/external/eval/case-labels":
            return []
        if path == "/external/eval/agents/agent-1/cases":
            return {
                "cases": [
                    {"id": "case-1", "input": "First question", "note": "Keep me"},
                    {"id": "case-2", "input": "Second question", "meta": {"keep": True}},
                ]
            }
        return []

    def post(self, path: str, **kwargs):
        self.calls.append(("POST", path, kwargs))
        if path == "/external/eval/case-labels":
            return {"id": "label-1", "name": kwargs["json"]["name"], "color": "#0969da"}
        return {"id": "unexpected-case"}


class EvalLabelClientTests(unittest.TestCase):
    def test_create_case_sends_label_ids(self) -> None:
        client = FakeClient()

        eval_mod.create_case(
            client,  # type: ignore[arg-type]
            agent_id="agent-1",
            input="How much?",
            label_ids=["10", "11"],
        )

        self.assertEqual(client.calls[0][0], "POST")
        self.assertEqual(client.calls[0][1], "/external/eval/cases")
        self.assertEqual(client.calls[0][2]["json"]["label_ids"], ["10", "11"])

    def test_update_case_sends_empty_label_ids_to_clear(self) -> None:
        client = FakeClient()

        eval_mod.update_case(
            client,  # type: ignore[arg-type]
            "case-1",
            label_ids=[],
        )

        self.assertEqual(client.calls[0][0], "PUT")
        self.assertEqual(client.calls[0][1], "/external/eval/cases/case-1")
        self.assertEqual(client.calls[0][2]["json"]["label_ids"], [])

    def test_case_label_crud_paths(self) -> None:
        client = FakeClient()

        eval_mod.list_case_labels(client)  # type: ignore[arg-type]
        eval_mod.create_case_label(client, name="Routing")  # type: ignore[arg-type]
        eval_mod.update_case_label(client, label_id="5", color="#0969da")  # type: ignore[arg-type]
        eval_mod.delete_case_label(client, label_id="5")  # type: ignore[arg-type]

        self.assertEqual(client.calls[0], ("GET", "/external/eval/case-labels", {}))
        self.assertEqual(client.calls[1][0:2], ("POST", "/external/eval/case-labels"))
        self.assertEqual(client.calls[1][2]["json"], {"name": "Routing"})
        self.assertEqual(client.calls[2][0:2], ("PUT", "/external/eval/case-labels/5"))
        self.assertEqual(client.calls[2][2]["json"], {"color": "#0969da"})
        self.assertEqual(client.calls[3][0:2], ("DELETE", "/external/eval/case-labels/5"))

    def test_label_create_dry_run_reports_active_api_key_workspace(self) -> None:
        client = FakeClient()
        args = SimpleNamespace(
            name="Routing",
            color="#0969da",
            dry_run=True,
            out=None,
        )

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            result = run_label_create(args, client)  # type: ignore[arg-type]

        report = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(report["workspace_id"], "ws-1")
        self.assertEqual(report["path"], "/external/eval/case-labels")
        self.assertEqual(client.calls, [])


class EvalLabelManifestTests(unittest.TestCase):
    def test_resolve_case_label_ids_from_ids_and_names(self) -> None:
        label_ids, label_names = _resolve_case_label_ids(
            {"label_ids": ["7"], "labels": ["Routing", "Billing"]},
            {
                "routing": {"id": "8", "name": "Routing"},
                "billing": {"id": "9", "name": "Billing"},
            },
        )

        self.assertEqual(label_ids, ["7", "8", "9"])
        self.assertEqual(label_names, ["Routing", "Billing"])

    def test_resolve_case_label_ids_dedupes_preserving_order(self) -> None:
        label_ids, _ = _resolve_case_label_ids(
            {"label_ids": ["7", "8"], "labels": ["Routing"]},
            {"routing": {"id": "8", "name": "Routing"}},
        )

        self.assertEqual(label_ids, ["7", "8"])

    def test_unknown_label_name_is_error(self) -> None:
        with self.assertRaises(ValueError):
            _resolve_case_label_ids({"labels": ["Missing"]}, {})

    def test_cases_apply_create_labels_dry_run_reports_without_writing(self) -> None:
        client = CasesApplyFakeClient()
        args = self._cases_apply_args(dry_run=True)

        with patch.object(Path, "read_text", return_value=json.dumps(self._manifest())):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = run_cases_apply(args, client)  # type: ignore[arg-type]

        report = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(report["would_create_case_labels"], ["Missing"])
        self.assertEqual([update["case_id"] for update in report["updates"]], ["case-1", "case-2"])
        self.assertTrue(all(update["label_ids"] == ["(new:Missing)"] for update in report["updates"]))
        self.assertTrue(all(call[0] == "GET" for call in client.calls))

    def test_cases_apply_creates_one_label_and_only_updates_existing_cases(self) -> None:
        client = CasesApplyFakeClient()
        args = self._cases_apply_args(dry_run=False)

        with patch.object(Path, "read_text", return_value=json.dumps(self._manifest())):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = run_cases_apply(args, client)  # type: ignore[arg-type]

        report = json.loads(stdout.getvalue())
        label_creates = [
            call for call in client.calls
            if call[0:2] == ("POST", "/external/eval/case-labels")
        ]
        case_creates = [
            call for call in client.calls
            if call[0:2] == ("POST", "/external/eval/cases")
        ]
        case_updates = [
            call for call in client.calls
            if call[0] == "PUT" and call[1] in {
                "/external/eval/cases/case-1",
                "/external/eval/cases/case-2",
            }
        ]

        self.assertEqual(result, 0)
        self.assertEqual(len(label_creates), 1)
        self.assertEqual(case_creates, [])
        self.assertEqual(len(case_updates), 2)
        self.assertTrue(all(call[2]["json"] == {"label_ids": ["label-1"]} for call in case_updates))
        self.assertEqual([row["case_id"] for row in report["reused"]], ["case-1", "case-2"])
        self.assertEqual(report["created_case_labels"][0]["name"], "Missing")

    @staticmethod
    def _cases_apply_args(*, dry_run: bool) -> SimpleNamespace:
        return SimpleNamespace(
            cases="manifest.json",
            agent="agent-1",
            attachments_dir=None,
            allow_duplicates=False,
            create_labels=True,
            dry_run=dry_run,
            out=None,
        )

    @staticmethod
    def _manifest() -> dict:
        return {
            "cases": [
                {
                    "label": "First",
                    "input": "First question",
                    "labels": ["Missing"],
                    "rubrics": {"eval-1": "Must pass"},
                },
                {
                    "label": "Second",
                    "input": "Second question",
                    "labels": ["Missing"],
                    "rubrics": {"eval-1": "Must pass"},
                },
            ]
        }


if __name__ == "__main__":
    unittest.main()
