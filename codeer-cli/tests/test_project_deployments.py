"""Portable deployment contracts, tested through CLI and HTTP MockTransport."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import httpx

from codeer_cli.cli import main
from codeer_cli.deployment import adoption_plan, adopt
from codeer_cli.project import discover, read_json, save_json, ProjectError
from codeer_cli.project_agent import canonical, writable
from codeer_cli.project_attachments import download
from test_project_sync import API


class PortableAPI(API):
    def __init__(self):
        super().__init__()
        self.agent.update(attachment_ids=[], primary_object_ids=[])
        self.upload_bytes = None
        self.upload_fail = False
        self.kb_text = {"node-faq": "Synthetic FAQ\n"}
        self.kb_faqs = []
        self.base_url = "https://fixture.invalid"
        self.attachment_id = "attachment-remote"
        self.fail_agent_get = False
        self.delete_timeout = False

    def client(self):
        value = super().client()
        value._client.close()
        value.base_url = self.base_url
        value._client = httpx.Client(base_url=value.base_url, headers={"x-api-key": value.api_key}, transport=httpx.MockTransport(self.handler))
        return value

    def handler(self, request):
        path = request.url.path.removeprefix("/api/v1")
        if path == "/external/agents/a" and request.method == "GET" and self.fail_agent_get:
            raise httpx.ReadTimeout("readback interrupted", request=request)
        if path.startswith("/external/eval/cases/") and request.method == "DELETE":
            sid = path.rsplit("/", 1)[1]
            self.cases.pop(sid, None)
            self.calls.append((request.method, path, None))
            if self.delete_timeout:
                raise httpx.ReadTimeout("delete committed, response lost", request=request)
            return httpx.Response(200, json={"data": {}, "error_code": 0})
        if path == "/external/files":
            self.calls.append((request.method, path, None))
            if self.upload_fail:
                raise httpx.ReadTimeout("unknown upload", request=request)
            self.upload_bytes = request.content
            return httpx.Response(200, json={"data": {"uuid": self.attachment_id, "file_url": "https://storage.invalid/original.pdf"}, "error_code": 0})
        if path == "/llm/models":
            return httpx.Response(200, json={"data": [{"model_id": "model-available"}], "error_code": 0})
        result = None
        if path == "/external/knowledge-bases/files:status":
            result = [{"node_id": sid, "status": self.file_status, "snapshot_object_id": 101} for sid in json.loads(request.content)["node_ids"]]
        elif path.startswith("/external/knowledge-bases/files/") and not path.endswith(("/content", "/download", "/export")):
            sid = path.rsplit("/", 1)[1]
            content = self.kb_text[sid].encode()
            result = {"node_id": sid, "snapshot_object_id": 101, "stored_file": {"available": True, "size_bytes": len(content), "sha256": None, "provenance": "uploaded_original", "revision": "file-v1"}}
        elif path == "/external/knowledge-bases/nodes" and request.method == "POST":
            result = {"id": "kb-created"}
        elif path == "/external/knowledge-bases/files:upload":
            self.upload_bytes = request.content
            result = {"nodes": [{"node_id": "node-faq", "original_name": "faq.md"}]}
        elif path == "/external/knowledge-bases/nodes" and request.url.params.get("parent_id") == "kb-created":
            result = [{"id": "node-faq", "name": "faq.md", "node_type": "FILE"}]
        elif path.startswith("/external/knowledge-bases/files/") and path.endswith("/content"):
            sid = path.split("/")[-2]
            result = {"node_id": sid, "status": "READY", "content": self.kb_text[sid]}
        elif path.startswith("/external/knowledge-bases/files/") and path.endswith("/export"):
            sid = path.split("/")[-2]
            from codeer_cli.project import fingerprint
            content = self.kb_text[sid]
            metadata = {"node_id": sid, "snapshot_object_id": 101, "status": "READY", "name": "faq.md",
                        "stored_file": {"available": True, "size_bytes": len(content.encode()), "sha256": None,
                                        "provenance": "uploaded_original", "filename": "faq.md", "revision": "file-v1"}}
            result = {"metadata": metadata, "snapshot": {"snapshot_object_id": 101, "content": content, "content_revision": fingerprint(content)},
                      "faqs": self.kb_faqs, "export_revision": fingerprint([content, self.kb_faqs])}
            if request.url.params.get("expected_export_revision", result["export_revision"]) != result["export_revision"]:
                return httpx.Response(409, json={"error_code": 1, "data": {"reason": "resource_changed"}})
        elif path.startswith("/external/knowledge-bases/files/") and path.endswith("/download"):
            sid = path.split("/")[-2]
            return httpx.Response(200, content=self.kb_text[sid].encode(), headers={"X-Codeer-Snapshot-Object-Id": "101"})
        elif path == "/external/context-object-faqs" and request.method == "POST":
            result = {"id": len(self.kb_faqs) + 1, **json.loads(request.content)}
            self.kb_faqs.append(result)
        if result is not None:
            self.calls.append((request.method, path, None))
            return httpx.Response(200, json={"data": result, "error_code": 0})
        return super().handler(request)


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        previous = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, previous)
        self.api = PortableAPI()
        self.addCleanup(patch.stopall)
        patch("codeer_cli.commands.profile.resolve_profile", return_value={"name": "fixture", "source": "fixture", "api_key": "synthetic"}).start()
        patch.dict(os.environ, {}, clear=True).start()
        self.assertEqual(self.cli("init")[0], 0)

    def cli(self, *args):
        output, error = io.StringIO(), io.StringIO()
        with patch("codeer_cli.cli.CodeerClient.from_env", side_effect=self.api.client), contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            code = main(list(args))
        self.error = error.getvalue()
        return code, json.loads(output.getvalue()) if output.getvalue() else None

    def bind(self, alias="dev", new=False):
        self.assertEqual(self.cli("agent", "bind", "--alias", alias, *( ["--new"] if new else ["--agent", "a"]))[0], 0, self.error)
        self.assertEqual(self.cli("agent", "use", alias)[0], 0)
        return discover()

    def local_agent(self, **changes):
        data = canonical(writable(self.api.agent))
        data.update(changes)
        prompt = data.pop("system_prompt")
        save_json(self.root / "agent/settings.json", data)
        (self.root / "agent/instructions.md").write_text(prompt)

    def decision(self, choice, fields=None):
        args = ["agent", "adopt", "--resource", "agent", choice]
        if fields:
            args += ["--fields", fields]
        code, plan = self.cli(*args, "--dry-run")
        self.assertEqual(code, 0, self.error)
        code, result = self.cli(*args, "--expect", plan["token"])
        self.assertEqual(code, 0, self.error)
        return result

    def test_offline_content_identity_and_isolated_deployment_selection(self):
        self.assertEqual(discover().config["schema_version"], 2)
        self.assertNotIn("target", discover().config)
        self.assertEqual(self.cli("status")[0], 0)
        before = discover().revision()
        dev = self.bind()
        self.assertEqual(before, dev.revision())
        dev.save_state({"resources": {"agent": {"server_id": "a"}}})
        prod = self.bind("prod")
        self.assertEqual(prod.state()["resources"], {})
        self.assertEqual(prod.revision(), before)
        self.assertEqual(self.cli("--deployment", "dev", "status")[1]["resources"]["agent"]["server_id"], "a")
        nested = self.root / "sources/documents"
        os.chdir(nested)
        self.assertEqual(discover().root, self.root)
        self.assertEqual(discover().deployment, "prod")
        self.assertEqual(self.cli("--deployment", "dev", "agent", "get", "other")[0], 2)

    def test_takeover_30_14_keeps_proposal_until_successful_readback(self):
        project = self.bind()
        remote = copy.deepcopy(self.api.agent["human_handoff"])
        self.api.agent["human_handoff"] = {**remote, "idle_timeout_minutes": 14}
        self.local_agent(human_handoff={**remote, "idle_timeout_minutes": 30})
        self.assertEqual(self.cli("agent", "pull")[0], 0)
        entry = discover().state()["resources"]["agent"]
        self.assertNotIn("base", entry)
        self.assertTrue(self.cli("agent", "apply", "--dry-run")[1]["conflicts"])
        result = self.decision("--keep-local")
        self.assertEqual(result["comparison"]["human_handoff"]["state"], "pending_apply")
        entry = discover().state()["resources"]["agent"]
        self.assertNotIn("human_handoff", entry["base"])
        _, plan = self.cli("agent", "apply", "--dry-run")
        self.assertEqual(plan["payload"]["human_handoff"]["idle_timeout_minutes"], 30)
        self.assertEqual(self.cli("agent", "apply", "--expect", plan["token"])[0], 0, self.error)
        self.assertEqual(self.api.agent["human_handoff"]["idle_timeout_minutes"], 30)
        self.assertEqual(project.state()["resources"]["agent"]["base"]["human_handoff"]["idle_timeout_minutes"], 30)
        self.assertFalse(self.cli("agent", "apply", "--dry-run")[1]["changed"])

    def test_partial_adoption_preserves_conflict_and_never_mutates_remote(self):
        self.bind()
        self.local_agent(system_prompt="Local proposal", description="Local description")
        self.api.agent.update(system_prompt="Platform proposal", description="Platform description")
        before = sum(method != "GET" for method, _, _ in self.api.calls)
        result = self.decision("--remote", "description")
        self.assertEqual(result["comparison"]["description"]["state"], "aligned")
        self.assertEqual(result["comparison"]["system_prompt"]["state"], "undecided")
        self.assertEqual((self.root / "agent/instructions.md").read_text(), "Local proposal")
        _, plan = self.cli("agent", "apply", "--dry-run")
        self.assertIn("system_prompt", plan["conflicts"])
        self.assertEqual(self.cli("agent", "apply", "--expect", plan["token"])[0], 2)
        self.decision("--remote", "system_prompt")
        self.assertEqual((self.root / "agent/instructions.md").read_text(), "Platform proposal")
        self.assertEqual(sum(method != "GET" for method, _, _ in self.api.calls), before)
        self.assertFalse(self.cli("agent", "apply", "--dry-run")[1]["changed"])

    def test_stale_decision_and_local_write_failure_do_not_advance_bases(self):
        project = self.bind()
        self.local_agent(system_prompt="Local")
        with self.api.client() as client:
            plan = adoption_plan(project, client, "agent", fields=["system_prompt"], choice="remote")
            old = copy.deepcopy(project.state())
            with patch("codeer_cli.deployment.save_json", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    adopt(project, client, plan, plan["token"])
            self.assertEqual(project.state(), old)
            self.assertEqual((self.root / "agent/instructions.md").read_text(), "Local")
            self.api.agent["system_prompt"] = "Changed after preview"
            with self.assertRaisesRegex(ProjectError, "stale"):
                adopt(project, client, plan, plan["token"])

    def test_created_agent_unbound_receipt_adopts_only_the_exact_bound_identity(self):
        project = self.bind()
        self.local_agent(llm_model="old-model")
        with self.api.client() as client:
            scope = project.check_scope(client)
            state = project.state()
            entry = {"server_id": "a", "scope": {**scope, "agent_id": None}, "status": "applied"}
            state["resources"]["agent"] = copy.deepcopy(entry)
            project.save_state(state)
            plan = adoption_plan(project, client, "agent", fields=["llm_model"], choice="remote")
            before_prompt = (self.root / "agent/instructions.md").read_bytes()
            calls_before = len(self.api.calls)
            result = adopt(project, client, plan, plan["token"])
            self.assertEqual(result["remote_mutations"], 0)
            self.assertEqual((self.root / "agent/instructions.md").read_bytes(), before_prompt)
            self.assertFalse(any(method in ("POST", "PATCH", "DELETE") for method, _, _ in self.api.calls[calls_before:]))
            for change in ({"server_id": "foreign-agent"}, {"scope": {**scope, "agent_id": "foreign-agent"}}, {"scope": {**scope, "agent_id": None, "workspace_id": "foreign-workspace"}}, {"scope": {**scope, "agent_id": None, "api_base": "https://foreign.invalid"}}):
                with self.subTest(change=change):
                    state = project.state()
                    state["resources"]["agent"] = {**copy.deepcopy(entry), **change}
                    project.save_state(state)
                    with self.assertRaisesRegex(ProjectError, "scope mismatch"):
                        adoption_plan(project, client, "agent", fields=["llm_model"], choice="remote")

    def test_unknown_agent_write_reconciles_only_matching_payload(self):
        self.bind(new=True)
        self.local_agent()
        _, plan = self.cli("agent", "apply", "--dry-run")
        original_client = self.api.client
        def conflicting_client():
            client = original_client()
            client.agent_id = "foreign-agent"
            return client
        with patch.object(self.api, "client", side_effect=conflicting_client):
            self.assertEqual(self.cli("agent", "apply", "--expect", plan["token"])[0], 2)
        self.assertFalse(any(method == "POST" and path == "/external/agents" for method, path, _ in self.api.calls))
        self.api.fail_write = True
        self.assertEqual(self.cli("agent", "apply", "--expect", plan["token"])[0], 1)
        self.api.fail_write = False
        self.assertIn("unreconciled_previous_operation", self.cli("agent", "apply", "--dry-run")[1]["conflicts"])
        self.assertEqual(discover().state()["resources"]["agent"]["status"], "outcome_unknown")

    def test_known_create_identity_can_reconcile_without_losing_a_newer_proposal(self):
        self.bind(new=True)
        self.local_agent()
        _, plan = self.cli("agent", "apply", "--dry-run")
        self.api.fail_agent_get = True
        self.assertEqual(self.cli("agent", "apply", "--expect", plan["token"])[0], 1)
        self.assertEqual(discover().state()["resources"]["agent"]["server_id"], "a")
        self.api.fail_agent_get = False
        (self.root / "agent/instructions.md").write_text("Newer unsent proposal")
        self.assertEqual(self.cli("agent", "pull", "--agent", "a", "--reconcile")[0], 0, self.error)
        self.assertEqual(discover().target["agent_id"], "a")
        self.assertEqual((self.root / "agent/instructions.md").read_text(), "Newer unsent proposal")
        self.assertEqual(sum(m == "POST" and p == "/external/agents" for m, p, _ in self.api.calls), 1)
        _, current = self.cli("agent", "apply", "--dry-run")
        self.assertFalse(current["conflicts"])
        self.assertEqual(current["payload"]["system_prompt"], "Newer unsent proposal")

    def test_attachment_bytes_two_deployments_and_unknown_upload_guard(self):
        original = self.root / "sources/documents/manual.pdf"
        content = b"%PDF-1.7 synthetic original\x00\xff"
        original.write_bytes(content)
        save_json(self.root / "resources.json", {"schema_version": 1, "attachments": {"manual": {"path": "sources/documents/manual.pdf"}}})
        revision = discover().revision()
        for alias in ("dev", "prod"):
            self.bind(alias, new=True)
            args = ["agent", "attachment", "--local-id", "manual"]
            _, plan = self.cli(*args, "--dry-run")
            with patch("codeer_cli.project_attachments.download", return_value=content):
                self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 0, self.error)
            self.assertIn(content, self.api.upload_bytes)
            self.local_agent(attachment_ids=["attachment:manual"])
            code, create = self.cli("agent", "apply", "--dry-run")
            self.assertEqual(code, 0, self.error)
            self.assertEqual(create["payload"]["attachment_ids"], ["attachment:manual"])
            self.assertEqual(self.cli("agent", "apply", "--expect", create["token"])[0], 0, self.error)
            self.assertEqual(self.api.agent["attachment_ids"], ["attachment-remote"])
        self.assertEqual(discover().select("dev").revision(), discover().select("prod").revision())
        self.assertNotEqual(discover().revision(), revision)  # Agent definition was added.
        self.bind("unknown", new=True)
        _, plan = self.cli(*args, "--dry-run")
        self.api.upload_fail = True
        self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 1)
        count = len(self.api.calls)
        self.api.upload_fail = False
        self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 2)
        self.assertFalse(any(path == "/external/files" for _, path, _ in self.api.calls[count:]))

    def test_pinned_attachment_recovery_preserves_uppercase_hash_source(self):
        import hashlib
        project = self.bind(new=True)
        content = b"Synthetic original attachment"
        (self.root / "sources/documents/manual.pdf").write_bytes(content)
        save_json(self.root / "resources.json", {"schema_version": 1, "attachments": {"manual": {"path": "sources/documents/manual.pdf"}}})
        args = ["agent", "attachment", "--local-id", "manual"]
        _, preview = self.cli(*args, "--dry-run")
        with patch("codeer_cli.project_attachments.download", side_effect=ProjectError("readback interrupted")):
            self.assertEqual(self.cli(*args, "--expect", preview["token"])[0], 2)
        entry = project.state()["resources"]["attachment:manual"]
        path = self.root / entry["receipt"]
        original = path.read_bytes()
        report = self.root / "reviews/attachment-baseline.md"
        report.parent.mkdir(exist_ok=True)
        report.write_text(hashlib.sha256(original).hexdigest().upper())
        uploads = len(self.api.upload_bytes)
        with patch("codeer_cli.project_attachments.download", return_value=content):
            self.assertEqual(self.cli(*args, "--reconcile")[0], 0, self.error)
        current = project.state()["resources"]["attachment:manual"]
        self.assertEqual(current["status"], "ready")
        self.assertEqual(path.read_bytes(), original)
        self.assertNotEqual(current["receipt"], entry["receipt"])
        self.assertEqual(read_json(self.root / current["receipt"])["provenance"]["original_sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(len(self.api.upload_bytes), uploads)

    def test_clone_attachment_takeover_verifies_explicit_identity_without_upload(self):
        self.bind()
        content = b"original-file-bytes"
        (self.root / "sources/documents/manual.pdf").write_bytes(content)
        save_json(self.root / "resources.json", {"schema_version": 1, "attachments": {"manual": {"path": "sources/documents/manual.pdf"}}})
        self.api.agent["attachment_ids"] = ["existing-file"]
        self.api.agent["attachments"] = [{"id": "existing-file", "original_name": "manual.pdf", "size": len(content), "source_url": "https://storage.invalid/original", "attachment_type": "file"}]
        args = ["agent", "attachment", "--local-id", "manual"]
        self.assertEqual(self.cli(*args, "--dry-run")[0], 2)
        with patch("codeer_cli.project_attachments.download", return_value=content):
            code, plan = self.cli(*args, "--remote-id", "existing-file", "--dry-run")
            self.assertEqual(code, 0, self.error)
            self.assertEqual(self.cli(*args, "--remote-id", "existing-file", "--expect", plan["token"])[0], 0, self.error)
        self.assertEqual(discover().state()["resources"]["attachment:manual"]["server_id"], "existing-file")
        self.local_agent(attachment_ids=["attachment:manual"])
        self.assertEqual(self.decision("--remote")["comparison"]["attachment_ids"]["state"], "aligned")
        self.assertFalse(any(path == "/external/files" for _, path, _ in self.api.calls))

    def test_download_integrity_and_import_gaps(self):
        metadata = {"attachment_id": "x", "stored_file": {"available": True, "revision": "v1", "size_bytes": 8}}
        transport = httpx.MockTransport(lambda request: httpx.Response(200, content=b"original", headers={"X-Codeer-Content-Revision": "v1"})
                                        if request.url.path.endswith("/download") else httpx.Response(200, json={"data": metadata, "error_code": 0}))
        with self.api.client() as client:
            client._client.close()
            client._client = httpx.Client(base_url=client.base_url, transport=transport)
            self.assertEqual(download(client, "x", 8), b"original")
            with self.assertRaises(ProjectError):
                download(client, "x", 9)
        self.bind()
        self.api.agent["attachment_ids"] = ["missing-original"]
        self.assertEqual(self.cli("agent", "pull")[0], 0)
        self.assertIn("unresolved:attachment:", (self.root / "agent/settings.json").read_text())
        self.assertEqual(self.cli("agent", "apply", "--dry-run")[0], 2)

    def test_original_import_records_downloaded_bytes_and_expired_reference_gaps(self):
        self.bind()
        self.api.agent["attachment_ids"] = ["available", "expired"]
        self.api.agent["attachments"] = [{"id": sid, "original_name": sid + ".pdf", "size": 8,
                                           "source_url": "https://storage.invalid/" + sid, "attachment_type": "file"} for sid in ("available", "expired")]
        def fetched(client, sid, **kwargs):
            if sid == "expired":
                raise ProjectError("Original download unavailable (403)")
            kwargs["record"].update(provenance="uploaded_original")
            return b"original"
        with patch("codeer_cli.project_attachments.download", side_effect=fetched):
            code, imported = self.cli("agent", "pull")
        self.assertEqual(code, 0, self.error)
        self.assertEqual(len(imported["originals"]["obtained"]), 1)
        self.assertEqual(len(imported["originals"]["gaps"]), 1)
        original_path = self.root / imported["originals"]["obtained"][0]
        self.assertEqual(original_path.read_bytes(), b"original")
        self.assertFalse(imported["accepted"])
        self.assertEqual(self.cli("agent", "apply", "--dry-run")[0], 2)
        from codeer_cli.project_attachments import import_originals
        with patch("codeer_cli.resource_exports.attachment", side_effect=ProjectError("Stored original unavailable")):
            with self.api.client() as client:
                result = import_originals(discover(), client, {"attachments": [{"id": "context", "source_url": "https://service.invalid/page", "attachment_type": "context_object"}]})
        self.assertFalse(result["obtained"])
        self.assertTrue(result["gaps"])

    def test_subagent_import_preserves_reference_and_blocks_project_write(self):
        self.bind()
        self.api.agent["unified_tools"] = [{"id": "delegate", "type": "agent", "agent_id": "child-remote"}]
        self.assertEqual(self.cli("agent", "pull")[0], 0)
        self.assertEqual(read_json(self.root / "agent/settings.json")["unified_tools"][0]["agent_id"], "child-remote")
        self.assertEqual(self.cli("agent", "apply", "--dry-run")[0], 2)
        self.assertIn("Sub-Agent", self.error)
        self.assertFalse(any(m in ("POST", "PATCH", "PUT", "DELETE") for m, _, _ in self.api.calls))

    def test_git_clone_contains_originals_and_definitions_but_no_state(self):
        repository = self.root.parent / (self.root.name + "-support-agents")
        self.addCleanup(shutil.rmtree, repository, True)
        repository.mkdir()
        (repository / "README.md").write_text("# Support agents\n\n- [Support](projects/support/README.md)\n")
        (repository / "AGENTS.md").write_text("Keep sources; coordinate production writes.\n")
        (repository / ".gitignore").write_text("# Shared repository rules\n.codeer/\n")
        (repository / ".codeer").mkdir()
        (repository / ".codeer/profile").write_text("fixture-parent\n")
        project_root = repository / "projects/support"
        self.assertEqual(self.cli("init", str(project_root))[0], 0)
        self.root = project_root
        os.chdir(project_root)
        self.bind()
        self.local_agent()
        (self.root / "sources/documents/manual.pdf").write_bytes(b"original-pdf")
        (self.root / "sources/history/private").mkdir(parents=True)
        (self.root / "sources/history/private/raw.json").write_text("private")
        (self.root / "runs/trial").mkdir(parents=True)
        (self.root / "runs/trial/run.json").write_text("private")
        (self.root / "releases").mkdir()
        (self.root / "releases/trial.json").write_text("private")
        def git(*args):
            return subprocess.run(["git", *args], cwd=repository, check=True, capture_output=True, text=True).stdout
        git("init", "-q")
        ignored = git("check-ignore", ".codeer/profile", "projects/support/.codeer/deployment", "projects/support/runs/trial/run.json", "projects/support/releases/trial.json", "projects/support/sources/history/private/raw.json")
        self.assertEqual(len(ignored.splitlines()), 5)
        git("add", ".")
        tracked = git("diff", "--cached", "--name-only").splitlines()
        self.assertIn("projects/support/sources/documents/manual.pdf", tracked)
        self.assertTrue(any(p.startswith("projects/support/logs/") for p in tracked))
        self.assertFalse((repository / "project.toml").exists())
        self.assertEqual((repository / ".gitignore").read_text(), "# Shared repository rules\n.codeer/\n")
        git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Synthetic portable project")
        clone = repository.parent / (repository.name + "-clone")
        self.addCleanup(shutil.rmtree, clone, True)
        git("clone", "-q", str(repository), str(clone))
        self.assertFalse((clone / ".codeer").exists())
        self.assertEqual((clone / "projects/support/sources/documents/manual.pdf").read_bytes(), b"original-pdf")
        os.chdir(clone / "projects/support")
        self.assertEqual(self.cli("status")[0], 0)
        self.assertEqual(self.cli("agent", "apply", "--dry-run")[0], 2)

    def test_kb_takeover_requires_explicit_ids_and_text_adoption_keeps_originals(self):
        self.bind()
        (self.root / "kb").mkdir()
        (self.root / "kb/faq.md").write_text("Local FAQ proposal\n")
        original = self.root / "sources/documents/original.pdf"
        original.write_bytes(b"original-pdf")
        save_json(self.root / "resources.json", {"schema_version": 1, "knowledge": {"faq": {"directory": "kb", "glob": "*.md"}}})
        mapping = self.root / "mapping.json"
        save_json(mapping, {"faq.md": "wrong-node"})
        args = ["kb", "bind", "--local-id", "faq", "--kb-id", "kb-created", "--files", str(mapping), "--remote-text"]
        self.assertEqual(self.cli(*args, "--dry-run")[0], 2)
        save_json(mapping, {"faq.md": "node-faq"})
        _, plan = self.cli(*args, "--dry-run")
        count = len(self.api.calls)
        self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 0, self.error)
        self.assertEqual((self.root / "kb/faq.md").read_text(), "Synthetic FAQ\n")
        self.assertEqual(original.read_bytes(), b"original-pdf")
        self.assertFalse(any(method != "GET" and not path.endswith(":status") for method, path, _ in self.api.calls[count:]))

    def test_profile_is_not_mapping_identity_but_changes_invalidate_preview(self):
        self.bind()
        self.local_agent()
        self.decision("--remote")
        (self.root / "agent/instructions.md").write_text("Reviewed local revision")
        revision = discover().revision()
        _, old = self.cli("agent", "apply", "--dry-run")
        with patch("codeer_cli.commands.profile.resolve_profile", return_value={"name": "another-operator", "source": "fixture"}):
            self.assertEqual(self.cli("agent", "apply", "--expect", old["token"])[0], 2)
            code, current = self.cli("agent", "apply", "--dry-run")
            self.assertEqual(code, 0, self.error)
            self.assertNotEqual(current["token"], old["token"])
            self.assertEqual(self.cli("agent", "apply", "--expect", current["token"])[0], 0, self.error)
        self.assertEqual(discover().revision(), revision)
        self.assertNotIn("profile", discover().state()["resources"]["agent"]["scope"])

    def test_two_projects_never_inherit_parent_deployment_state(self):
        self.bind()
        child = self.root / "projects/separate"
        self.assertEqual(self.cli("init", str(child))[0], 0)
        os.chdir(child / "sources/documents")
        project = discover()
        self.assertEqual(project.root, child)
        self.assertIsNone(project.deployment)
        self.assertEqual(project.state()["resources"], {})
        self.assertEqual(project.target, {})

    def test_unsupported_project_is_rejected_before_http_without_changing_unknown_operation(self):
        manifest = self.root / "project.toml"
        original = 'schema_version = 1\nname = "Legacy"\n\n[target]\nagent_id = "a" # retain identity\napi_base = "https://fixture.invalid"\nworkspace_id = "w"\n\n[paths]\n# retain path comment\n'
        manifest.write_text(original)
        receipt = {"id": "old", "plan": {"local": {"description": "old proposal"}}, "status": "outcome_unknown"}
        save_json(self.root / ".codeer/receipts/old.json", receipt)
        state = {"schema_version": 1, "resources": {"agent": {"server_id": "a", "status": "outcome_unknown", "receipt": ".codeer/receipts/old.json", "base": {"description": "old base"}}}}
        save_json(self.root / ".codeer/state.json", state)
        calls = len(self.api.calls)
        self.assertEqual(self.cli("status")[0], 2)
        self.assertEqual(self.cli("agent", "apply", "--dry-run")[0], 2)
        self.assertEqual(len(self.api.calls), calls)
        self.assertEqual(manifest.read_text(), original)
        self.assertEqual(read_json(self.root / ".codeer/state.json"), state)
        self.assertEqual(read_json(self.root / ".codeer/receipts/old.json"), receipt)
        self.assertIn("# retain path comment", manifest.read_text())

    def test_remote_deleted_case_requires_explicit_local_retirement(self):
        from test_project_eval import design_fixture
        project = self.bind()
        design = design_fixture()
        save_json(project.path("evals"), design)
        with self.api.client() as client:
            scope = project.check_scope(client)
        project.save_state({"resources": {"case:handoff": {"server_id": "c1", "scope": scope, "status": "tracked"}, "pairs:handoff": {"server_id": "c1"}}})
        args = ["agent", "adopt", "--resource", "case:handoff", "--remote"]
        _, plan = self.cli(*args, "--dry-run")
        self.assertIsNone(plan["remote"])
        self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 0, self.error)
        self.assertEqual(project.state()["resources"]["case:handoff"]["status"], "retired")
        self.assertEqual([c["local_id"] for c in read_json(project.path("evals"))["cases"]], ["hours"])
        self.assertFalse(any(method in ("PUT", "PATCH", "DELETE") for method, _, _ in self.api.calls))

    def test_case_delete_unknown_receipt_stays_in_deployment_and_reconciles_without_retry(self):
        from test_project_eval import design_fixture
        project = self.bind()
        save_json(project.path("evals"), design_fixture())
        self.api.cases["c1"] = {"id": "c1", "agent_id": "a", "input": "Human please", "expected_output": "", "attachment_ids": [], "label_ids": []}
        with self.api.client() as client:
            scope = project.check_scope(client)
        project.save_state({"resources": {"case:handoff": {"server_id": "c1", "scope": scope, "status": "tracked"}}})
        args = ["eval", "case-delete", "--case", "c1"]
        _, plan = self.cli(*args, "--dry-run")
        self.api.delete_timeout = True
        self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 1)
        entry = project.state()["resources"]["case:handoff"]
        self.assertIn(".codeer/deployments/dev/receipts/", entry["delete_receipt"])
        self.assertEqual(entry["status"], "outcome_unknown")
        self.assertEqual(self.cli("eval", "pull", "--reconcile")[0], 0, self.error)
        self.assertEqual(project.state()["resources"]["case:handoff"]["status"], "retired")
        self.assertEqual(sum(method == "DELETE" for method, _, _ in self.api.calls), 1)

    def test_clone_eval_maps_shared_tester_cases_and_pairs_by_identity(self):
        from test_project_eval import design_fixture
        from codeer_cli.project_eval import CASE_FIELDS, TESTER_FIELDS, select
        project = self.bind()
        design = design_fixture()
        design["testers"][0]["judge_llm_model_id"] = "model-available"
        design["cases"][0].pop("attachment_ids")
        design["cases"][0].pop("label_ids")
        self.api.testers["t1"] = {"id": "t1", **select(design["testers"][0], TESTER_FIELDS)}
        for sid, row in zip(("c1", "c2"), design["cases"]):
            self.api.cases[sid] = {"id": sid, "agent_id": "a", **select(row, CASE_FIELDS)}
            self.api.pairs[sid] = [{"evaluator_id": "t1", "rubric": row["pairs"][0]["rubric"]}]
        design["cases"][0]["input"] = "Local pending wording"
        (self.root / "sources/documents/sop.md").write_text("Synthetic SOP")
        (self.root / "reviews").mkdir()
        (self.root / "reviews/evidence.md").write_text("Synthetic trace evidence")
        save_json(project.path("evals"), design)
        self.assertEqual(self.cli("eval", "cases-apply", "--dry-run")[0], 2)
        for key, sid, choice in (("tester:tools", "t1", "--remote"), ("case:handoff", "c1", "--keep-local"),
                                 ("case:hours", "c2", "--remote"), ("pairs:handoff", "c1", "--remote"), ("pairs:hours", "c2", "--remote")):
            args = ["agent", "adopt", "--resource", key, "--remote-id", sid, choice]
            code, plan = self.cli(*args, "--dry-run")
            self.assertEqual(code, 0, self.error)
            self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 0, self.error)
        self.assertEqual(self.cli("agent", "adopt", "--resource", "pairs:handoff", "--remote-id", "c2", "--remote", "--dry-run")[0], 2)
        code, plan = self.cli("eval", "cases-apply", "--dry-run")
        self.assertEqual(code, 0, self.error)
        self.assertEqual([p["resource"] for p in plan["plans"] if p["changed"]], ["case:handoff"])
        count = len(self.api.calls)
        self.assertEqual(self.cli("eval", "cases-apply", "--expect", plan["token"])[0], 0, self.error)
        self.assertEqual(self.api.cases["c1"]["input"], "Local pending wording")
        self.assertEqual(len(self.api.testers), 1)
        self.assertEqual([path for method, path, _ in self.api.calls[count:] if method in ("PUT", "PATCH")], ["/external/eval/cases/c1"])

    def test_platform_resume_fixture(self):
        self.bind()
        self.api.agent["publish_history_id"] = "h0"
        self.api.agent.update(system_prompt="Platform prompt proposal", description="Platform description")
        self.local_agent(system_prompt="Local prompt proposal", description="Local description")
        self.assertEqual(self.cli("agent", "pull")[0], 0, self.error)
        self.decision("--remote", "description")
        status = self.cli("status")[1]
        self.assertEqual(status["resources"]["agent"]["comparison_at_last_query"]["system_prompt"]["state"], "undecided")
        log = next((self.root / "logs").glob("*.md"))
        log.write_text("# Synthetic resume fixture\n\nUser decision: adopt platform description only. Prompt difference remains undecided; no platform mutation authorized. Draft h1 and Published h0 differ. Imports/decisions are fixture observations, not accepted policy.\n")
        self.artifact = self.root

    def test_environment_resolution_stays_out_of_preview_receipts_and_content(self):
        self.bind(new=True)
        with patch.dict(os.environ, {"FIXTURE_MODEL": "model-available", "FIXTURE_TOKEN": "synthetic-tool-secret", "FIXTURE_CONTEXT": "42"}):
            self.local_agent(llm_model="env:FIXTURE_MODEL", primary_object_ids=["env:FIXTURE_CONTEXT"],
                             unified_tools=[{"id": "request", "type": "http_request", "http_request": {"method": "POST", "url_template": "https://service.invalid/action", "auth": {"type": "bearer", "token": "env:FIXTURE_TOKEN"}}}])
            code, plan = self.cli("agent", "apply", "--dry-run")
            self.assertEqual(code, 0, self.error)
            self.assertNotIn("synthetic-tool-secret", json.dumps(plan))
            self.assertEqual(self.cli("agent", "apply", "--expect", plan["token"])[0], 0, self.error)
            payload = next(body for method, path, body in self.api.calls if method == "POST" and path == "/external/agents")
            self.assertEqual(payload["unified_tools"][0]["http_request"]["auth"]["token"], "synthetic-tool-secret")
            # Real API primary_object_ids are integers, unlike this fixture payload.
            self.api.agent["primary_object_ids"] = [42]
            self.assertFalse(self.cli("agent", "apply", "--dry-run")[1]["changed"])
            for path in (self.root / ".codeer").rglob("*.json"):
                self.assertNotIn("synthetic-tool-secret", path.read_text())
            self.assertIn("env:FIXTURE_TOKEN", (self.root / "agent/settings.json").read_text())
            _, old = self.cli("agent", "apply", "--dry-run")
            os.environ["FIXTURE_TOKEN"] = "changed-tool-secret"
            self.assertEqual(self.cli("agent", "apply", "--expect", old["token"])[0], 2)

    def test_legacy_flat_release_copies_are_deduplicated_or_rejected_if_inconsistent(self):
        project = discover()
        record = {"id": "old", "time": "2026-10-01", "status": "outcome_unknown"}
        save_json(self.root / "releases/old/release.json", record)
        save_json(self.root / "releases/old.json", record)
        self.assertEqual(len(project.release_paths()), 1)
        save_json(self.root / "releases/new.json", {"id": "new", "time": "2026-10-02", "status": "pending"})
        self.assertEqual(len(project.release_paths()), 2)
        save_json(self.root / "releases/old.json", {**record, "status": "published"})
        with self.assertRaisesRegex(ProjectError, "Conflicting release"):
            project.release_paths()

    def test_complete_portable_eval_release_delivery_and_environment_isolation(self):
        from test_project_eval import design_fixture
        from codeer_cli.project import fingerprint
        from codeer_cli.delivery import digest
        project = self.bind(new=True)
        self.local_agent(attachment_ids=["attachment:manual"], unified_tools=[{"id": "search", "type": "knowledge_base", "knowledge_node_ids": ["kb:faq"]}])
        original = b"%PDF-1.7 synthetic deployment original"
        (self.root / "sources/documents/manual.pdf").write_bytes(original)
        (self.root / "kb").mkdir()
        (self.root / "kb/faq.md").write_text("Synthetic FAQ\n")
        save_json(self.root / "resources.json", {"schema_version": 1, "attachments": {"manual": {"path": "sources/documents/manual.pdf"}}, "knowledge": {"faq": {"directory": "kb", "glob": "*.md", "faq_file": "sources/knowledge/faq-definitions.json"}}})
        save_json(self.root / "sources/knowledge/faq-definitions.json", {"schema_version": 1, "files": {"faq.md": {"content": "Synthetic FAQ\n", "faqs": {"hours": {"question": "Opening hours?", "ranges": []}}}}})
        attach_args = ["agent", "attachment", "--local-id", "manual"]
        _, attachment = self.cli(*attach_args, "--dry-run")
        with patch("codeer_cli.project_attachments.download", return_value=original):
            self.assertEqual(self.cli(*attach_args, "--expect", attachment["token"])[0], 0, self.error)
        args = ["kb", "upload", "--local-id", "faq", "--dir", str(self.root / "kb"), "--glob", "*.md", "--name", "Fixture", "--poll-timeout", "0"]
        code, plan = self.cli(*args, "--dry-run")
        self.assertEqual(code, 0, self.error)
        self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 0, self.error)
        self.assertIn(b"Synthetic FAQ\n", self.api.upload_bytes)
        faq_args = ["kb", "faq-sync", "--local-id", "faq", "--keep-local"]
        for extra in ([], ["--apply"]):
            code, faq = self.cli(*faq_args, *extra, "--dry-run")
            self.assertEqual(code, 0, self.error)
            self.assertEqual(self.cli(*faq_args, *extra, "--expect", faq["token"])[0], 0, self.error)
        _, plan = self.cli("agent", "apply", "--dry-run")
        self.assertEqual(self.cli("agent", "apply", "--expect", plan["token"])[0], 0, self.error)
        self.assertEqual(self.api.agent["unified_tools"][0]["knowledge_node_ids"], ["kb-created"])
        design = design_fixture()
        design["testers"][0]["judge_llm_model_id"] = "model-available"
        design["cases"][0].pop("attachment_ids")
        design["cases"][0].pop("label_ids")
        (self.root / "sources/documents/sop.md").write_text("Synthetic SOP")
        (self.root / "reviews").mkdir()
        (self.root / "reviews/evidence.md").write_text("Synthetic tool trace delivery")
        save_json(project.path("evals"), design)
        code, plan = self.cli("eval", "cases-apply", "--dry-run")
        self.assertEqual(code, 0, self.error)
        self.assertEqual(self.cli("eval", "cases-apply", "--expect", plan["token"])[0], 0, self.error)
        self.assertEqual(len(self.api.testers), 1)
        self.assertEqual(len(self.api.cases), 2)
        confirmation = self.root / "reviews/acceptance.md"
        confirmation.write_text("Synthetic confirmation for both pairs")
        acceptance = {"pairs": [{"case": c["local_id"], "tester": "tools"} for c in design["cases"]]}
        acceptance["confirmation"] = {"source": "reviews/acceptance.md", "source_fingerprint": fingerprint(confirmation.read_text()), "scope_fingerprint": fingerprint(acceptance)}
        save_json(project.path("acceptance"), acceptance)
        anchor_path = self.root / "reviews/anchor.json"
        self.assertEqual(self.cli("eval", "snapshot", "--history", "h1", "--out", str(anchor_path))[0], 0, self.error)
        anchor = read_json(anchor_path)
        report = self.root / "reviews/audit.md"
        report.write_text("Synthetic audit")
        save_json(self.root / "reviews/current.audit.json", {"schema_version": 1, "conclusion": "pass", "revision": anchor["revision"], "remote_fingerprint": anchor["remote_fingerprint"], "history_id": "h1", "pairs": anchor["snapshot"]["pairs"], "report": "reviews/audit.md", "report_fingerprint": fingerprint(report.read_text())})
        code, run = self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
        self.assertEqual(code, 0, self.error)
        _, plan = self.cli("agent", "publish", "--history", "h1", "--dry-run")
        code, release = self.cli("agent", "publish", "--history", "h1", "--expect", plan["token"])
        self.assertEqual(code, 0, self.error)
        self.assertEqual(project.release_paths()[0].parent.name, "releases")
        destination = self.root / "delivery/formal"
        code, exported = self.cli("eval", "delivery", "--run-id", run["id"], "--release-id", release["id"], "--out-dir", str(destination))
        self.assertEqual(code, 0, exported)
        self.assertFalse((destination / ".codeer").exists())
        self.assertEqual(self.cli("eval", "delivery", "--verify", str(destination))[0], 0)
        input_path = destination / f"runs/{run['id']}/inputs/sources/documents/manual.pdf"
        self.assertEqual(input_path.read_bytes(), original)
        self.assertEqual(read_json(destination / f"runs/{run['id']}/inputs/sources/knowledge/faq-definitions.json")["files"]["faq.md"]["faqs"]["hours"]["question"], "Opening hours?")
        self.assertEqual(len(read_json(self.root / f"runs/{run['id']}/run.json")["snapshot"]["kb"]["kb-created"]["faqs"]["node-faq"]["faqs"]), 1)
        input_path.unlink()
        self.assertEqual(self.cli("eval", "delivery", "--verify", str(destination))[0], 1)
        input_path.write_bytes(original)
        # A newer result cannot substitute for the exact run even if file hashes are refreshed.
        path = destination / f"runs/{run['id']}/run.json"
        record = read_json(path)
        record["results"][0]["result"]["id"] = "newer-unrelated-id"
        save_json(path, record)
        manifest = read_json(destination / "manifest.json")
        manifest["files"][str(path.relative_to(destination))] = digest(path.read_bytes())
        save_json(destination / "manifest.json", manifest)
        self.assertEqual(self.cli("eval", "delivery", "--verify", str(destination))[0], 1)
        content_revision = project.revision()
        self.api = PortableAPI()
        self.api.base_url = "https://beta.fixture.invalid"
        self.api.attachment_id = "beta-attachment"
        self.bind("beta", new=True)
        _, attachment = self.cli(*attach_args, "--dry-run")
        with patch("codeer_cli.project_attachments.download", return_value=original):
            self.assertEqual(self.cli(*attach_args, "--expect", attachment["token"])[0], 0, self.error)
        _, plan = self.cli(*args, "--dry-run")
        self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 0, self.error)
        for extra in ([], ["--apply"]):
            _, faq = self.cli(*faq_args, *extra, "--dry-run")
            self.assertEqual(self.cli(*faq_args, *extra, "--expect", faq["token"])[0], 0, self.error)
        _, plan = self.cli("agent", "apply", "--dry-run")
        self.assertEqual(self.cli("agent", "apply", "--expect", plan["token"])[0], 0, self.error)
        self.assertEqual(self.api.agent["attachment_ids"], ["beta-attachment"])
        _, plan = self.cli("eval", "cases-apply", "--dry-run")
        self.assertEqual(self.cli("eval", "cases-apply", "--expect", plan["token"])[0], 0, self.error)
        self.assertEqual(discover().revision(), content_revision)
        self.assertIsNone(self.cli("status")[1]["latest_run"])
        self.assertEqual(self.cli("eval", "delivery", "--run-id", run["id"], "--release-id", release["id"], "--out-dir", str(self.root / "wrong-scope-delivery"))[0], 2)
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 2)  # no beta audit/run
        self.bind("another")
        # Same scope is the same deployment identity, even with another alias.
        # A different API cannot inherit its run or release.
        other = discover()
        other.bind(api_base="https://other.invalid")
        status = other.status()
        self.assertIsNone(status["latest_run"])
        self.assertIsNone(status["latest_release"])
        self.artifact = self.root


if __name__ == "__main__":
    unittest.main()
