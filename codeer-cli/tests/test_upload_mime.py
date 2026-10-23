from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from codeer_cli.commands.eval_cmd import _upload_attachment
from codeer_cli.kb import guess_upload_mime


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def post(self, path: str, **kwargs):
        self.calls.append((path, kwargs))
        return {"uuid": "file-1"}


class GuessUploadMimeTest(unittest.TestCase):
    def test_text_extensions_get_text_types(self):
        self.assertEqual(guess_upload_mime("paihan-context-5.md"), "text/markdown")
        self.assertEqual(guess_upload_mime("NOTES.MARKDOWN"), "text/markdown")
        self.assertEqual(guess_upload_mime("notes.txt"), "text/plain")
        self.assertEqual(guess_upload_mime("rows.csv"), "text/csv")

    def test_eval_attachment_upload_sends_markdown_content_type(self):
        client = RecordingClient()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "paihan-context-5.md"
            path.write_text("# PaiHan current presentation\n")
            uuid = _upload_attachment(client, file_path=path, workspace_id="ws-1")

        self.assertEqual(uuid, "file-1")
        path_called, kwargs = client.calls[0]
        self.assertEqual(path_called, "/external/files")
        name, _content, content_type = kwargs["files"]["file"]
        self.assertEqual(name, "paihan-context-5.md")
        self.assertEqual(content_type, "text/markdown")
        self.assertEqual(kwargs["data"]["purpose"], "evaluation_context")


if __name__ == "__main__":
    unittest.main()
