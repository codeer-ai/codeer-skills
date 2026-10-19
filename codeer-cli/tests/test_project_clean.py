"""Real reclamation, cross-binding references and stale-preview protection."""
import hashlib
import json
import os
import unittest
from unittest.mock import patch

from codeer_cli.project import discover, fingerprint, save_json
import test_project_deployments as fixtures


class CleanTests(unittest.TestCase):
    setUp = fixtures.DeploymentTests.setUp
    cli = fixtures.DeploymentTests.cli
    bind = fixtures.DeploymentTests.bind

    def receipt(self, name, status="applied"):
        path = discover().local_dir / "receipts" / f"{name}.json"
        plan = {"resource": "agent", "server_id": "a", "payload": {"description": name},
                "local": {"description": name}, "scope": discover().target}
        plan["token"] = fingerprint(plan)
        save_json(path, {"plan": plan, "status": status, "response": {"id": "a"}, "readback": {"description": name}})
        return path

    def inventory(self):
        return {str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob("*") if path.is_file() and path.name != "project.lock"}

    def test_exact_nonzero_reclamation_keeps_all_reference_forms_and_fixed_history(self):
        project = self.bind()
        removable = self.receipt("old")
        structured = self.receipt("live")
        markdown = self.receipt("cited")
        hashed = self.receipt("hashed")
        kept = self.receipt("manual")
        pending = self.receipt("unknown", "outcome_unknown")
        project.save_state({"resources": {"agent": {"receipt": str(structured.relative_to(self.root)), "server_id": "a"}}})
        (self.root / "reviews").mkdir()
        report = self.root / "reviews/audit.md"
        report.write_text(f"[proof](../{markdown.relative_to(self.root)})\nSHA-256: {hashlib.sha256(hashed.read_bytes()).hexdigest()}\n")
        fixed = self.root / "runs/historical/run.json"
        save_json(fixed, {"schema_version": 1, "status": "passed"})
        self.assertEqual(self.cli("clean", "--keep", str(kept), "--reason", "Operator reference")[0], 0)
        before = self.inventory()
        with patch("codeer_cli.cli.CodeerClient.from_env", side_effect=AssertionError("network")):
            code, plan = self.cli("clean", "--dry-run")
        self.assertEqual(code, 0, self.error)
        self.assertEqual(self.inventory(), before)
        self.assertEqual([row["path"] for row in plan["candidates"]], [str(removable.relative_to(self.root))])
        size = removable.stat().st_size
        code, result = self.cli("clean", "--expect", plan["token"])
        self.assertEqual(code, 0, self.error)
        self.assertEqual(result["bytes"], size)
        self.assertFalse(removable.exists())
        for path in (structured, markdown, hashed, kept, pending, fixed, report):
            self.assertEqual(path.read_bytes(), before[str(path.relative_to(self.root))])
        self.assertEqual(self.cli("status")[0], 0)
        self.artifact = self.root

    def test_other_binding_and_transitive_references_protect_selected_history(self):
        self.bind()
        first, second = self.receipt("first"), self.receipt("second")
        record = json.loads(first.read_text())
        record["recovery"] = str(second.relative_to(self.root))
        save_json(first, record)
        other = self.bind("prod")
        other.save_state({"resources": {"agent": {"receipt": str(first.relative_to(self.root))}}})
        self.assertEqual(self.cli("--binding", "dev", "clean", "--dry-run")[1]["file_count"], 0)
        self.assertTrue(first.exists() and second.exists())

    def test_new_reference_invalidates_token_and_age_can_filter(self):
        project = self.bind()
        old = self.receipt("old")
        _, plan = self.cli("clean", "--dry-run")
        project.save_state({"resources": {}, "pinned": str(old.relative_to(self.root))})
        self.assertEqual(self.cli("clean", "--expect", plan["token"])[0], 2)
        self.assertTrue(old.exists())
        project.save_state({"resources": {}})
        self.assertEqual(self.cli("clean", "--older-than", "1d", "--dry-run")[1]["file_count"], 0)
        os.utime(old, (1, 1))
        self.assertEqual(self.cli("clean", "--older-than", "1d", "--dry-run")[1]["file_count"], 1)

    def test_unknown_history_keeps_binding_and_corrupt_global_state_refuses(self):
        project = self.bind()
        self.receipt("old")
        unknown = project.local_dir / "receipts/mystery.json"
        unknown.write_text("unknown bytes")
        code, plan = self.cli("clean", "--dry-run")
        self.assertEqual(code, 0, self.error)
        self.assertEqual(plan["file_count"], 0)
        self.assertTrue(plan["unknown"])
        unknown.unlink()
        project.state_path.write_text("broken")
        self.assertEqual(self.cli("clean", "--dry-run")[0], 2)

    def test_symlink_cannot_escape_and_preview_does_not_create_a_lock(self):
        project = self.bind()
        lock = self.root / ".codeer/project.lock"
        lock.unlink()
        self.receipt("old")
        self.assertEqual(self.cli("clean", "--dry-run")[0], 0)
        self.assertFalse(lock.exists())
        (project.local_dir / "receipts/escape.json").symlink_to(self.root / "sources/index.md")
        self.assertEqual(self.cli("clean", "--dry-run")[0], 2)

    def test_interruption_deletes_referrers_first_and_cycles_are_retained(self):
        from codeer_cli.clean import clean
        from pathlib import Path
        project = self.bind()
        dependency = self.receipt("a-previous")
        later = self.receipt("b-later")
        row = json.loads(later.read_text())
        row["previous"] = str(dependency.relative_to(self.root))
        save_json(later, row)
        _, plan = self.cli("clean", "--dry-run")
        self.assertEqual(plan["candidates"][0]["path"], str(later.relative_to(self.root)))
        unlink = Path.unlink
        def interrupt(path, *args, **kwargs):
            if path == dependency:
                raise OSError("Interrupted after one deletion")
            return unlink(path, *args, **kwargs)
        with patch.object(Path, "unlink", interrupt), self.assertRaises(OSError):
            clean(project, expected=plan["token"])
        self.assertTrue(dependency.exists())
        self.assertFalse(later.exists())
        _, fresh = self.cli("clean", "--dry-run")
        self.assertEqual(self.cli("clean", "--expect", fresh["token"])[0], 0)
        one, two = self.receipt("cycle-1"), self.receipt("cycle-2")
        for source, target in ((one, two), (two, one)):
            row = json.loads(source.read_text())
            row["previous"] = str(target.relative_to(self.root))
            save_json(source, row)
        self.assertEqual(self.cli("clean", "--dry-run")[1]["file_count"], 0)

    def test_status_alone_cannot_make_an_unknown_record_deletable(self):
        project = self.bind()
        self.receipt("valid")
        path = project.local_dir / "receipts/incomplete.json"
        save_json(path, {"plan": {"resource": "agent", "scope": project.target}, "status": "applied"})
        code, plan = self.cli("clean", "--dry-run")
        self.assertEqual(code, 0, self.error)
        self.assertEqual(plan["file_count"], 0)
        self.assertTrue(plan["unknown"])
        path.unlink()
        malformed = self.receipt("wrong-scope")
        row = json.loads(malformed.read_text())
        row["plan"]["scope"]["api_base"] = 123
        save_json(malformed, row)
        self.assertEqual(self.cli("clean", "--dry-run")[1]["file_count"], 0)
        malformed.unlink()
        save_json(self.root / ".codeer/keep.json", {"schema_version": 1, "entries": ["invalid"]})
        self.assertEqual(self.cli("clean", "--dry-run")[0], 2)
