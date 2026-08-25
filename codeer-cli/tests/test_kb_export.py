from __future__ import annotations

import json
import unittest
from argparse import Namespace
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from codeer_cli.commands.kb import run_export


class FakeExportClient:
    def __init__(self, *, pending: bool = False) -> None:
        status = "INDEXING" if pending else "READY"
        self.nodes = {
            "kb-1": [
                {"id": "folder-1", "node_type": "FOLDER", "name": "FAQs"},
                {"id": "file-1", "node_type": "FILE", "name": "Guide.pdf", "status": status},
            ],
            "folder-1": [
                {"id": "file-2", "node_type": "FILE", "name": "Answer.md", "status": "READY"},
            ],
        }
        self.contents = {
            "file-1": {"node_id": "file-1", "status": status, "name": "Guide.pdf", "content": "# Guide"},
            "file-2": {"node_id": "file-2", "status": "READY", "name": "Answer.md", "content": "Answer"},
        }
        self.calls: list[tuple[str, str, dict]] = []

    def resolve_scope(self) -> tuple[str, str]:
        return "ws-1", "org-1"

    def get(self, path: str, **kwargs):
        self.calls.append(("GET", path, kwargs))
        if path == "/external/knowledge-bases/nodes":
            return self.nodes[kwargs["params"]["parent_id"]]
        node_id = path.split("/")[-2]
        return self.contents[node_id]


def export_args(directory: str | None = None, **overrides) -> Namespace:
    values = {
        "node_id": "kb-1",
        "file": None,
        "dir": directory,
        "overwrite": False,
        "full": False,
        "out": None,
    }
    values.update(overrides)
    return Namespace(**values)


class KbExportTests(unittest.TestCase):
    def test_exports_one_file_without_listing_folder_contents(self) -> None:
        client = FakeExportClient(pending=True)
        with TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "guide.md"
            stdout = StringIO()
            with redirect_stdout(stdout):
                status = run_export(
                    export_args(None, node_id="file-1", file=str(output_file), full=True),
                    client,  # type: ignore[arg-type]
                )

            self.assertEqual(status, 0)
            self.assertEqual(output_file.read_text(), "# Guide")
            result = json.loads(stdout.getvalue())
            self.assertEqual(result["mode"], "file")
            self.assertEqual(result["server_status"], "INDEXING")
            self.assertTrue(result["exported_while_not_ready"])
            self.assertEqual(result["non_ready_exported_count"], 1)
            self.assertFalse(any(call[1] == "/external/knowledge-bases/nodes" for call in client.calls))

    def test_exports_ready_snapshot_content_and_preserves_folders(self) -> None:
        client = FakeExportClient()
        with TemporaryDirectory() as tmpdir:
            stdout = StringIO()
            with redirect_stdout(stdout):
                status = run_export(export_args(tmpdir), client)  # type: ignore[arg-type]

            self.assertEqual(status, 0)
            self.assertEqual((Path(tmpdir) / "Guide.pdf.md").read_text(), "# Guide")
            self.assertEqual((Path(tmpdir) / "FAQs" / "Answer.md").read_text(), "Answer")
            summary = json.loads(stdout.getvalue())
            self.assertTrue(summary["complete"])
            self.assertEqual(summary["exported_count"], 2)
            content_paths = [call[1] for call in client.calls if call[1].endswith("/content")]
            self.assertEqual(
                content_paths,
                [
                    "/external/knowledge-bases/files/file-2/content",
                    "/external/knowledge-bases/files/file-1/content",
                ],
            )

    def test_exports_non_ready_file_when_endpoint_returns_content(self) -> None:
        client = FakeExportClient(pending=True)
        with TemporaryDirectory() as tmpdir:
            stdout = StringIO()
            with redirect_stdout(stdout):
                status = run_export(export_args(tmpdir, full=True), client)  # type: ignore[arg-type]

            self.assertEqual(status, 0)
            self.assertTrue((Path(tmpdir) / "Guide.pdf.md").exists())
            self.assertTrue((Path(tmpdir) / "FAQs" / "Answer.md").exists())
            result = json.loads(stdout.getvalue())
            self.assertEqual(result["skipped_count"], 0)
            self.assertEqual(result["exported_count"], 2)
            self.assertEqual(result["non_ready_exported_count"], 1)
            pending_file = next(item for item in result["files"] if item["node_id"] == "file-1")
            self.assertEqual(pending_file["server_status"], "INDEXING")
            self.assertTrue(pending_file["exported_while_not_ready"])
            self.assertIn(
                "/external/knowledge-bases/files/file-1/content",
                [call[1] for call in client.calls],
            )

    def test_skips_file_when_endpoint_returns_no_content(self) -> None:
        client = FakeExportClient(pending=True)
        client.contents["file-1"]["content"] = None
        with TemporaryDirectory() as tmpdir:
            stdout = StringIO()
            with redirect_stdout(stdout):
                status = run_export(export_args(tmpdir), client)  # type: ignore[arg-type]

            self.assertEqual(status, 1)
            self.assertFalse((Path(tmpdir) / "Guide.pdf.md").exists())
            summary = json.loads(stdout.getvalue())
            self.assertEqual(summary["skipped_count"], 1)
            self.assertEqual(summary["exported_count"], 1)
            self.assertIn(
                "/external/knowledge-bases/files/file-1/content",
                [call[1] for call in client.calls],
            )

    def test_blocks_before_writing_when_target_exists_without_overwrite(self) -> None:
        client = FakeExportClient()
        with TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "Guide.pdf.md"
            target.write_text("keep")
            stdout = StringIO()
            stderr = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = run_export(export_args(tmpdir), client)  # type: ignore[arg-type]

            self.assertEqual(status, 2)
            self.assertEqual(target.read_text(), "keep")
            self.assertIn("export blocked before writing", stderr.getvalue())
            self.assertFalse(any(call[1].endswith("/content") for call in client.calls))

    def test_overwrite_replaces_existing_export_file(self) -> None:
        client = FakeExportClient()
        with TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "Guide.pdf.md"
            target.write_text("old")
            with redirect_stdout(StringIO()):
                status = run_export(
                    export_args(tmpdir, overwrite=True),
                    client,  # type: ignore[arg-type]
                )

            self.assertEqual(status, 0)
            self.assertEqual(target.read_text(), "# Guide")

    def test_sanitizes_server_names_before_creating_local_paths(self) -> None:
        client = FakeExportClient()
        client.nodes["kb-1"] = [
            {"id": "file-1", "node_type": "FILE", "name": "../Guide.pdf", "status": "READY"},
        ]
        with TemporaryDirectory() as tmpdir:
            with redirect_stdout(StringIO()):
                status = run_export(export_args(tmpdir), client)  # type: ignore[arg-type]

            self.assertEqual(status, 0)
            exported = list(Path(tmpdir).glob("*.md"))
            self.assertEqual(len(exported), 1)
            self.assertEqual(exported[0].read_text(), "# Guide")
            self.assertEqual(exported[0].parent, Path(tmpdir))


if __name__ == "__main__":
    unittest.main()
