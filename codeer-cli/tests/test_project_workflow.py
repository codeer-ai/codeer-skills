"""Two synthetic journeys through the real parser and MockTransport API."""
import copy
import unittest

from codeer_cli.project import read_json, save_json
from test_project_evidence import EvidenceFixture


class WorkflowTests(EvidenceFixture, unittest.TestCase):
    def test_new_agent_repair_regression_and_release(self):
        # Local design first, with no Agent binding or remote writes.
        (self.root / "agent").mkdir()
        save_json(self.root / "agent/settings.json", {"name": "Synthetic Support", "human_handoff": self.api.agent["human_handoff"]})
        (self.root / "agent/instructions.md").write_text("Transfer explicit human requests; answer factual hours directly.")
        (self.root / "design").mkdir()
        (self.root / "design/agent-design.md").write_text("Synthetic accepted policy: explicit human request transfers; hours questions do not.")
        (self.root / "sources/index.md").write_text("# Sources\n\nSynthetic SOP: documents/sop.md; authoritative only inside this fixture.\n")
        self.assertFalse(any(method != "GET" for method, _, _ in self.api.calls))
        _, preview = self.cli("agent", "apply", "--dry-run")
        self.assertEqual(self.cli("agent", "apply", "--expect", preview["token"])[0], 0)
        self.assertEqual(sum(method == "POST" and path == "/external/agents" for method, path, _ in self.api.calls), 1)
        project = self.setup_evidence()
        self.api.run_mode = "failed"
        code, failed = self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
        self.assertEqual(code, 1)
        report = project.root / "reviews/repair.md"
        report.write_text("Synthetic finding: failed scores require repair. Confirmed fixture change: clarify transfer trigger; protect factual-hours behavior. No real quality claim.")
        project.path("instructions").write_text("On explicit request for a person, call handoff. Answer hours directly without transfer.")
        self.api.bump_versions = True
        _, preview = self.cli("agent", "apply", "--dry-run")
        self.assertEqual(self.cli("agent", "apply", "--expect", preview["token"])[0], 0)
        self.assertEqual(self.api.history_id, "h2")
        self.assertEqual(self.cli("eval", "run", "--history", "h2", "--poll-timeout", "0")[0], 2)  # stale audit
        self.audit(project, "h2")
        self.api.run_mode = "pass"
        self.assertEqual(self.cli("eval", "run", "--history", "h2", "--cases", "c1", "--poll-timeout", "0")[0], 0)
        self.assertEqual(self.cli("agent", "publish", "--history", "h2", "--dry-run")[0], 2)  # focused only
        code, full = self.cli("eval", "run", "--history", "h2", "--poll-timeout", "0")
        self.assertEqual(code, 0)
        _, preview = self.cli("agent", "publish", "--history", "h2", "--dry-run")
        code, release = self.cli("agent", "publish", "--history", "h2", "--expect", preview["token"])
        self.assertEqual(code, 0)
        self.assertEqual(release["actual_history_id"], "h2")
        self.assertNotEqual(failed["id"], full["id"])
        (project.root / "log.md").write_text(f"# Fixture log\n\nAccepted synthetic policy → Draft applied → failed [{failed['id']}](runs/{failed['id']}/run.json) → [confirmed repair](reviews/repair.md) → h2 focused and full [{full['id']}](runs/{full['id']}/run.json) → fixture release read back.\n")
        _, status = self.cli("status")
        self.assertEqual(status["latest_release"]["status"], "published")
        self.artifact = project.root

    def test_existing_agent_web_conflict_and_history_candidates(self):
        self.api.agent["publish_history_id"] = "h0"
        project, design = self.prepare()
        self.apply_design()
        self.assertFalse(project.path("design").exists())  # does not block bounded import/review
        imported = next((project.root / ".codeer/imports").glob("*/agent.json"))
        raw = read_json(imported)
        self.assertEqual(raw["published"]["system_prompt"], "Previously published")
        project.path("instructions").write_text("Local prompt proposal")
        self.api.agent["system_prompt"] = "Web prompt proposal"
        _, preview = self.cli("agent", "diff", "--local")
        self.assertIn("system_prompt", preview["conflicts"])
        before = sum(method != "GET" for method, _, _ in self.api.calls)
        self.assertEqual(self.cli("agent", "apply", "--expect", preview["token"])[0], 2)
        self.assertEqual(self.cli("agent", "pull")[0], 0)
        self.assertEqual(project.path("instructions").read_text(), "Local prompt proposal")
        collection = project.root / "sources/history/synthetic-week"
        collection.mkdir(parents=True)
        self.assertEqual(self.cli("history", "list", "--has-ai-drafts", "--out", str(collection / "index.json"))[0], 0)
        self.assertEqual(self.cli("history", "ai-drafts", "12", "--out", str(collection / "drafts.json"))[0], 0)
        self.assertEqual(self.cli("history", "conversations", "12", "--out", str(collection / "parts.json"))[0], 0)
        self.assertEqual(sum(method != "GET" for method, _, _ in self.api.calls), before)
        exported = read_json(collection / "drafts.json")
        self.assertEqual(exported["history_id"], 12)
        self.assertEqual(exported["total_records"], 1)
        self.assertEqual(len(exported["drafts"]), 1)
        draft = exported["drafts"][0]
        self.assertEqual((draft["id"], draft["history_id"]), (9, 12))
        self.assertEqual(draft["outcome"], "dismissed")
        self.assertEqual(draft["content"], "Claimed transfer")
        self.assertEqual(draft["dismiss_feedback"], "No transfer occurred")
        self.assertEqual(draft["tool_activities"], [])
        self.assertEqual(draft["delivery"]["status"], "not_sent")
        # Skill-owned analysis is an explicit local proposal, never inferred acceptance.
        candidate = {"status": "proposal", "source": {"history_id": 12, "draft_id": 9,
                     "artifact": "sources/history/synthetic-week/drafts.json"},
                     "owner": "evidence delivery or handoff implementation, unresolved",
                     "variants": ["original explicit request", "nearby paraphrase", "opposite factual query", "previously passing hours protection"],
                     "reproduction": "Verify complete tool trace before asserting non-execution"}
        save_json(project.root / "reviews/history-candidates.json", [candidate])
        proposed = copy.deepcopy(design)
        proposed["cases"][0]["source"] = {**candidate["source"], "document": candidate["source"]["artifact"]}
        save_json(project.root / "evals/history-proposal.json", proposed)
        (project.root / "design").mkdir(exist_ok=True)
        (project.root / "design/agent-design.draft.md").write_text("Pending: should ambiguous frustration trigger transfer? Recommend explicit requests only; confirm business policy before changing.")
        (project.root / "log.md").write_text("# Fixture log\n\nImported h1 Draft and h0 Published, unvalidated. Local/web prompt conflict preserved; no apply. [History candidates](reviews/history-candidates.json) are proposals. Ambiguous handoff policy awaits confirmation in Agent design draft.\n")
        self.assertEqual(read_json(project.path("evals")), design)
        self.assertEqual(self.api.agent["publish_history_id"], "h0")
        self.assertFalse(any(method == "POST" and path == "/external/agents" for method, path, _ in self.api.calls))
        self.artifact = project.root
