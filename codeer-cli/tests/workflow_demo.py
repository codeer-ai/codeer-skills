"""Reproduce synthetic API journeys and retain their reviewable artifacts."""
import argparse
from pathlib import Path
import shutil

from test_project_workflow import WorkflowTests
from test_project_deployments import DeploymentTests
from test_project_resource_exports import ResourceExportTests
from test_project_guidance import GuidanceTests
from test_project_guided import GuidedProjectTests
from test_project_bindings import BindingCommandsTests
from test_project_fork import TesterForkTests, KBForkTests
from test_project_clean import CleanTests
from test_project_operation_records import OperationRecordsTests
from test_project_upgrade import UpgradeRehearsalTests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.out_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for name, cls, method in (("new-agent", WorkflowTests, "test_new_agent_repair_regression_and_release"),
                              ("existing-agent", WorkflowTests, "test_existing_agent_web_conflict_and_history_candidates"),
                              ("portable-deployments", DeploymentTests, "test_complete_portable_eval_release_delivery_and_environment_isolation"),
                              ("platform-resume", DeploymentTests, "test_platform_resume_fixture"),
                              ("kb-faq-portability", ResourceExportTests, "test_faq_resume_fixture"),
                              ("unverified-contracts", GuidanceTests, "test_unverified_contracts_resume_fixture"),
                              ("execution-errors", GuidanceTests, "test_execution_errors_resume_fixture"),
                              ("guided-existing", GuidedProjectTests, "test_existing_clone_batch_audit_status_run_publish_and_readonly_resume"),
                              ("partial-baseline", GuidedProjectTests, "test_partial_baseline_pin_survives_resume_export_without_changing_original_project"),
                              ("static-context", GuidedProjectTests, "test_static_context_is_exact_snapshot_evidence_and_historical_inspection_is_readonly"),
                              ("agent-bindings", BindingCommandsTests, "test_named_bind_and_offline_listing_with_multiple_agents"),
                              ("tester-separation", TesterForkTests, "test_separates_candidate_without_modifying_shared_source"),
                              ("kb-separation", KBForkTests, "test_separate_files_require_subsequent_agent_and_faq_review"),
                              ("safe-cleanup", CleanTests, "test_exact_nonzero_reclamation_keeps_all_reference_forms_and_fixed_history"),
                              ("record-reduction", OperationRecordsTests, "test_large_receipt_reduces_bytes_and_keeps_actual_recovery_inputs"),
                              ("small-record-reduction", OperationRecordsTests, "test_small_receipt_and_optional_preview_fields_use_the_same_recovery_reader"),
                              ("one-time-preparation", UpgradeRehearsalTests, "test_zero_change_current_contract_and_reviewed_carry_are_idempotent")):
        destination = output / name
        if destination.exists():
            parser.error(f"Use a fresh output directory; exists: {destination}")
        test = cls(method)
        test.setUp()
        try:
            getattr(test, method)()
            shutil.copytree(test.artifact, destination)
            print(f"PASS {name}: {destination}")
        finally:
            test.doCleanups()


if __name__ == "__main__":
    main()
