"""Executable rehearsal of the bounded, manual one-time preparation runbook.

Helpers are fixture-only file operations, not a second CLI format reader or a
customer migration utility. Every input lives in a synthetic temporary project.
"""
import copy
import hashlib
import shutil
import unittest

from codeer_cli.project import read_json, save_json, ProjectError
import test_project_deployments as fixtures


def manifest(root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*") if path.is_file() and path.name != "project.lock"}


def reviewed_carry(project, expected):
    """A single reviewed fixture correction, retaining fixed source evidence."""
    if manifest(project.root) != expected:
        raise ProjectError("Source changed after review; discard the stale correction")
    state = project.state()
    entry = state["resources"]["kb:faq"]
    if entry["receipt"].endswith("/recovery-reviewed.json"):
        return []
    original = project.root / entry["receipt"]
    receipt = read_json(original)
    receipt["provenance"] = {"original_path": entry["receipt"], "original_sha256": hashlib.sha256(original.read_bytes()).hexdigest()}
    destination = project.local_dir / "receipts/recovery-reviewed.json"
    save_json(destination, receipt)
    entry["receipt"] = str(destination.relative_to(project.root))
    project.save_state(state)
    return [str(destination.relative_to(project.root)), str(project.state_path.relative_to(project.root))]


class UpgradeRehearsalTests(unittest.TestCase):
    setUp = fixtures.DeploymentTests.setUp
    cli = fixtures.DeploymentTests.cli
    bind = fixtures.DeploymentTests.bind
    local_agent = fixtures.DeploymentTests.local_agent

    def prepare_copy(self):
        project = self.bind("beta-customer-a-main")
        self.local_agent()
        scope = {key: project.target.get(key) for key in ("api_base", "workspace_id", "agent_id")}
        receipt = project.local_dir / "receipts/known-unknown.json"
        save_json(receipt, {"status": "outcome_unknown", "plan": {"resource": "kb:faq", "scope": scope,
                            "kb_id": "known-kb", "upload_files": ["faq.md"], "local": {"faq.md": "source-hash"}},
                            "response": {"nodes": [{"node_id": "known-file", "original_name": "faq.md"}]}})
        entry = {"server_id": "known-kb", "node_ids": ["known-file"], "status": "outcome_unknown",
                 "receipt": str(receipt.relative_to(self.root)), "scope": scope,
                 "base": [{"status": "PROCESSING", "node_id": "known-file"}], "local_base": {"faq.md": "old-hash"}}
        project.save_state({"schema_version": 1, "resources": {"kb:faq": entry}})
        save_json(self.root / "runs/historical/run.json", {"schema_version": 1, "id": "historical", "status": "passed", "snapshot": {"scope": scope}})
        old_project = self.root / "runs/historical/inputs/project.toml"
        old_project.parent.mkdir(parents=True)
        old_project.write_text('schema_version = 1\nname = "Historical snapshot"\n')
        report = self.root / "reviews/baseline.md"
        report.parent.mkdir(parents=True)
        report.write_text(f"Fixed evidence: {receipt.relative_to(self.root)}\nSHA-256 {hashlib.sha256(receipt.read_bytes()).hexdigest()}\n")
        save_json(self.root / "releases/historical/release.json", {"id": "old-release", "status": "published", "plan": {"scope": scope}})
        return project

    def test_zero_change_current_contract_and_reviewed_carry_are_idempotent(self):
        project = self.prepare_copy()
        source_before = manifest(self.root)
        revision = project.revision()
        self.assertEqual(self.cli("status")[0], 0)
        self.assertEqual(self.cli("agent", "bindings")[0], 0)
        self.assertTrue(self.cli("eval", "inspect-run", "--run-id", "historical")[1]["historical"])
        self.assertEqual(manifest(self.root), source_before)
        clone = self.root.parent / (self.root.name + "-reviewed-copy")
        self.addCleanup(shutil.rmtree, clone)
        shutil.copytree(self.root, clone)
        from codeer_cli.project import Project
        prepared = Project.load(clone)
        original_entry = copy.deepcopy(prepared.state()["resources"]["kb:faq"])
        diff = reviewed_carry(prepared, manifest(clone))
        self.assertEqual(len(diff), 2)
        after = manifest(clone)
        self.assertEqual({path for path in set(source_before) | set(after) if source_before.get(path) != after.get(path)}, set(diff))
        entry = prepared.state()["resources"]["kb:faq"]
        self.assertEqual({key: value for key, value in entry.items() if key != "receipt"},
                         {key: value for key, value in original_entry.items() if key != "receipt"})
        self.assertEqual(prepared.revision(), revision)
        self.assertEqual(reviewed_carry(prepared, after), [])
        self.assertEqual(manifest(clone), after)
        self.assertEqual(manifest(self.root), source_before)
        self.artifact = clone

    def test_stale_review_and_rollback_boundary_preserve_new_operation_identity(self):
        project = self.prepare_copy()
        before = manifest(self.root)
        backup = self.root.parent / (self.root.name + "-backup")
        self.addCleanup(shutil.rmtree, backup)
        shutil.copytree(self.root, backup)
        original = project.path("instructions").read_bytes()
        project.path("instructions").write_text("Changed after review")
        with self.assertRaisesRegex(ProjectError, "Source changed"):
            reviewed_carry(project, before)
        project.path("instructions").write_bytes(original)
        self.assertEqual(manifest(self.root), before)
        reviewed_carry(project, before)
        # Before a new dispatch, exact backup restoration is feasible.
        shutil.rmtree(project.local_dir)
        shutil.copytree(backup / project.local_dir.relative_to(self.root), project.local_dir)
        self.assertEqual(manifest(self.root), before)
        reviewed_carry(project, before)
        prepared = manifest(self.root)
        # A later operation's identity must survive. A stale rollback is refused.
        state = project.state()
        state["resources"]["attachment:new-operation"] = {"status": "outcome_unknown", "server_id": "new-known-id"}
        project.save_state(state)
        with self.assertRaisesRegex(ProjectError, "Source changed"):
            reviewed_carry(project, prepared)
        self.assertEqual(project.state()["resources"]["attachment:new-operation"]["server_id"], "new-known-id")
        self.assertFalse(any(method != "GET" for method, _, _ in self.api.calls))

    def test_historical_delivery_checks_bytes_without_interpreting_old_input_formats(self):
        from codeer_cli.delivery import verify
        bundle = self.root / "old-delivery"
        resources = bundle / "runs/historical/inputs/resources.json"
        save_json(resources, {"knowledge": {"opaque-old-shape": "Original old-tool representation"}})
        run = bundle / "runs/historical/run.json"
        save_json(run, {"schema_version": 1, "id": "historical", "status": "passed",
                       "input_files": {str(resources.relative_to(bundle)): hashlib.sha256(resources.read_bytes()).hexdigest()}})
        before = manifest(bundle)
        save_json(bundle / "manifest.json", {"schema_version": 1, "run_path": str(run.relative_to(bundle)),
                                            "release_path": None, "files": before})
        before = manifest(bundle)
        result = verify(bundle)
        self.assertTrue(result["historical"])
        self.assertTrue(result["integrity"])
        self.assertFalse(result["complete"])
        self.assertEqual(manifest(bundle), before)
        resources.write_bytes(resources.read_bytes() + b"\n")
        self.assertFalse(verify(bundle)["integrity"])
