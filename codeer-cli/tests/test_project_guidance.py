"""Evidence-shaped continuation regressions; no customer content or live APIs."""
import copy
import hashlib
import unittest

from codeer_cli.project import fingerprint, read_json, save_json
from test_project_evidence import EvidenceFixture


class GuidanceTests(EvidenceFixture, unittest.TestCase):
    def tree_hashes(self):
        return {str(p.relative_to(self.root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.root.rglob("*") if p.is_file()}

    def test_unverified_contracts_resume_fixture(self):
        project, _ = self.prepare()
        # Same dependency shape as a large customer FAQ project, synthetic inputs.
        testers = []
        for tid, variables in (("answer", ("input", "output", "rubric", "conversation")),
                               ("actions", ("tool_steps", "action_state", "output", "rubric"))):
            testers.append({"local_id": tid, "name": tid, "rationale": "Synthetic candidate purpose",
                            "system_prompt_template": "Judge " + " ".join("{" + v + "}" for v in variables),
                            "evidence": [{"variable": v, "producer": "unconfirmed runtime contract",
                                          "availability": "unresolved"} for v in variables]})
        cases = []
        facts = []
        for i in range(52):
            plan = f"P{i + 1:02}"
            months = i + 6
            days = i + 7
            fact = f"方案 {plan}：購買日起可使用 {months} 個月；退課需在購買後 {days} 天內交人工審核，Agent 不得保證核准。"
            facts.append(fact)
            required = ["input", "output", "rubric"] + (["conversation"] if i < 6 else [])
            question = f"我剛買了 {plan}，想退課並請真人處理。"
            rubric = f"參考事實：{fact} 必須說明人工審核與期限，不得承諾已退款或核准。"
            if i >= 19:
                question = f"我今天買了 {plan}，可以使用多久？"
                rubric = f"參考事實：{fact} 回答購買日起 {months} 個月即可，不要求額外說明退款。不得編造固定到期日。"
            pairs = [{"tester": "answer", "rubric": rubric, "required_evidence": required}]
            if i < 19:
                pairs.append({"tester": "actions", "rubric": "若可用且獲授權則呼叫人工接手；核對實際結果，未成功不得聲稱已交接；退款不屬於 Agent 權限。",
                              "required_evidence": ["tool_steps", "action_state", "output", "rubric"]})
            case = {"local_id": f"candidate-{i:02}", "input": question,
                    "source": {"document": "sources/documents/sop.md"}, "pairs": pairs}
            if i < 6:
                case["local_design"] = {"user_turns": [question, "我剛才已經說過購買方案了，請沿用，不要再問一次。"],
                                        "note": "Unresolved true multi-turn delivery; not a backend context field"}
                pairs[0]["rubric"] += " 需依真實前文沿用已知方案，不重問；兩次獨立回答不算多輪證據。"
            cases.append(case)
        (project.root / "sources/documents/sop.md").write_text("# Synthetic plan policy\n\n" + "\n".join(facts))
        save_json(project.path("evals"), {"schema_version": 1, "testers": testers, "cases": cases})
        (project.root / "evals/cases.draft.md").write_text(
            "# Synthetic acceptance candidates\n52 authored scenarios; multi-turn and action contracts unresolved.\n"
            "All requirements remain in scope. No authorization to deploy or run.\n")
        project.path("design").parent.mkdir(parents=True, exist_ok=True)
        project.path("design").write_text("# Synthetic support design\n回答方案期限、協助退課與真人要求。依方案辨認適用規則；退款由人工核定，未知方案先澄清。已知前文不重問；未觀察到成功不得聲稱交接完成。\n")
        project.path("instructions").write_text("依 KB 核對指定方案並回答問題，方案不明才澄清。退課說明期限及人工核定；真人要求依可用授權能力處理，未成功不得宣稱交接完成。未知能力如實說明，沿用已知前文。\n")
        project.path("sources").write_text("# Sources\nSynthetic SOP and candidate provenance are retained locally.\n")
        (project.root / "kb").mkdir(exist_ok=True)
        (project.root / "kb/facts.md").write_text("# Synthetic plan facts\nSource: sources/documents/sop.md\n\n" + "\n".join(facts))
        (project.root / "README.md").write_text(
            "# Synthetic continuation A\nSources, KB, Instructions and acceptance candidates were authored and locally reviewed.\n"
            "See evals/cases.draft.md and evals/design.json. No deployment or runtime evidence exists.\n"
            "The manifest currently retains unresolved candidates; do not silently remove requirements or fabricate verification.\n")
        before = self.tree_hashes()
        calls = len(self.api.calls)
        code, report = self.cli("validate")
        self.assertEqual(code, 1)
        self.assertTrue(report["structurally_valid"])
        evaluation = report["eval_design"]
        self.assertFalse(evaluation["design_complete"])
        self.assertFalse(evaluation["apply_ready"])
        self.assertEqual(evaluation["pair_count"], 71)
        self.assertEqual(len(report["evidence_issues"]), 238)
        self.assertEqual(len(evaluation["evidence_gaps"]), 8)
        answer_input = next(g for g in evaluation["evidence_gaps"] if g["tester"] == "answer" and g["variable"] == "input")
        self.assertEqual(len(answer_input["affected_pairs"]), 52)
        _, status = self.cli("status")
        self.assertEqual(status["next_action"]["code"], "verify_evidence_contracts")
        self.assertFalse(status["structural_issues"])
        self.assertEqual(len(status["next_action"]["evidence"]), 8)
        self.assertEqual(status["evidence_issue_count"], 238)
        self.assertNotIn("affected_pairs", status["eval_design"]["evidence_gaps"][0])
        self.assertEqual(len(self.cli("status", "--full")[1]["evidence_issues"]), 238)
        self.assertEqual(self.cli("status")[1]["next_action"], status["next_action"])
        self.assertEqual(self.tree_hashes(), before)
        self.assertEqual(len(self.api.calls), calls)
        # Presentation changes cannot waive existing apply/run gates.
        self.assertEqual(self.cli("eval", "cases-apply", "--dry-run")[0], 2)
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 2)
        self.assertFalse(self.api.cases)
        self.artifact = project.root

    def test_execution_errors_resume_fixture(self):
        project = self.setup_evidence()
        project.path("instructions").write_text("Call handoff on an explicit human request; answer hours directly. Synthetic applied draft.")
        code, preview = self.cli("agent", "apply", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(self.cli("agent", "apply", "--expect", preview["token"])[0], 0)
        self.audit(project)
        self.api.run_mode = "error"
        code, result = self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
        self.assertEqual(code, 1)
        self.assertEqual(result["counts"], {"error": 2})
        (project.root / "README.md").write_text(
            "# Synthetic continuation B\nAgent and Eval were applied/read back; pre-eval audit and exact run are recorded.\n"
            "Both pairs have execution errors. Inspect runs/ and reviews/current.audit.json.\n"
            "The requested action is diagnosis only, no rerun or publication.\n")
        before = self.tree_hashes()
        calls = len(self.api.calls)
        _, status = self.cli("status")
        self.assertEqual(status["next_action"]["code"], "diagnose_execution")
        self.assertTrue(status["audit"]["valid_at_last_remote_query"])
        self.assertFalse(status["local_changes"])
        self.assertEqual(status["latest_run"]["id"], result["id"])
        self.assertEqual(self.cli("status")[1]["next_action"], status["next_action"])
        self.assertEqual(self.tree_hashes(), before)
        self.assertEqual(len(self.api.calls), calls)
        self.assertEqual(self.cli("agent", "publish", "--history", "h1", "--dry-run")[0], 2)
        self.artifact = project.root

    def test_quality_failure_and_execution_error_have_different_actions(self):
        self.setup_evidence()
        self.api.run_mode = "failed"
        self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
        self.assertEqual(self.cli("status")[1]["next_action"]["code"], "diagnose_results")

    def test_expired_audit_keeps_passing_run_and_recovers_publication(self):
        for mode in ("edited_report", "missing_report", "blocked_metadata", "missing_metadata"):
            with self.subTest(mode=mode):
                project = self.setup_evidence()
                code, result = self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
                self.assertEqual(code, 0)
                run_path = project.root / "runs" / result["id"] / "run.json"
                original_bytes = run_path.read_bytes()
                trigger_count = self.api.run_number
                metadata_path = project.root / "reviews/current.audit.json"
                report_path = project.root / "reviews/audit.md"
                if mode == "edited_report":
                    report_path.write_text("Changed semantic review; previous fingerprint no longer matches")
                elif mode == "missing_report":
                    report_path.unlink()
                elif mode == "blocked_metadata":
                    metadata = read_json(metadata_path)
                    save_json(metadata_path, {**metadata, "conclusion": "blocked"})
                else:
                    metadata_path.unlink()
                _, status = self.cli("status")
                self.assertFalse(status["audit"]["valid_at_last_remote_query"])
                self.assertFalse(status["latest_run"]["local_stale"])
                self.assertFalse(status["latest_run"]["remote_stale_at_last_query"])
                self.assertEqual(status["next_action"]["code"], "renew_audit")
                self.assertEqual(self.cli("agent", "publish", "--history", "h1", "--dry-run")[0], 2)
                # Renewed semantic clearance is a separate prerequisite, not a rerun.
                self.audit(project)
                self.assertEqual(self.cli("status")[1]["next_action"]["code"], "review_acceptance")
                code, plan = self.cli("agent", "publish", "--history", "h1", "--dry-run")
                self.assertEqual(code, 0, plan)
                self.assertEqual(plan["run"]["id"], result["id"])
                self.assertEqual(run_path.read_bytes(), original_bytes)
                self.assertEqual(self.api.run_number, trigger_count)

    def test_published_run_stays_observable_if_old_audit_missing(self):
        project = self.setup_evidence()
        self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
        _, plan = self.cli("agent", "publish", "--history", "h1", "--dry-run")
        self.assertEqual(self.cli("agent", "publish", "--history", "h1", "--expect", plan["token"])[0], 0)
        (project.root / "reviews/audit.md").unlink()
        _, status = self.cli("status")
        self.assertFalse(status["audit"]["valid_at_last_remote_query"])
        self.assertEqual(status["next_action"]["code"], "observe")

    def test_valid_acceptance_audit_does_not_require_exploratory_pairs(self):
        project = self.setup_evidence()
        acceptance = read_json(project.path("acceptance"))
        acceptance["pairs"] = acceptance["pairs"][:1]
        source = project.root / "reviews/acceptance.md"
        source.write_text("Synthetic approval: first pair is required; second is exploratory.")
        content = {k: v for k, v in acceptance.items() if k != "confirmation"}
        acceptance["confirmation"].update(source_fingerprint=fingerprint(source.read_text()),
                                          scope_fingerprint=fingerprint(content))
        save_json(project.path("acceptance"), acceptance)
        self.audit(project)
        _, run = self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
        metadata_path = project.root / "reviews/current.audit.json"
        metadata = read_json(metadata_path)
        metadata["pairs"] = metadata["pairs"][:1]
        save_json(metadata_path, metadata)
        code, plan = self.cli("agent", "publish", "--history", "h1", "--dry-run")
        self.assertEqual(code, 0, plan)
        self.assertEqual(plan["run"]["id"], run["id"])
        _, status = self.cli("status")
        self.assertFalse(status["audit"]["valid_at_last_remote_query"])
        self.assertTrue(status["audit"]["valid_for_acceptance_at_last_query"])
        self.assertEqual(status["next_action"]["code"], "review_acceptance")

    def test_changed_configuration_needs_new_run_even_with_renewed_audit(self):
        project = self.setup_evidence()
        _, result = self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
        run_path = project.root / "runs" / result["id"] / "run.json"
        original_bytes = run_path.read_bytes()
        project.path("instructions").write_text("A changed behavior proposal, then applied")
        self.api.bump_versions = True
        _, preview = self.cli("agent", "apply", "--dry-run")
        self.assertEqual(self.cli("agent", "apply", "--expect", preview["token"])[0], 0)
        self.audit(project, "h2")
        self.assertEqual(self.cli("status")[1]["next_action"]["code"], "renew_verification")
        self.assertEqual(self.cli("agent", "publish", "--history", "h2", "--dry-run")[0], 2)
        self.assertEqual(run_path.read_bytes(), original_bytes)
        self.assertEqual(self.api.run_number, 1)

    def test_unconfirmed_acceptance_reviews_scope_without_rerunning(self):
        project = self.setup_evidence()
        _, result = self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
        run_path = project.root / "runs" / result["id"] / "run.json"
        original_bytes = run_path.read_bytes()
        # Confirmation evidence can expire without changing the evaluated content.
        (project.root / "reviews/acceptance.md").write_text("Updated acceptance discussion; not yet confirmed")
        _, status = self.cli("status")
        self.assertFalse(status["latest_run"]["local_stale"])
        self.assertIsNone(status["audit"]["valid_for_acceptance_at_last_query"])
        self.assertTrue(status["audit"]["valid_for_latest_run_at_last_query"])
        self.assertEqual(status["next_action"]["code"], "review_acceptance")
        self.assertEqual(self.cli("agent", "publish", "--history", "h1", "--dry-run")[0], 2)
        self.assertEqual(run_path.read_bytes(), original_bytes)
        self.assertEqual(self.api.run_number, 1)

    def test_unknown_run_requires_reconciliation_before_retry(self):
        project = self.setup_evidence()
        self.api.run_mode = "trigger_timeout"
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 1)
        _, status = self.cli("status")
        self.assertEqual(status["next_action"]["code"], "reconcile_run")
        triggers = self.api.run_number
        self.assertEqual(self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")[0], 2)
        self.assertEqual(self.api.run_number, triggers)
        self.assertEqual(len(list((project.root / "runs").glob("*/run.json"))), 1)

    def test_new_local_change_retains_error_and_invalidates_only_verification(self):
        project = self.setup_evidence()
        self.api.run_mode = "error"
        self.cli("eval", "run", "--history", "h1", "--poll-timeout", "0")
        project.path("instructions").write_text("New local proposal, not yet applied")
        _, status = self.cli("status")
        self.assertEqual(status["next_action"]["code"], "review_local_changes")
        self.assertTrue(status["latest_run"]["local_stale"])
        self.assertEqual(status["latest_run"]["counts"], {"error": 2})
        self.assertFalse(status["audit"]["local_revision_valid"])

    def test_missing_audit_and_ready_audit_choose_different_prerequisites(self):
        project, _ = self.prepare()
        self.apply_design()
        self.assertEqual(self.cli("status")[1]["next_action"]["code"], "pre_eval_audit")
        self.audit(project)
        self.assertEqual(self.cli("status")[1]["next_action"]["code"], "run_baseline")

    def test_schema_error_stays_structural_and_missing_delivery_stays_unresolved(self):
        project, design = self.prepare()
        malformed = copy.deepcopy(design)
        malformed["cases"][0]["pairs"] = None
        save_json(project.path("evals"), malformed)
        code, report = self.cli("validate")
        self.assertEqual(code, 1)
        self.assertFalse(report["structurally_valid"])
        self.assertEqual(self.cli("status")[1]["next_action"]["code"], "repair_structure")
        design["testers"][0]["evidence"][0]["verification"] = "reviews/absent.md"
        save_json(project.path("evals"), design)
        self.assertFalse(self.cli("validate")[1]["structurally_valid"])
        self.assertEqual(self.cli("eval", "cases-apply", "--dry-run")[0], 2)

    def test_pending_operation_takes_precedence_over_evidence_gaps(self):
        project, design = self.prepare()
        design["testers"][0]["evidence"][0]["availability"] = "unresolved"
        save_json(project.path("evals"), design)
        state = project.state()
        state["resources"]["tester:tools"] = {"status": "outcome_unknown"}
        project.save_state(state)
        self.assertEqual(self.cli("status")[1]["next_action"]["code"], "reconcile_resources")
        report = self.cli("validate")[1]
        self.assertTrue(report["operation_issues"])
        self.assertFalse(report["eval_design"]["apply_ready"])

    def test_portable_offline_design_classification(self):
        # The shared validator/guidance also runs without a selected deployment.
        self.cli("init", str(self.root / "portable"))
        from codeer_cli.project import Project
        project = Project.load(self.root / "portable")
        save_json(project.path("evals"), {"schema_version": 1, "testers": [], "cases": []})
        report = project.validation()
        self.assertFalse(report["eval_design"]["design_complete"])
        self.assertFalse(report["structural_issues"])
        self.assertEqual(project.status()["next_action"]["code"], "complete_case_draft")
        self.assertEqual(project.state().get("resources", {}), {})
