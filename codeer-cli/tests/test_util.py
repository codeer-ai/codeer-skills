from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from codeer_cli.commands._util import write_json


class WriteJsonTests(unittest.TestCase):
    def test_write_json_creates_parent_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "nested" / "artifact.json"

            write_json(str(out), {"ok": True})

            self.assertEqual(json.loads(out.read_text()), {"ok": True})


if __name__ == "__main__":
    unittest.main()
