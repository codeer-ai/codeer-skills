"""Offline advice from recorded prerequisites, never a workflow state authority."""


def next_action(status, *, release_matches_run=False, referenced_kb=()):
    resources = status["resources"]
    run = status["latest_run"]
    release = status["latest_release"]
    evaluation = status["eval_design"]

    def advice(code, evidence, action, completion):
        return {"code": code, "evidence": evidence, "action": action, "completion_condition": completion,
                "limits": "Recorded evidence only; confirm live prerequisites and existing authorization before acting. "
                          "This advice neither approves business scope nor grants mutation/publication permission."}

    unfinished = [k for k, v in resources.items() if v.get("status") in ("pending", "outcome_unknown", "readback_mismatch")]
    if unfinished:
        return advice("reconcile_resources", unfinished,
                      "Inspect unfinished resource receipts and reconcile known identities before another write; do not repeat unknown creates.",
                      "Recorded operations have verified outcomes; unknown identities are explicitly resolved before retry.")
    if release and release.get("status") in ("pending", "outcome_unknown", "readback_mismatch"):
        return advice("reconcile_publication", [release.get("id")],
                      "Previous publication is unresolved; inspect its receipt and run agent publish --reconcile before retrying.",
                      "Publication readback is reconciled without losing the original receipt.")
    if run and run.get("status") in ("triggering", "polling", "outcome_unknown"):
        return advice("reconcile_run", [run.get("id"), run.get("status")],
                      "Inspect the unfinished run and reconcile its exact result IDs before triggering another run.",
                      "Every recorded trigger/result identity has a known outcome; unknown triggers are investigated before retry.")
    if status["structural_issues"]:
        return advice("repair_structure", status["structural_issues"],
                      "Resolve structural issues before apply or validation clearance.",
                      "Configured files and references pass structural validation; evidence and semantic review remain separate.")
    if status["evidence_issues"]:
        return advice("verify_evidence_contracts", evaluation["evidence_gaps"],
                      "Verify the shared Tester evidence producer/delivery contracts, then admit supported pairs into the configured manifest; keep unresolved candidates in the Markdown draft.",
                      "Each admitted pair has reviewed Tester suitability, rubric and evidence contracts; deferred requirements remain visible and acceptance scope is preserved.")
    if status["design_issues"]:
        return advice("complete_case_draft", status["design_issues"],
                      "Recover existing case drafts and the intended behavior, then review Tester/evidence decisions before admitting pairs; do not restart established design.",
                      "A reviewed admitted manifest exists, with unresolved candidates and acceptance gaps retained in the draft.")
    if evaluation and evaluation["design_complete"] and not resources.get("agent", {}).get("server_id"):
        return advice("prepare_deployment", ["local Eval manifest checks passed; no recorded Agent mapping"],
                      "Check deployment capabilities and mappings, preview local Agent/KB/Eval proposals, then apply only authorized changes and verify readback.",
                      "Required resources have explicit mappings and matching readback; local checks do not establish semantic acceptance.")
    if status["local_changes"]:
        return advice("review_local_changes", status["local_changes"],
                      "Review local proposals and compare current remote changes before apply.",
                      "The reviewed, authorized changes have matching readback; only affected audit/run evidence is renewed.")
    if run and (run.get("local_stale") or run.get("remote_stale_at_last_query") or run.get("status") == "stale"):
        return advice("renew_verification", [run.get("id"), "configuration evidence changed"],
                      "Identify changes since this run, review their affected scope and renew audit/run evidence for the intended version.",
                      "Current version and pair scope have valid audit and matching run evidence; unchanged design is retained.")
    not_ready = [k for k, v in resources.items() if k.startswith("kb:")
                 and set(referenced_kb).intersection({v.get("server_id"), *v.get("node_ids", [])})
                 and v.get("status") != "ready"]
    if not_ready:
        return advice("verify_kb_readiness", not_ready,
                      "Read back the managed KB readiness and recorded upload identities before pre-eval clearance.",
                      "Referenced managed KB files are READY and their current content matches the reviewed sources.")
    if run and run.get("counts", {}).get("error"):
        return advice("diagnose_execution", [run.get("id"), run.get("counts")],
                      "Inspect exact run errors and execution dependencies before interpreting quality scores. After recovery, verify current prerequisites and rerun within authorization.",
                      "The evidenced execution fault is resolved and matching audit/version prerequisites permit a new run; errors are not treated as answer-quality failures.")
    if run and run.get("status") in ("failed", "incomplete"):
        return advice("diagnose_results", [run.get("id"), run.get("counts")],
                      "Inspect exact failed, missing, skipped or unjudgeable results; distinguish quality findings from evidence/execution gaps before proposing repair.",
                      "Findings identify evidence, consequence and affected owner; any repair has a reviewed diff and regression scope.")
    current_pass = run and run.get("status") == "passed"
    if current_pass and release_matches_run and release.get("status") in ("published", "published_reconciled"):
        return advice("observe", [run.get("id"), release.get("id")],
                      "Recorded release readback is complete; observe production feedback when requested. Live remote state is not checked.",
                      "Requested observation is scoped and evidence-backed; no new publication is implied.")
    if current_pass:
        audit_valid = status["audit"].get("valid_for_acceptance_at_last_query")
        if audit_valid is None:
            audit_valid = status["audit"].get("valid_for_latest_run_at_last_query",
                                             status["audit"]["valid_at_last_remote_query"])
        if not audit_valid:
            return advice("renew_audit", [run.get("id"), "matching audit missing or invalid"],
                          "Review and renew the semantic audit for the exact version and intended pairs, retaining this passing run. Do not rerun Eval solely to repair audit evidence.",
                          "A current matching audit and acceptance coverage are verified; reuse the unchanged run/results unless new findings require configuration or coverage changes.")
        return advice("review_acceptance", [run.get("id")],
                      "Review semantic evidence and confirmed acceptance coverage; publish only within explicit authorization.",
                      "The confirmed acceptance set is covered for the exact version, with separate publication authorization.")
    if evaluation and evaluation["design_complete"]:
        if not status["audit"]["valid_at_last_remote_query"]:
            return advice("pre_eval_audit", ["no matching audit for the last recorded remote snapshot"],
                          "Verify effective Agent/KB/Tester/Case readback, then complete a scoped pre-eval audit against the exact version and intended pairs.",
                          "Current readback and semantic audit cover the intended version and pairs; cached status alone cannot grant clearance.")
        return advice("run_baseline", ["matching audit at last remote query"],
                      "Verify current version, dependencies and pair scope, then run the baseline within existing authorization.",
                      "An exact-version run records every intended pair outcome; completion and passing are reported separately.")
    return advice("recover_design_basis", ["no checked Eval manifest"],
                  "Read existing sources, established design, pending decisions and case drafts; identify the missing design or capability prerequisite without repeating completed work.",
                  "The relevant draft and capability gaps have a concrete next action; file presence and imported state do not establish acceptance.")
