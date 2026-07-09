from __future__ import annotations

import unittest

from codeer_cli import kb as kb_mod


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def patch(self, path: str, **kwargs):
        self.calls.append(("PATCH", path, kwargs))
        return {"id": "node-1"}

    def delete(self, path: str, **kwargs):
        self.calls.append(("DELETE", path, kwargs))
        return {"ok": True}


class KbNodeClientTests(unittest.TestCase):
    def test_update_node_renames_by_patch(self) -> None:
        client = FakeClient()

        kb_mod.update_node(
            client,  # type: ignore[arg-type]
            organization_id="org-1",
            workspace_id="ws-1",
            node_id="node-1",
            name="New Name",
        )

        self.assertEqual(
            client.calls[0],
            (
                "PATCH",
                "/external/knowledge-bases/nodes/node-1",
                {"json": {"name": "New Name"}},
            ),
        )

    def test_delete_node_deletes_by_node_id(self) -> None:
        client = FakeClient()

        kb_mod.delete_node(
            client,  # type: ignore[arg-type]
            organization_id="org-1",
            workspace_id="ws-1",
            node_id="node-1",
        )

        self.assertEqual(
            client.calls[0],
            (
                "DELETE",
                "/external/knowledge-bases/nodes/node-1",
                {},
            ),
        )


if __name__ == "__main__":
    unittest.main()
