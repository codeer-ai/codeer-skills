"""Review regressions across FAQ recovery, KB import and delivery inputs."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from codeer_cli import resource_exports
from codeer_cli.portable import input_paths, logical_remote
from codeer_cli.project import discover, read_json, save_json, ProjectError
from codeer_cli.delivery import verify, digest
import test_project_resource_exports as fixtures


class ExportReviewTests(unittest.TestCase):
    setUp = fixtures.ResourceExportTests.setUp
    cli = fixtures.ResourceExportTests.cli
    bind = fixtures.ResourceExportTests.bind
    imported = fixtures.ResourceExportTests.imported
    sync = fixtures.ResourceExportTests.sync

    def test_upload_and_reconcile_without_snapshot_in_status(self):
        import os
        for initial_status in ("READY", "PROCESSING"):
            with self.subTest(initial_status=initial_status), tempfile.TemporaryDirectory() as directory:
                previous = Path.cwd()
                try:
                    os.chdir(directory)
                    self.api = fixtures.deployments.PortableAPI()
                    self.api.file_status = initial_status
                    handler = self.api.handler
                    def status_contract(request):
                        response = handler(request)
                        if request.url.path.endswith("/knowledge-bases/files:status"):
                            value = response.json()
                            for row in value["data"]:
                                row.pop("snapshot_object_id", None)
                            return httpx.Response(200, json=value)
                        return response
                    self.api.handler = status_contract
                    self.assertEqual(self.cli("init")[0], 0)
                    self.bind()
                    root = Path(directory)
                    (root / "kb").mkdir()
                    (root / "kb/faq.md").write_text("Synthetic FAQ\n")
                    save_json(root / "resources.json", {"schema_version": 1, "knowledge": {"manual": {"directory": "kb", "glob": "*.md"}}})
                    args = ["kb", "upload", "--local-id", "manual", "--dir", str(root / "kb"), "--glob", "*.md", "--name", "Fixture", "--new", "--poll-timeout", "0"]
                    _, plan = self.cli(*args, "--dry-run")
                    code, result = self.cli(*args, "--expect", plan["token"])
                    self.assertEqual(code, 0 if initial_status == "READY" else 1, self.error)
                    if initial_status != "READY":
                        self.api.file_status = "READY"
                        code, result = self.cli(*args, "--reconcile")
                        self.assertEqual(code, 0, self.error)
                    self.assertEqual(result["status"], "ready")
                    entry = discover().state()["resources"]["kb:manual"]
                    self.assertEqual(entry["original_verification"]["faq.md"]["snapshot_object_id"], 101)
                    self.assertNotIn("snapshot_object_id", entry["base"][0])
                finally:
                    os.chdir(previous)

    def test_bind_without_status_snapshot_still_checks_export_revision(self):
        self.imported()
        handler = self.api.handler
        change = []
        def status_contract(request):
            response = handler(request)
            if request.url.path.endswith("/knowledge-bases/files:status"):
                value = response.json()
                for row in value["data"]:
                    row.pop("snapshot_object_id", None)
                if change:
                    self.api.text = "Changed after original export"
                return httpx.Response(200, json=value)
            return response
        self.api.handler = status_contract
        mapping = self.root / "files.json"
        save_json(mapping, {"001-guide.pdf": "node-faq"})
        args = ["kb", "bind", "--local-id", "manual", "--kb-id", "kb-created", "--files", str(mapping), "--keep-local"]
        _, plan = self.cli(*args, "--dry-run")
        self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 0, self.error)
        before = copy.deepcopy(discover().state()["resources"]["kb:manual"])
        change.append(True)
        _, plan = self.cli(*args, "--dry-run")
        self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 1, self.error)
        self.assertEqual(discover().state()["resources"]["kb:manual"], before)

    def edit_question(self, value):
        path = self.root / "kb/manual-faqs.json"
        bundle = read_json(path)
        next(iter(bundle["files"]["001-guide.pdf"]["faqs"].values()))["question"] = value
        save_json(path, bundle)

    def test_reconcile_preserves_unreviewed_platform_change(self):
        self.imported()
        self.edit_question("Reviewed local")
        args = ["kb", "faq-sync", "--local-id", "manual", "--keep-local", "--apply"]
        _, preview = self.cli(*args, "--dry-run")
        get_export = resource_exports.knowledge
        changed = False
        def on_condition(client, sid, **kwargs):
            nonlocal changed
            if kwargs.get("expected") and not changed:
                self.api.faqs[0]["question"] = "Unreviewed platform"
                changed = True
            return get_export(client, sid, **kwargs)
        with patch.object(resource_exports, "knowledge", side_effect=on_condition):
            self.assertEqual(self.cli(*args, "--expect", preview["token"])[0], 1)
        previous = copy.deepcopy(discover().state()["resources"]["faq:manual"])
        code, recovered = self.cli("kb", "faq-sync", "--local-id", "manual", "--reconcile")
        self.assertEqual(code, 0, self.error)
        self.assertEqual(recovered["status"], "conflict")
        current = discover().state()["resources"]["faq:manual"]
        self.assertEqual(current["base"], previous["base"])
        self.assertEqual(current["local_base"], previous["local_base"])
        self.assertFalse(current.get("decisions"))
        _, plan = self.cli(*args, "--dry-run")
        self.assertEqual(plan["comparison"]["001-guide.pdf"]["state"], "undecided")
        self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 2)
        self.assertEqual(self.api.faqs[0]["question"], "Unreviewed platform")

    def test_batch_refresh_does_not_authorize_other_faq_edits(self):
        self.api.faqs.append({**self.api.faqs[0], "id": 8, "question": "Second baseline"})
        self.imported()
        path = self.root / "kb/manual-faqs.json"
        bundle = read_json(path)
        for lid, faq in bundle["files"]["001-guide.pdf"]["faqs"].items():
            faq["question"] = "Reviewed " + lid
        save_json(path, bundle)
        args = ["kb", "faq-sync", "--local-id", "manual", "--keep-local", "--apply"]
        _, preview = self.cli(*args, "--dry-run")
        handler = self.api.handler
        changed = []
        def concurrent(request):
            result = handler(request)
            if request.method == "PATCH" and not changed:
                sid = int(request.url.path.rsplit("/", 1)[1])
                row = next(f for f in self.api.faqs if f["id"] != sid)
                row["question"] = "Unreviewed platform"
                changed.append(row["id"])
            return result
        self.api.handler = concurrent
        self.assertEqual(self.cli(*args, "--expect", preview["token"])[0], 2)
        self.assertEqual(sum(m == "PATCH" for m, _, _ in self.api.calls), 1)
        self.assertEqual(next(f for f in self.api.faqs if f["id"] == changed[0])["question"], "Unreviewed platform")
        code, recovered = self.cli("kb", "faq-sync", "--local-id", "manual", "--reconcile")
        self.assertEqual(code, 0, self.error)
        self.assertEqual(recovered["status"], "conflict")

    def test_auto_export_symlinks_cannot_leave_content_boundary(self):
        directory = self.root / "sources/exports"
        directory.mkdir()
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / "private.json"
            target.write_text('{"fake_private":"excluded"}')
            (directory / "external.json").symlink_to(target)
            with self.assertRaises(ProjectError):
                input_paths(discover())
        (directory / "external.json").unlink()
        state_file = self.root / ".codeer/hidden.json"
        save_json(state_file, {"not_content": True})
        (directory / "state.json").symlink_to(state_file)
        with self.assertRaises(ProjectError):
            input_paths(discover())

    def test_direct_file_import_has_unique_logical_reference(self):
        args = ["kb", "import", "--local-id", "single", "--kb-id", "node-faq"]
        code, preview = self.cli(*args, "--dry-run")
        self.assertEqual(code, 0, self.error)
        self.assertEqual(self.cli(*args, "--expect", preview["token"])[0], 0, self.error)
        value = logical_remote(discover(), {"unified_tools": [{"type": "tabular_data", "knowledge_node_id": "node-faq"}]})
        self.assertEqual(value["unified_tools"][0]["knowledge_node_id"], "kb:single/001-guide.pdf")

    def test_investigated_create_recovers_after_local_removal(self):
        self.imported()
        path = self.root / "kb/manual-faqs.json"
        bundle = read_json(path)
        bundle["files"]["001-guide.pdf"]["faqs"]["new-faq"] = {"question": "New proposal", "ranges": []}
        save_json(path, bundle)
        self.api.fail_create = True
        args = ["kb", "faq-sync", "--local-id", "manual", "--keep-local", "--apply"]
        _, preview = self.cli(*args, "--dry-run")
        self.assertEqual(self.cli(*args, "--expect", preview["token"])[0], 1)
        bundle["files"]["001-guide.pdf"]["faqs"].pop("new-faq")
        save_json(path, bundle)
        ids = discover().state()["resources"]["faq:manual"]["ids"]
        ids["001-guide.pdf"]["new-faq"] = self.api.faqs[-1]["id"]
        save_json(self.root / "investigated.json", ids)
        count = len(self.api.calls)
        code, recovered = self.cli("kb", "faq-sync", "--local-id", "manual", "--reconcile", "--ids", str(self.root / "investigated.json"))
        self.assertEqual(code, 0, self.error)
        self.assertEqual(recovered["comparison"]["001-guide.pdf"]["state"], "pending_apply")
        self.assertNotIn("new-faq", read_json(path)["files"]["001-guide.pdf"]["faqs"])
        self.assertFalse(any(m != "GET" for m, _, _ in self.api.calls[count:]))

    def test_missing_declared_manifest_is_required_input(self):
        self.imported()
        (self.root / "sources/knowledge/manual/manifest.json").unlink()
        code, result = self.cli("validate")
        self.assertNotEqual(code, 0)
        self.assertIn("manifest", str(result))
        with self.assertRaises(ProjectError):
            input_paths(discover())

    def test_partial_kb_import_keeps_ready_faq_and_resource_reason(self):
        handler = self.api.handler
        def partially_ready(request):
            if request.url.path.endswith("/knowledge-bases/nodes") and request.url.params.get("parent_id") == "kb-created":
                return httpx.Response(200, json={"error_code": 0, "data": [{"id": "node-faq", "node_type": "FILE"}, {"id": "pending-node", "node_type": "FILE"}]})
            if request.url.path.endswith("/pending-node/export"):
                return httpx.Response(404, json={"error_code": 1, "data": {"reason": "not_ready"}})
            return handler(request)
        self.api.handler = partially_ready
        args = ["kb", "import", "--local-id", "partial", "--kb-id", "kb-created"]
        code, preview = self.cli(*args, "--dry-run")
        self.assertEqual(code, 0, self.error)
        code, result = self.cli(*args, "--expect", preview["token"])
        self.assertEqual(code, 0, self.error)
        self.assertFalse(result["original_backup_complete"])
        self.assertEqual(len(result["obtained"]), 1)
        self.assertEqual(discover().state()["resources"]["kb:partial"]["status"], "incomplete")
        self.assertIn("not_ready", str(result["gaps"]))
        self.assertEqual(len(read_json(self.root / "kb/partial-faqs.json")["files"]["001-guide.pdf"]["faqs"]), 1)

    def test_agent_pull_direct_and_covering_folder_references(self):
        for refs in ([{"type": "tabular_data", "knowledge_node_id": "node-faq"}],
                     [{"type": "knowledge_base", "knowledge_node_ids": ["kb-created"]},
                      {"type": "tabular_data", "knowledge_node_id": "node-faq"}]):
            with self.subTest(refs=refs), tempfile.TemporaryDirectory() as directory:
                import os
                previous = Path.cwd()
                try:
                    os.chdir(directory)
                    self.assertEqual(self.cli("init")[0], 0)
                    self.bind()
                    self.api.agent["unified_tools"] = refs
                    self.assertEqual(self.cli("agent", "pull")[0], 0, self.error)
                    local = read_json(Path(directory) / "agent/settings.json")
                    self.assertNotIn("node-faq", str(local))
                    self.assertNotIn("unresolved:", str(local))
                    self.assertEqual(len(read_json(Path(directory) / "resources.json")["knowledge"]), 1)
                finally:
                    os.chdir(previous)

    def test_agent_pull_overlapping_folder_references(self):
        handler = self.api.handler
        def tree(request):
            if request.url.path.endswith("/knowledge-bases/nodes"):
                parent = request.url.params.get("parent_id")
                rows = {"kb-created": [{"id": "nested", "node_type": "FOLDER"}],
                        "nested": [{"id": "node-faq", "node_type": "FILE"}]}
                if parent in rows:
                    return httpx.Response(200, json={"error_code": 0, "data": rows[parent]})
            return handler(request)
        self.api.handler = tree
        self.api.agent["unified_tools"] = [
            {"type": "knowledge_base", "knowledge_node_ids": ["kb-created", "nested"]},
            {"type": "tabular_data", "knowledge_node_id": "node-faq"}]
        self.assertEqual(self.cli("agent", "pull")[0], 0, self.error)
        local = read_json(self.root / "agent/settings.json")
        self.assertNotIn("unresolved:", str(local))
        self.assertNotIn("node-faq", str(local))
        from codeer_cli.portable import translate
        tools = translate(discover(), local)["unified_tools"]
        self.assertEqual(tools[0]["knowledge_node_ids"], ["kb-created", "nested"])
        self.assertEqual(tools[1]["knowledge_node_id"], "node-faq")
        project = discover()
        state = project.state()
        for entry in state["resources"].values():
            entry.pop("file_aliases", None)
        project.save_state(state)
        with self.assertRaisesRegex(ProjectError, "Ambiguous"):
            translate(project, "node-faq", reverse=True)

    def test_known_delete_timeout_reconciles_without_retry(self):
        self.imported()
        path = self.root / "kb/manual-faqs.json"
        data = read_json(path)
        data["files"]["001-guide.pdf"]["faqs"] = {}
        save_json(path, data)
        handler = self.api.handler
        def lost_response(request):
            response = handler(request)
            if request.method == "DELETE":
                raise httpx.ReadTimeout("deleted; response lost", request=request)
            return response
        self.api.handler = lost_response
        args = ["kb", "faq-sync", "--local-id", "manual", "--keep-local", "--apply"]
        _, plan = self.cli(*args, "--dry-run")
        self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 1)
        project = discover()
        receipt_path = self.root / project.state()["resources"]["faq:manual"]["receipt"]
        original = receipt_path.read_bytes()
        report = self.root / "reviews/faq-delete-baseline.md"
        report.parent.mkdir(exist_ok=True)
        report.write_text(digest(original).upper())
        count = len(self.api.calls)
        code, result = self.cli("kb", "faq-sync", "--local-id", "manual", "--reconcile")
        self.assertEqual(code, 0, self.error)
        self.assertEqual(result["status"], "aligned")
        self.assertFalse(any(m != "GET" for m, _, _ in self.api.calls[count:]))
        self.assertEqual(receipt_path.read_bytes(), original)
        current = self.root / project.state()["resources"]["faq:manual"]["receipt"]
        self.assertNotEqual(current, receipt_path)
        self.assertEqual(read_json(current)["provenance"]["original_sha256"], digest(original))

    def test_recovery_refuses_changed_file_mapping(self):
        self.imported()
        self.edit_question("Pending proposal")
        self.api.fail_update = True
        args = ["kb", "faq-sync", "--local-id", "manual", "--keep-local", "--apply"]
        _, plan = self.cli(*args, "--dry-run")
        self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 1)
        project = discover()
        state = project.state()
        state["resources"]["kb:manual"]["file_ids"]["001-guide.pdf"] = "another-node"
        project.save_state(state)
        self.assertEqual(self.cli("kb", "faq-sync", "--local-id", "manual", "--reconcile")[0], 2)
        self.assertIn("file mapping differs", self.error)

    def test_verify_current_bundle_reports_omitted_manifest_reference(self):
        root = self.root / "old-delivery"
        resources = root / "runs/r/inputs/resources.json"
        save_json(resources, {"schema_version": 1, "knowledge": {"manual": {"manifest": "sources/missing.json"}}})
        run = root / "runs/r/run.json"
        save_json(run, {"evidence_contract_version": 2, "input_files": {"runs/r/inputs/resources.json": digest(resources.read_bytes())}})
        save_json(root / "manifest.json", {"schema_version": 1, "run_path": "runs/r/run.json", "files": {"runs/r/run.json": digest(run.read_bytes()), "runs/r/inputs/resources.json": digest(resources.read_bytes())}})
        result = verify(root)
        self.assertFalse(result["complete"])
        self.assertIn("Required declared manifest input missing: sources/missing.json", result["gaps"])
        save_json(resources, {"schema_version": 1, "knowledge": {"manual": {"manifest": "sources/../saved.json"}}})
        saved = root / "runs/r/inputs/saved.json"
        save_json(saved, {"files": {}})
        inputs = {"runs/r/inputs/resources.json": digest(resources.read_bytes()), "runs/r/inputs/saved.json": digest(saved.read_bytes())}
        save_json(run, {"evidence_contract_version": 2, "input_files": inputs})
        save_json(root / "manifest.json", {"schema_version": 1, "run_path": "runs/r/run.json", "files": {"runs/r/run.json": digest(run.read_bytes()), **inputs}})
        self.assertFalse(any("Required declared" in gap for gap in verify(root)["gaps"]))

    def test_manifest_required_for_attachment_and_symlinked_state_directory(self):
        source = self.root / "sources/documents/manual.txt"
        source.write_text("original")
        save_json(self.root / "resources.json", {"schema_version": 1, "attachments": {"manual": {"path": "sources/documents/manual.txt", "manifest": "sources/missing.json"}}})
        self.assertNotEqual(self.cli("validate")[0], 0)
        with self.assertRaises(ProjectError):
            input_paths(discover())
        save_json(self.root / "resources.json", {"schema_version": 1})
        machine = self.root / ".codeer"
        relocated = self.root / "private-machine-state"
        machine.rename(relocated)
        machine.symlink_to(relocated, target_is_directory=True)
        save_json(relocated / "secret.json", {"fake_secret": "not content"})
        exports = self.root / "sources/exports"
        exports.mkdir()
        (exports / "state.json").symlink_to(relocated / "secret.json")
        with self.assertRaises(ProjectError):
            input_paths(discover())
