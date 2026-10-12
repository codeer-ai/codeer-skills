import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from codeer_cli.cli import main
from codeer_cli.project import Project, ProjectError, discover


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.old = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, self.old)

    def cli(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            code = main(list(args))
        return code, json.loads(output.getvalue()) if output.getvalue() else None

    def test_offline_scaffold_reentry_and_nested_discovery(self):
        with patch("codeer_cli.cli.CodeerClient.from_env", side_effect=AssertionError("network")):
            self.assertEqual(self.cli("init")[0], 0)
            source = self.root / "sources/index.md"
            source.write_text("customer source https://example.invalid/sop\n")
            (self.root / "log.md").write_text("private decision\n")
            self.assertEqual(self.cli("init")[1]["created"], [])
            nested = self.root / "sources/documents"
            os.chdir(nested)
            self.assertEqual(discover().root, self.root)
            self.assertEqual(self.cli("validate")[0], 0)
            before = self.cli("status")[1]
            (self.root / "log.md").unlink()
            self.assertEqual(before, self.cli("status")[1])
            self.assertEqual(source.read_text(), "customer source https://example.invalid/sop\n")
            self.assertFalse((self.root / "design").exists())

    def test_binding_retains_comments_and_existing_paths(self):
        self.cli("init")
        p = self.root / "project.toml"
        p.write_text(p.read_text() + 'agent = "old/settings.json" # keep path\n')
        project = discover()
        project.bind(agent_id="a", api_base="https://api.invalid", workspace_id="w")
        project.bind(agent_id="a2")
        self.assertIn("# keep path", p.read_text())
        self.assertIn("# Bound by", p.read_text())
        self.assertEqual(Project.load(self.root).path("agent"), self.root / "old/settings.json")
        self.assertEqual(Project.load(self.root).target["agent_id"], "a2")

    def test_invalid_schema_and_escape_are_errors_before_client(self):
        self.cli("init")
        p = self.root / "project.toml"
        for content in ('schema_version=99\nname="x"', 'schema_version=1\nname="x"\n[paths]\nagent="../other.json"', 'invalid = ['):
            p.write_text(content)
            with patch("codeer_cli.cli.CodeerClient.from_env", side_effect=AssertionError("client")):
                self.assertEqual(self.cli("status")[0], 2)

    def test_agent_mismatch_blocks_before_client_and_explicit_escape_works(self):
        self.cli("init")
        discover().bind(agent_id="a")
        with patch("codeer_cli.cli.CodeerClient.from_env", side_effect=AssertionError("client")):
            self.assertEqual(self.cli("agent", "get", "other")[0], 2)
        fake = unittest.mock.Mock()
        fake.get.return_value = {"id": "other"}
        with patch("codeer_cli.cli.CodeerClient.from_env", return_value=fake):
            self.assertEqual(self.cli("--outside-project", "agent", "get", "other")[0], 0)

    def test_scope_rejects_other_base_and_workspace(self):
        self.cli("init")
        project = discover()
        project.bind(api_base="https://one", workspace_id="w")
        fake = unittest.mock.Mock(base_url="https://two")
        fake.resolve_scope.return_value = ("w", "org")
        with self.assertRaises(ProjectError):
            project.check_scope(fake)
        fake.base_url = "https://one"
        fake.resolve_scope.return_value = ("other", "org")
        with self.assertRaises(ProjectError):
            project.check_scope(fake)


if __name__ == "__main__":
    unittest.main()
