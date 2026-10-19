"""Agent design naming must not discard established project evidence."""
import hashlib
import json
import unittest
from unittest.mock import patch

from codeer_cli.project import Project, ProjectError, read_json
import test_project
from test_project_evidence import EvidenceFixture


def legacy_revision(project):
    """Pre-rename serialization, independent of the new PATHS/resolver.

    Fixtures here have no local KB resources. Include Eval references just as
    the old version did so a saved audit is usable by the new CLI.
    """
    def digest(value):
        return hashlib.sha256(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()

    files = {}
    for key, default in (
        ("agent", "agent/settings.json"), ("instructions", "agent/instructions.md"),
        ("evals", "evals/design.json"), ("sources", "sources/index.md"),
        ("contract", "design/behavior-contract.md"), ("acceptance", "design/acceptance.json"),
    ):
        path = project.root / project.config.get("paths", {}).get(key, default)
        files[key] = digest(path.read_text()) if path.is_file() else None
    from codeer_cli.project_eval import references
    for ref in references(read_json(project.path("evals"), {})):
        if not ref.startswith(("http://", "https://")):
            path = project.root / ref
            files["reference:" + ref] = digest(path.read_bytes().hex()) if path.is_file() else None
    return digest({"target": project.target, "files": files})


class DesignPathTests(unittest.TestCase):
    setUp = test_project.ProjectTests.setUp
    cli = test_project.ProjectTests.cli

    def test_design_defaults_and_legacy_draft_continuation(self):
        self.cli("init")
        project = Project.load(self.root)
        self.assertEqual(project.path("design"), self.root / "design/agent-design.md")
        self.assertEqual(project.path("contract"), project.path("design"))
        old_draft = self.root / "design/behavior-contract.draft.md"
        old_draft.parent.mkdir()
        old_draft.write_text("Unresolved proposal")
        self.assertEqual(project.path("design"), self.root / "design/behavior-contract.md")
        before = project.revision()
        old_draft.write_text("Updated unresolved proposal")
        self.assertEqual(project.revision(), before)
        self.assertEqual(self.cli("status")[0], 0)
        self.assertEqual(self.cli("validate")[0], 0)
        self.assertFalse((self.root / "design/agent-design.md").exists())

    def test_explicit_new_and_legacy_paths_and_conflicts(self):
        self.cli("init")
        manifest = self.root / "project.toml"
        initial = manifest.read_text()
        for setting in ('design="notes/policy.md"', 'contract="notes/policy.md"',
                        'design="notes/policy.md"\ncontract="notes/../notes/policy.md"'):
            with self.subTest(setting=setting):
                manifest.write_text(initial + setting + "\n")
                self.assertEqual(Project.load(self.root).path("design"), self.root / "notes/policy.md")
        manifest.write_text(initial + 'design="notes/policy.md"\ncontract="other.md"\n')
        with self.assertRaisesRegex(ProjectError, "Conflicting.*paths"):
            Project.load(self.root)
        for setting in ('design="../outside.md"', 'contract="../outside.md"',
                        'design="inside.md"\ncontract="../outside.md"'):
            manifest.write_text(initial + setting + "\n")
            with self.assertRaisesRegex(ProjectError, "escapes root"):
                Project.load(self.root)

    def test_default_families_require_explicit_selection(self):
        self.cli("init")
        folder = self.root / "design"
        folder.mkdir()
        old = folder / "behavior-contract.md"
        new = folder / "agent-design.draft.md"
        old.write_text("Established old decision")
        new.write_text("Pending new proposal")
        with patch("codeer_cli.cli.CodeerClient.from_env", side_effect=AssertionError("client")):
            self.assertEqual(self.cli("status")[0], 2)
            self.assertEqual(self.cli("validate")[0], 2)
        with self.assertRaisesRegex(ProjectError, r"\[paths\].design"):
            Project.load(self.root)
        manifest = self.root / "project.toml"
        manifest.write_text(manifest.read_text() + 'design="design/behavior-contract.md"\n')
        self.assertEqual(Project.load(self.root).path("design"), old)
        self.assertEqual(new.read_text(), "Pending new proposal")

    def test_current_revision_survives_alias_and_filename_rename(self):
        self.cli("init")
        old = self.root / "design/behavior-contract.md"
        old.parent.mkdir()
        old.write_text("Accepted decision\n")
        project = Project.load(self.root)
        baseline = project.revision()
        old.rename(self.root / "design/agent-design.md")
        manifest = self.root / "project.toml"
        manifest.write_text(manifest.read_text() + 'design="design/agent-design.md"\n')
        self.assertEqual(Project.load(self.root).revision(), baseline)


class DesignEvidenceTests(EvidenceFixture, unittest.TestCase):
    def test_old_evidence_survives_design_rename_without_new_clearance(self):
        old = self.root / "design/behavior-contract.md"
        old.parent.mkdir()
        old.write_text("Established synthetic policy")
        project = self.setup_evidence()
        historical = project.root / "runs/historical/run.json"
        from codeer_cli.project import save_json
        save_json(historical, {"schema_version": 1, "id": "historical", "status": "passed",
                              "revision": legacy_revision(project), "history_id": "h1",
                              "snapshot": {"scope": project.target}, "counts": {"passed": 2}})
        baseline = project.revision()
        original = historical.read_bytes()
        self.assertEqual(self.cli("eval", "inspect-run", "--run-id", "historical")[1]["recorded_status"], "passed")
        self.assertEqual(self.cli("agent", "publish", "--history", "h1", "--dry-run")[0], 2)
        old.rename(self.root / "design/agent-design.md")
        self.assertEqual(project.revision(), baseline)
        _, status = self.cli("status")
        self.assertIsNone(status["latest_run"])
        self.assertEqual(historical.read_bytes(), original)
        calls = len(self.api.calls)
        self.assertEqual(self.cli("eval", "export", "--run-id", "historical", "--out-dir", str(project.root / "export"))[0], 2)
        self.assertEqual(len(self.api.calls), calls)
        self.assertEqual(historical.read_bytes(), original)
        project.path("design").write_text("Changed policy requires new validation")
        self.assertNotEqual(project.revision(), baseline)
        self.assertEqual(self.cli("agent", "publish", "--history", "h1", "--dry-run")[0], 2)
