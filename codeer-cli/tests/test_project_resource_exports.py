"""Public resource export → portable files/FAQ → another environment contracts."""
import copy
import hashlib
import json
import unittest

import httpx

from codeer_cli.project import discover, fingerprint, read_json, save_json, ProjectError
from codeer_cli.resource_exports import original
import test_project_deployments as deployments


class ExportAPI(deployments.PortableAPI):
    def __init__(self):
        super().__init__()
        self.text = "First line\r\nSecond line\n"
        self.binary = b"%PDF-1.7\x00\xff\r\noriginal"
        self.faqs = [{"id": 7, "context_object_id": 101, "question": "Which line?",
                      "ranges": [{"start_line": 1, "start_column": 0, "end_line": 1, "end_column": 5,
                                  "start_offset": 0, "end_offset": 5, "text": "First"}]}]
        self.digest = True
        self.bad_header = False
        self.bad_bytes = False
        self.fail_create = False
        self.fail_update = False
        self.export_unavailable = False
        self.other_faq_on_readback = False
        self.attachment_type = "file"
        self.status_snapshot = 101

    def metadata(self):
        return {"node_id": "node-faq", "knowledge_base_id": "kb-created", "workspace_id": "w",
                "name": "guide.pdf", "source_type": "LOCAL_UPLOAD", "status": "READY", "snapshot_object_id": 101,
                "stored_file": {"available": True, "filename": "guide.pdf", "size_bytes": len(self.binary),
                                "sha256": hashlib.sha256(self.binary).hexdigest() if self.digest else None,
                                "provenance": "uploaded_original", "revision": "file-v1"},
                "text_snapshot": {"available": True, "revision": fingerprint(self.text)}, "external_reference": None}

    def exported(self):
        return {"metadata": self.metadata(), "snapshot": {"snapshot_object_id": 101, "content": self.text,
                "content_revision": fingerprint(self.text)}, "faqs": copy.deepcopy(self.faqs),
                "export_revision": fingerprint([101, self.text, sorted(self.faqs, key=lambda f: f["id"])])}

    def handler(self, request):
        path = request.url.path.removeprefix("/api/v1")
        result = None
        if path == "/external/knowledge-bases/files:status":
            return httpx.Response(200, json={"error_code": 0, "data": [{"node_id": "node-faq", "status": "READY", "snapshot_object_id": self.status_snapshot}]})
        if path.startswith("/external/files/"):
            sid = path.split("/")[3]
            self.calls.append((request.method, path, dict(request.url.params)))
            assert request.headers["x-api-key"] == "synthetic"
            if path.endswith("/download"):
                assert request.url.params["expected_revision"] == "file-v1"
                return httpx.Response(200, content=self.binary, headers={"X-Codeer-Content-Revision": "file-v1"})
            if path.endswith("/content"):
                assert request.url.params["expected_revision"] == "text-v1"
                return httpx.Response(200, json={"error_code": 0, "data": {"attachment_id": sid, "content": self.text, "content_revision": "text-v1", "source_type": "context_object"}})
            meta = self.metadata()
            meta.update(attachment_id=sid, attachment_type=self.attachment_type,
                        text_snapshot={"available": True, "revision": "text-v1"})
            if self.attachment_type == "context_object":
                meta["stored_file"] = {"available": False, "reason": "no_stored_file", "provenance": "unknown"}
            return httpx.Response(200, json={"error_code": 0, "data": meta})
        if path == "/external/knowledge-bases/files/node-faq/export":
            if self.export_unavailable:
                return httpx.Response(404, json={"error_code": 1, "message": "not deployed"})
            result = self.exported()
            if request.url.params.get("expected_export_revision", result["export_revision"]) != result["export_revision"]:
                return httpx.Response(409, json={"error_code": 1, "data": {"reason": "resource_changed"}})
        elif path == "/external/knowledge-bases/files/node-faq/download":
            self.calls.append(("GET", path, dict(request.url.params)))
            if request.url.params.get("expected_snapshot_object_id") != "101":
                return httpx.Response(409, json={"error_code": 1})
            return httpx.Response(200, content=self.binary + (b"bad" if self.bad_bytes else b""),
                                  headers={"X-Codeer-Snapshot-Object-Id": "102" if self.bad_header else "101"})
        elif path.startswith("/external/context-object-faqs"):
            if request.method == "POST":
                data = json.loads(request.content)
                result = {"id": max([f["id"] for f in self.faqs] + [100]) + 1, **data}
                self.faqs.append(result)
                if self.fail_create:
                    self.calls.append(("POST", path, data))
                    raise httpx.ReadTimeout("created; response lost", request=request)
            elif request.method == "PATCH":
                sid = int(path.rsplit("/", 1)[1])
                result = next(f for f in self.faqs if f["id"] == sid)
                result.update(json.loads(request.content))
                if self.fail_update:
                    self.calls.append(("PATCH", path, None))
                    raise httpx.ReadTimeout("updated; response lost", request=request)
            elif request.method == "DELETE":
                sid = int(path.rsplit("/", 1)[1])
                self.faqs = [f for f in self.faqs if f["id"] != sid]
                result = {}
        if result is not None:
            self.calls.append((request.method, path, None))
            return httpx.Response(200, json={"data": result, "error_code": 0})
        return super().handler(request)


class ResourceExportTests(unittest.TestCase):
    cli = deployments.DeploymentTests.cli
    bind = deployments.DeploymentTests.bind
    local_agent = deployments.DeploymentTests.local_agent

    def setUp(self):
        deployments.DeploymentTests.setUp(self)
        self.api = ExportAPI()
        self.bind()

    def imported(self):
        args = ["kb", "import", "--local-id", "manual", "--kb-id", "kb-created"]
        code, plan = self.cli(*args, "--dry-run")
        self.assertEqual(code, 0, self.error)
        self.assertFalse((self.root / "kb/manual-faqs.json").exists())
        code, result = self.cli(*args, "--expect", plan["token"])
        self.assertEqual(code, 0, self.error)
        return result

    def sync(self, *args):
        base = ["kb", "faq-sync", "--local-id", "manual", *args]
        code, plan = self.cli(*base, "--dry-run")
        self.assertEqual(code, 0, self.error)
        code, result = self.cli(*base, "--expect", plan["token"])
        self.assertEqual(code, 0, self.error)
        return result

    def test_import_binary_saved_text_complete_faq_and_manifest(self):
        self.api.faqs = [{**self.api.faqs[0], "id": i} for i in range(1, 206)]
        result = self.imported()
        self.assertEqual((self.root / result["obtained"][0]).read_bytes(), self.api.binary)
        bundle = read_json(self.root / result["faq_file"])
        row = bundle["files"]["001-guide.pdf"]
        self.assertEqual(row["content"], self.api.text)
        self.assertEqual(len(row["faqs"]), 205)
        self.assertTrue(all("id" not in v and "context_object_id" not in v for v in row["faqs"].values()))
        manifest = read_json(self.root / "sources/knowledge/manual/manifest.json")
        self.assertEqual(manifest["files"]["001-guide.pdf"]["original"]["verification"], "size_digest_verified")
        self.assertIn({"reason": "website_crawl_settings_excluded"}, manifest["gaps"])
        from codeer_cli.portable import input_paths
        self.assertIn(self.root / result["faq_file"], input_paths(discover()))
        self.assertFalse(any(m != "GET" for m, p, _ in self.api.calls if not p.endswith(":status")))

    def test_new_environment_rebuild_maps_new_ids_and_preserves_content_revision(self):
        self.imported()
        revision = discover().revision()
        definition = read_json(self.root / "resources.json")["knowledge"]["manual"]
        self.api.base_url = "https://other.invalid"
        self.bind("second", new=True)
        # Bind the target through the actual CLI, including conditioned byte verification.
        save_json(self.root / "target-files.json", {"001-guide.pdf": "node-faq"})
        bind_args = ["kb", "bind", "--local-id", "manual", "--kb-id", "kb-created", "--files", str(self.root / "target-files.json"), "--keep-local"]
        code, binding = self.cli(*bind_args, "--dry-run")
        self.assertEqual(code, 0, self.error)
        self.assertEqual(self.cli(*bind_args, "--expect", binding["token"])[0], 0, self.error)
        self.api.faqs = []
        self.assertEqual(self.sync("--keep-local")["status"], "pending_apply")
        result = self.sync("--keep-local", "--apply")
        self.assertEqual(result["status"], "aligned")
        self.assertEqual(len(self.api.faqs), 1)
        self.assertNotEqual(self.api.faqs[0]["id"], 7)
        self.assertEqual(discover().revision(), revision)
        self.assertEqual(definition["faq_file"], "kb/manual-faqs.json")
        self.assertEqual(self.sync("--keep-local", "--apply")["status"], "aligned")
        self.assertEqual(sum(m == "POST" and p == "/external/context-object-faqs" for m, p, _ in self.api.calls), 1)

    def test_faq_only_change_invalidates_preview_remote_adoption_has_no_mutations(self):
        self.imported()
        revision = discover().revision()
        args = ["kb", "faq-sync", "--local-id", "manual", "--remote"]
        _, plan = self.cli(*args, "--dry-run")
        self.api.faqs[0]["question"] = "Changed platform question"
        self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 2)
        self.sync("--remote")
        self.assertNotEqual(discover().revision(), revision)
        self.assertFalse(any(m != "GET" for m, p, _ in self.api.calls if not p.endswith(":status")))
        self.api.faqs = []
        self.sync("--remote")
        self.assertFalse(read_json(self.root / "kb/manual-faqs.json")["files"]["001-guide.pdf"]["faqs"])

    def test_target_text_mismatch_blocks_faq_rebuild(self):
        self.imported()
        self.api.text = "A changed extraction"
        self.sync("--keep-local")
        args = ["kb", "faq-sync", "--local-id", "manual", "--keep-local", "--apply"]
        _, plan = self.cli(*args, "--dry-run")
        self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 2)
        self.assertIn("Target saved text differs", self.error)

    def test_unknown_create_never_retries_by_question(self):
        self.imported()
        bundle = read_json(self.root / "kb/manual-faqs.json")
        bundle["files"]["001-guide.pdf"]["faqs"]["new-faq"] = {"question": "new", "ranges": []}
        save_json(self.root / "kb/manual-faqs.json", bundle)
        self.sync("--keep-local")
        self.api.fail_create = True
        args = ["kb", "faq-sync", "--local-id", "manual", "--keep-local", "--apply"]
        _, plan = self.cli(*args, "--dry-run")
        self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 1)
        self.assertEqual(self.cli("kb", "faq-sync", "--local-id", "manual", "--reconcile")[0], 2)
        self.assertIn("Unknown created FAQ identity", self.error)
        self.assertEqual(sum(m == "POST" and p == "/external/context-object-faqs" for m, p, _ in self.api.calls), 1)
        mapping = discover().state()["resources"]["faq:manual"]["ids"]
        mapping["001-guide.pdf"]["new-faq"] = self.api.faqs[-1]["id"]
        save_json(self.root / "recovered-ids.json", mapping)
        count = len(self.api.calls)
        code, result = self.cli("kb", "faq-sync", "--local-id", "manual", "--reconcile", "--ids", str(self.root / "recovered-ids.json"))
        self.assertEqual(code, 0, self.error)
        self.assertEqual(result["status"], "aligned")
        self.assertFalse(any(m != "GET" for m, _, _ in self.api.calls[count:]))

    def test_known_update_timeout_reconciles_without_write(self):
        self.imported()
        path = self.root / "kb/manual-faqs.json"
        bundle = read_json(path)
        row = bundle["files"]["001-guide.pdf"]
        next(iter(row["faqs"].values()))["question"] = "Local proposal"
        save_json(path, bundle)
        self.api.fail_update = True
        args = ["kb", "faq-sync", "--local-id", "manual", "--keep-local", "--apply"]
        _, plan = self.cli(*args, "--dry-run")
        self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 1)
        next(iter(row["faqs"].values()))["question"] = "Newer proposal"
        save_json(path, bundle)
        count = len(self.api.calls)
        code, result = self.cli("kb", "faq-sync", "--local-id", "manual", "--reconcile")
        self.assertEqual(code, 0, self.error)
        self.assertEqual(result["comparison"]["001-guide.pdf"]["state"], "pending_apply")
        self.assertFalse(any(m != "GET" for m, _, _ in self.api.calls[count:]))
        self.assertEqual(next(iter(read_json(path)["files"]["001-guide.pdf"]["faqs"].values()))["question"], "Newer proposal")

    def test_managed_faq_delete_is_explicit_and_read_back(self):
        self.imported()
        path = self.root / "kb/manual-faqs.json"
        bundle = read_json(path)
        bundle["files"]["001-guide.pdf"]["faqs"] = {}
        save_json(path, bundle)
        self.assertEqual(self.sync("--keep-local", "--apply")["status"], "aligned")
        self.assertEqual(self.api.faqs, [])

    def test_export_unavailable_retains_gap_and_no_partial_original(self):
        self.api.export_unavailable = True
        self.api.agent["unified_tools"] = [{"type": "knowledge_base", "knowledge_node_ids": ["kb-created"]}]
        code, result = self.cli("agent", "pull")
        self.assertEqual(code, 0, self.error)
        self.assertIn("export_api_unavailable", str(result["knowledge"]["gaps"]))
        self.assertFalse((self.root / "sources/knowledge").exists())

    def test_digest_header_and_length_failures_never_finalize_original(self):
        for attr in ("bad_bytes", "bad_header"):
            with self.subTest(attr=attr):
                setattr(self.api, attr, True)
                with self.api.client() as client, self.assertRaises(ProjectError):
                    original(client, self.api.metadata(), node_id="node-faq")
                setattr(self.api, attr, False)
        self.api.digest = False
        with self.api.client() as client:
            data, receipt = original(client, self.api.metadata(), node_id="node-faq")
        self.assertEqual(data, self.api.binary)
        self.assertEqual(receipt["verification"], "no_server_digest")

    def test_authenticated_attachment_original_and_context_text_only(self):
        from codeer_cli.project_attachments import import_originals
        history = {"id": "h1", "attachments": [{"id": "asset", "original_name": "../manual.pdf", "source_url": "https://untrusted.invalid/never-fetch"}]}
        with self.api.client() as client:
            result = import_originals(discover(), client, history)
        self.assertEqual((self.root / result["obtained"][0]).read_bytes(), self.api.binary)
        manifest = next((self.root / "sources/exports").glob("*.json"))
        evidence = read_json(manifest)
        self.assertEqual(evidence["agent_version_id"], "h1")
        self.assertEqual(evidence["verification"], "size_digest_verified")
        self.assertNotIn("untrusted.invalid", manifest.read_text())
        self.api.attachment_type = "context_object"
        with self.api.client() as client:
            result = import_originals(discover(), client, {"id": "h1", "attachments": [{"id": "context", "attachment_type": "context_object"}]})
        self.assertFalse(result["obtained"])
        self.assertTrue(result["gaps"])
        exported = read_json(self.root / ("sources/exports/imported-" + fingerprint("context")[:12] + ".json"))
        self.assertEqual(exported["text_snapshot"]["content"], self.api.text)
        self.assertFalse(exported["original_obtained"])

    def test_bad_digest_and_interrupted_stream_do_not_return_success(self):
        metadata = self.api.metadata()
        metadata["stored_file"]["sha256"] = "0" * 64
        with self.api.client() as client, self.assertRaises(ProjectError):
            original(client, metadata, node_id="node-faq")
        class Interrupted(httpx.SyncByteStream):
            def __iter__(self):
                yield b"partial"
                raise httpx.ReadError("connection lost")
        with self.api.client() as client:
            client._client.close()
            client._client = httpx.Client(base_url=client.base_url, transport=httpx.MockTransport(
                lambda r: httpx.Response(200, stream=Interrupted(), headers={"X-Codeer-Snapshot-Object-Id": "101"})))
            with self.assertRaisesRegex(ProjectError, "interrupted"):
                original(client, self.api.metadata(), node_id="node-faq")

    def test_clone_requires_explicit_faq_mapping(self):
        self.imported()
        project = discover()
        state = project.state()
        state["resources"].pop("faq:manual")
        project.save_state(state)
        args = ["kb", "faq-sync", "--local-id", "manual", "--keep-local"]
        self.sync("--keep-local")
        _, plan = self.cli(*args, "--apply", "--dry-run")
        self.assertEqual(self.cli(*args, "--apply", "--expect", plan["token"])[0], 2)
        self.assertIn("Unmapped target FAQ", self.error)
        lid = next(iter(read_json(self.root / "kb/manual-faqs.json")["files"]["001-guide.pdf"]["faqs"]))
        save_json(self.root / "faq-ids.json", {"001-guide.pdf": {lid: 7}})
        self.assertEqual(self.sync("--remote", "--ids", str(self.root / "faq-ids.json"))["status"], "aligned")

    def test_invalid_coordinate_basis_blocks_before_any_write(self):
        self.imported()
        path = self.root / "kb/manual-faqs.json"
        data = read_json(path)
        span = next(iter(data["files"]["001-guide.pdf"]["faqs"].values()))["ranges"][0]
        span["start_offset"] = 2
        save_json(path, data)
        count = len(self.api.calls)
        self.assertEqual(self.cli("kb", "faq-sync", "--local-id", "manual", "--keep-local", "--apply", "--dry-run")[0], 2)
        self.assertFalse(any(m != "GET" for m, _, _ in self.api.calls[count:]))

    def test_faq_resume_fixture(self):
        self.test_new_environment_rebuild_maps_new_ids_and_preserves_content_revision()
        path = self.root / "kb/manual-faqs.json"
        bundle = read_json(path)
        next(iter(bundle["files"]["001-guide.pdf"]["faqs"].values()))["question"] = "Local pending FAQ proposal"
        save_json(path, bundle)
        self.api.faqs[0]["question"] = "Platform FAQ proposal"
        count = len(self.api.calls)
        code, observation = self.cli("kb", "faq-sync", "--local-id", "manual", "--dry-run")
        self.assertEqual(code, 0, self.error)
        self.assertEqual(observation["comparison"]["001-guide.pdf"]["state"], "undecided")
        code, status = self.cli("status")
        self.assertEqual(code, 0)
        self.assertEqual(status["resources"]["faq:manual"]["comparison_at_last_query"]["001-guide.pdf"]["state"], "undecided")
        self.assertIn("faq:manual", status["local_changes"])
        binding = discover().state()["resources"]["kb:manual"]
        self.assertEqual(binding["base"][0]["snapshot_object_id"], 101)
        self.assertEqual(binding["original_verification"]["001-guide.pdf"]["snapshot_object_id"], 101)
        save_json(self.root / "reviews/faq-observation.json", observation)
        (self.root / "logs").mkdir(exist_ok=True)
        (self.root / "logs/2026-10.md").write_text("# Synthetic FAQ handoff\n\nSource KB originals/text/FAQ imported; target FAQ rebuilt with new IDs.\nBoth local and platform FAQ questions now differ from the confirmed base.\nReview reviews/faq-observation.json; no further FAQ choice/apply is authorized.\nWebsite crawl settings excluded; all data and API responses are synthetic.\n")
        self.assertFalse(any(m != "GET" for m, _, _ in self.api.calls[count:]))
        self.artifact = self.root

    def test_snapshot_change_blocks_bind_baseline(self):
        self.imported()
        save_json(self.root / "files.json", {"001-guide.pdf": "node-faq"})
        args = ["kb", "bind", "--local-id", "manual", "--kb-id", "kb-created", "--files", str(self.root / "files.json"), "--keep-local"]
        _, plan = self.cli(*args, "--dry-run")
        previous = discover().state()["resources"]["kb:manual"]
        self.api.status_snapshot = 102
        self.assertEqual(self.cli(*args, "--expect", plan["token"])[0], 2)
        self.assertIn("snapshot changed", self.error)
        self.assertEqual(discover().state()["resources"]["kb:manual"], previous)


if __name__ == "__main__":
    unittest.main()
