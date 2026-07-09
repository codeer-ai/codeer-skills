from __future__ import annotations

import unittest

from codeer_cli import eval_ as eval_mod
from codeer_cli.commands.eval_cmd import _resolve_case_label_ids


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

        eval_mod.list_case_labels(client, workspace_id="ws-1")  # type: ignore[arg-type]
        eval_mod.create_case_label(client, workspace_id="ws-1", name="Routing")  # type: ignore[arg-type]
        eval_mod.update_case_label(client, label_id="5", color="#0969da")  # type: ignore[arg-type]
        eval_mod.delete_case_label(client, label_id="5")  # type: ignore[arg-type]

        self.assertEqual(client.calls[0], ("GET", "/eval/workspaces/ws-1/case-labels", {}))
        self.assertEqual(client.calls[1][0:2], ("POST", "/eval/workspaces/ws-1/case-labels"))
        self.assertEqual(client.calls[1][2]["json"], {"name": "Routing"})
        self.assertEqual(client.calls[2][0:2], ("PUT", "/eval/case-labels/5"))
        self.assertEqual(client.calls[2][2]["json"], {"color": "#0969da"})
        self.assertEqual(client.calls[3][0:2], ("DELETE", "/eval/case-labels/5"))


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


if __name__ == "__main__":
    unittest.main()
