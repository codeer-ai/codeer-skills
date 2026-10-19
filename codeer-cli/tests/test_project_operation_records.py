import copy
import multiprocessing
import unittest

from codeer_cli.project import discover, read_json, save_json
from codeer_cli.operation_records import recovery_plan
import test_project_deployments as fixtures


def locked_writer(root, connection):
    from pathlib import Path
    from codeer_cli.project_lock import project_lock
    with project_lock(root):
        connection.send("locked")
        connection.recv()
        save_json(Path(root) / ".codeer/keep.json", {"schema_version": 1, "entries": []})
    connection.send("released")


def cli_clean(root, token, connection):
    import contextlib
    import io
    import os
    from codeer_cli.cli import main
    os.chdir(root)
    connection.send("started")
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        result = main(["clean", "--expect", token])
    connection.send(result)


class OperationRecordsTests(unittest.TestCase):
    setUp = fixtures.DeploymentTests.setUp
    cli = fixtures.DeploymentTests.cli
    bind = fixtures.DeploymentTests.bind
    local_agent = fixtures.DeploymentTests.local_agent
    decision = fixtures.DeploymentTests.decision

    def test_large_receipt_reduces_bytes_and_keeps_actual_recovery_inputs(self):
        import json
        self.bind()
        self.local_agent()
        self.decision("--remote")
        (self.root / "agent/instructions.md").write_text("Large updated prompt\n" * 2000)
        _, plan = self.cli("agent", "apply", "--dry-run")
        self.assertEqual(recovery_plan(plan)["payload"], plan["payload"])
        self.assertEqual(self.cli("agent", "apply", "--expect", plan["token"])[0], 0, self.error)
        entry = discover().state()["resources"]["agent"]
        receipt = read_json(self.root / entry["receipt"])
        self.assertEqual(receipt["plan"]["payload"], plan["payload"])
        self.assertEqual(receipt["plan"]["local"], plan["local"])
        self.assertNotIn("comparison", receipt["plan"])
        self.assertEqual(receipt["status"], "applied")
        previous = {**copy.deepcopy(receipt), "plan": plan}
        before = len((json.dumps(previous, ensure_ascii=False, indent=2) + "\n").encode())
        after = (self.root / entry["receipt"]).stat().st_size
        self.assertLess(after, before * 0.9)
        save_json(self.root / "reviews/storage-measurement.json", {"previous_receipt_bytes": before,
                  "current_receipt_bytes": after, "saved_bytes": before - after,
                  "reduction_percent": round((before - after) / before * 100, 2),
                  "method": "Actual CLI preview and completed receipt; same JSON formatting, response and readback"})
        self.artifact = self.root

    def test_unchanged_agent_and_eval_pull_do_not_accumulate_snapshots(self):
        project = self.bind()
        self.local_agent()
        self.assertEqual(self.cli("agent", "pull")[0], 0)
        self.assertEqual(self.cli("eval", "pull")[0], 0)
        before = {str(path): path.read_bytes() for path in (project.local_dir / "imports").rglob("*.json")}
        previous_observation = project.state()["queried_at"]
        for _ in range(3):
            self.assertEqual(self.cli("agent", "pull")[0], 0)
            self.assertEqual(self.cli("eval", "pull")[0], 0)
        self.assertEqual({str(path): path.read_bytes() for path in (project.local_dir / "imports").rglob("*.json")}, before)
        self.assertNotEqual(project.state()["queried_at"], previous_observation)

    def test_small_receipt_and_optional_preview_fields_use_the_same_recovery_reader(self):
        import json
        project = self.bind()
        self.local_agent()
        self.decision("--remote")
        project.path("instructions").write_text("Small reviewed update")
        _, plan = self.cli("agent", "apply", "--dry-run")
        self.assertEqual(self.cli("agent", "apply", "--expect", plan["token"])[0], 0, self.error)
        state = project.state()
        entry = state["resources"]["agent"]
        compact = self.root / entry["receipt"]
        record = read_json(compact)
        expanded = {**record, "plan": plan}
        before = len((json.dumps(expanded, ensure_ascii=False, indent=2) + "\n").encode())
        after = compact.stat().st_size
        self.assertLess(after, before)
        optional = project.local_dir / "receipts/with-optional-diagnostics.json"
        save_json(optional, expanded)
        entry.update(status="outcome_unknown", receipt=str(optional.relative_to(self.root)))
        project.save_state(state)
        self.assertEqual(self.cli("agent", "pull", "--reconcile")[0], 0, self.error)
        self.assertEqual(project.state()["resources"]["agent"]["status"], "imported_unvalidated")
        self.assertEqual(project.path("instructions").read_text(), "Small reviewed update")
        save_json(self.root / "reviews/storage-measurement.json", {"previous_receipt_bytes": before,
                  "current_receipt_bytes": after, "saved_bytes": before - after,
                  "reduction_percent": round((before - after) / before * 100, 2),
                  "optional_preview_fields_recovered_by_same_reader": True})
        self.artifact = self.root

    def test_pinned_unknown_receipt_is_immutable_and_recovery_derives_provenance(self):
        from codeer_cli.sync import reconcile_entry
        project = self.bind()
        path = project.local_dir / "receipts/interrupted.json"
        save_json(path, {"plan": {"resource": "agent", "payload": {"name": "Support"}, "local": {"name": "Support"}}, "status": "outcome_unknown"})
        original = path.read_bytes()
        (self.root / "reviews").mkdir()
        (self.root / "reviews/baseline.md").write_text(str(path.relative_to(self.root)))
        entry = {"receipt": str(path.relative_to(self.root)), "server_id": "a", "status": "outcome_unknown"}
        reconcile_entry(project, entry, {"name": "Support"})
        self.assertEqual(path.read_bytes(), original)
        self.assertNotEqual(entry["receipt"], str(path.relative_to(self.root)))
        derivative = read_json(self.root / entry["receipt"])
        self.assertEqual(derivative["plan"]["payload"], {"name": "Support"})
        self.assertEqual(derivative["provenance"]["original_path"], str(path.relative_to(self.root)))
        self.assertTrue(derivative["reconciliation"]["payload_matches"])

    def test_recovery_rejects_foreign_scope_identity_and_outside_path(self):
        from codeer_cli.sync import reconcile_entry
        from codeer_cli.project import ProjectError
        project = self.bind()
        path = project.local_dir / "receipts/foreign.json"
        scope = {key: project.target[key] for key in ("api_base", "workspace_id", "agent_id")}
        entry = {"receipt": str(path.relative_to(self.root)), "server_id": "a", "status": "outcome_unknown", "scope": scope}
        for foreign_scope, foreign_id in (({**scope, "workspace_id": "another"}, "a"), (scope, "another-id")):
            save_json(path, {"plan": {"resource": "agent", "scope": foreign_scope, "server_id": foreign_id,
                                      "payload": {"name": "Support"}, "local": {"name": "Support"}}, "status": "outcome_unknown"})
            before = copy.deepcopy(entry)
            with self.assertRaises(ProjectError):
                reconcile_entry(project, entry, {"name": "Support"})
            self.assertEqual(entry, before)
        entry["receipt"] = "../outside.json"
        with self.assertRaises(ProjectError):
            reconcile_entry(project, entry, {"name": "Support"})

    def test_pinned_receipt_references_share_cleanup_rules_and_preserve_bytes(self):
        import hashlib
        import json
        from urllib.parse import quote
        from codeer_cli.clean import preview
        from codeer_cli.sync import reconcile_entry
        project = self.bind()
        reports = self.root / "reviews"
        reports.mkdir()
        for kind, suffix in (("uppercase", ".md"), ("encoded", ".md"), ("relative", ".md"),
                             ("escaped-json", ".json"), ("jsonl", ".jsonl")):
            with self.subTest(kind=kind):
                actual = {"name": kind}
                plan = {"resource": "agent", "payload": actual, "local": actual, "scope": project.target, "token": kind}
                path = project.local_dir / f"receipts/{kind} evidence.json"
                save_json(path, {"plan": plan, "status": "applied"})
                raw = path.read_bytes()
                name = str(path.relative_to(self.root))
                digest = hashlib.sha256(raw).hexdigest()
                content = {"uppercase": digest.upper(), "encoded": f"[proof]({quote(name)})",
                           "relative": f"[proof](../{name})",
                           "escaped-json": json.dumps({"receipt": name}).replace(".codeer", "\\u002ecodeer"),
                           "jsonl": json.dumps({"sha256": digest.upper()}) + "\n"}[kind]
                (reports / (kind + suffix)).write_text(content)
                self.assertNotIn(name, {row["path"] for row in preview(project)["candidates"]})
                entry = {"receipt": name, "server_id": "a", "status": "outcome_unknown"}
                reconcile_entry(project, entry, actual)
                self.assertEqual(path.read_bytes(), raw)
                self.assertNotEqual(entry["receipt"], name)
                derivative = read_json(self.root / entry["receipt"])
                self.assertEqual(derivative["provenance"], {"original_path": name, "original_sha256": digest})
                self.assertEqual(derivative["plan"], plan)
                derived = entry["receipt"]
                entry["status"] = "outcome_unknown"
                reconcile_entry(project, entry, actual)
                self.assertEqual(entry["receipt"], derived)
                self.assertEqual(path.read_bytes(), raw)
                self.assertEqual(read_json(self.root / derived)["provenance"], derivative["provenance"])

    def test_cleanup_waits_for_writer_then_revalidates_roots(self):
        self.bind()
        _, plan = self.cli("clean", "--dry-run")
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe()
        writer = context.Process(target=locked_writer, args=(str(self.root), child))
        writer.start()
        self.addCleanup(lambda: writer.terminate() if writer.is_alive() else None)
        self.assertTrue(parent.poll(5))
        self.assertEqual(parent.recv(), "locked")
        result, worker = context.Pipe()
        cleaner = context.Process(target=cli_clean, args=(str(self.root), plan["token"], worker))
        cleaner.start()
        self.addCleanup(lambda: cleaner.terminate() if cleaner.is_alive() else None)
        self.assertTrue(result.poll(5))
        self.assertEqual(result.recv(), "started")
        self.assertFalse(result.poll(0.2), "cleanup completed while the writer still held the lock")
        parent.send("finish")
        self.assertTrue(result.poll(5))
        self.assertEqual(result.recv(), 2, "new root must invalidate the old cleanup token after taking the lock")
        writer.join(5)
        cleaner.join(5)
        self.assertEqual(writer.exitcode, 0)
        self.assertEqual(cleaner.exitcode, 0)

    def test_interrupted_writer_releases_os_lock(self):
        project = self.bind()
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe()
        writer = context.Process(target=locked_writer, args=(str(self.root), child))
        writer.start()
        self.addCleanup(lambda: writer.terminate() if writer.is_alive() else None)
        self.assertTrue(parent.poll(5))
        self.assertEqual(parent.recv(), "locked")
        writer.terminate()
        writer.join(5)
        from codeer_cli.project_lock import project_lock
        with project_lock(project.root):
            self.assertEqual(self.cli("clean", "--dry-run")[0], 0)
