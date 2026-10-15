"""Guided development on synthetic existing projects; no live customer data."""
import contextlib
import copy
import hashlib
import io
import os
import shutil
import unittest

from codeer_cli.cli import main
from codeer_cli.project import Project, read_json, save_json
from test_project_evidence import EvidenceFixture


def tree_bytes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


class GuidedProjectTests(EvidenceFixture, unittest.TestCase):
    def test_partial_baseline_pin_survives_resume_export_without_changing_original_project(self):
        project = self.setup_evidence()
        original = tree_bytes(project.root)
        clone = project.root.parent / (project.root.name + '-baseline-clone')
        shutil.copytree(project.root, clone)
        self.addCleanup(shutil.rmtree, clone)
        os.chdir(clone)
        project = Project.load(clone)
        self.api.run_mode = 'missing_evidence'
        code, run = self.cli('eval', 'run', '--history', 'h1', '--poll-timeout', '0')
        self.assertEqual(code, 1)
        self.assertEqual(run['status'], 'incomplete')
        self.assertEqual(run['counts'], {'unjudgeable': 2})
        run_path = clone / 'runs' / run['id'] / 'run.json'
        captured = run_path.read_bytes()
        captured_hash = hashlib.sha256(captured).hexdigest()
        batch = clone / 'reviews/batches/first-baseline'
        pin = batch / 'baseline' / f"{run['id']}-{captured_hash}.json"
        pin.parent.mkdir(parents=True)
        # Follow the skill's local byte-snapshot protocol, not a new CLI format.
        with pin.open('xb') as stream:
            stream.write(captured)
        (batch / 'report.md').write_text(
            f"Synthetic pre-repair observation, not acceptance: {pin.relative_to(clone)}\n"
            f"SHA-256: {captured_hash}\nRun: {run['id']}; history: h1; status: incomplete\n"
            f"Result IDs: {read_json(pin)['result_ids']}\n")
        before_read = tree_bytes(clone)
        before_calls = len(self.api.calls)
        self.assertEqual(self.cli('status')[0], 0)
        self.assertEqual(self.cli('eval', 'inspect-run', '--run-id', run['id'])[1]['derived_counts'],
                         {'unjudgeable': 2})
        # Reuse the same verified pin; a fresh create must not overwrite it.
        self.assertEqual(pin.read_bytes(), captured)
        self.assertEqual(hashlib.sha256(pin.read_bytes()).hexdigest(), captured_hash)
        with self.assertRaises(FileExistsError):
            pin.open('xb')
        self.assertEqual(tree_bytes(clone), before_read)
        self.assertEqual(len(self.api.calls), before_calls)
        self.assertEqual(self.cli('agent', 'publish', '--history', 'h1', '--dry-run')[0], 2)
        self.assertEqual(run_path.read_bytes(), captured)

        project.path('instructions').write_text('Synthetic local repair after initial diagnosis')
        triggers = self.api.run_number
        code, exported = self.cli('eval', 'export', '--run-id', run['id'], '--out-dir', str(clone / 'exports'))
        self.assertEqual(code, 1)
        self.assertTrue(exported['record_updated'])
        self.assertEqual(exported['status'], 'stale')
        self.assertNotEqual(run_path.read_bytes(), captured)
        self.assertEqual(pin.read_bytes(), captured)
        self.assertEqual(read_json(pin)['status'], 'incomplete')
        self.assertEqual(read_json(pin)['counts'], {'unjudgeable': 2})
        self.assertEqual(sorted(str(p.relative_to(batch)) for p in batch.rglob('*') if p.is_file()),
                         [f'baseline/{pin.name}', 'report.md'])
        self.assertEqual(self.api.run_number, triggers)
        self.assertEqual(self.cli('agent', 'publish', '--history', 'h1', '--dry-run')[0], 2)
        self.assertEqual(tree_bytes(self.root), original)
        self.artifact = clone

    def test_existing_clone_batch_audit_status_run_publish_and_readonly_resume(self):
        project = self.setup_evidence()
        original = tree_bytes(project.root)
        clone = project.root.parent / (project.root.name + '-clone')
        shutil.copytree(project.root, clone)
        self.addCleanup(shutil.rmtree, clone)
        os.chdir(clone)
        project = Project.load(clone)
        report = clone / 'reviews/audit.md'
        metadata = read_json(clone / 'reviews/current.audit.json')
        batch = clone / 'reviews/batches/2026-10-first-test'
        batch.mkdir(parents=True)
        report.rename(batch / 'report.md')
        metadata['report'] = 'reviews/batches/2026-10-first-test/report.md'
        save_json(batch / 'current.audit.json', metadata)
        (clone / 'reviews/current.audit.json').unlink()
        before = tree_bytes(clone)
        self.assertTrue(self.cli('status')[1]['audit']['valid_at_last_remote_query'])
        output = io.StringIO()
        calls = len(self.api.calls)
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(['status', '--human']), 0)
        self.assertIn('Next:', output.getvalue())
        self.assertIn('Offline', output.getvalue())
        self.assertEqual(tree_bytes(clone), before)
        self.assertEqual(len(self.api.calls), calls)
        code, run = self.cli('eval', 'run', '--history', 'h1', '--poll-timeout', '0')
        self.assertEqual(code, 0)
        fixed = clone / 'runs' / run['id'] / 'run.json'
        fixed_bytes = fixed.read_bytes()
        code, exported = self.cli('eval', 'export', '--run-id', run['id'], '--out-dir', str(clone / 'exports'))
        self.assertEqual(code, 0)
        self.assertFalse(exported['record_updated'])
        self.assertEqual(fixed.read_bytes(), fixed_bytes)
        code, preview = self.cli('agent', 'publish', '--history', 'h1', '--dry-run')
        self.assertEqual(code, 0)
        code, release = self.cli('agent', 'publish', '--history', 'h1', '--expect', preview['token'])
        self.assertEqual(code, 0)
        delivery = clone.parent / (clone.name + '-delivery')
        self.addCleanup(shutil.rmtree, delivery)
        code, bundle = self.cli('eval', 'delivery', '--run-id', run['id'], '--release-id', release['id'], '--out-dir', str(delivery))
        self.assertEqual(code, 0, bundle)
        self.assertEqual(self.cli('eval', 'delivery', '--verify', str(delivery))[0], 0)
        (batch / 'report.md').write_text('Changed finding invalidates the previous review')
        self.assertFalse(self.cli('status')[1]['audit']['valid_at_last_remote_query'])
        self.assertEqual(self.cli('agent', 'publish', '--history', 'h1', '--dry-run')[0], 2)
        self.assertEqual(tree_bytes(self.root), original)
        self.artifact = clone

    def test_archived_and_outside_project_audits_do_not_grant_clearance(self):
        project = self.setup_evidence()
        original = project.root / 'reviews/current.audit.json'
        archived = project.root / 'reviews/evidence/old'
        archived.mkdir(parents=True)
        original.rename(archived / original.name)
        self.assertFalse(self.cli('status')[1]['audit']['valid_at_last_remote_query'])
        outside = project.root.parent / (project.root.name + '-outside.audit.json')
        outside.write_bytes((archived / original.name).read_bytes())
        self.addCleanup(outside.unlink)
        original.symlink_to(outside)
        self.assertEqual(project.audit_paths(), [])
        self.assertEqual(self.cli('eval', 'run', '--history', 'h1', '--poll-timeout', '0')[0], 2)

    def test_static_context_is_exact_snapshot_evidence_and_historical_inspection_is_readonly(self):
        project = self.setup_evidence()
        design = read_json(project.path('evals'))
        tester = design['testers'][0]
        tester['system_prompt_template'] = 'Judge {input} and {output} using {rubric}'
        tester['evidence'] = [dict(variable=v, producer='Synthetic bound runtime', availability='verified',
                                   verification='reviews/evidence.md') for v in ('input', 'output', 'rubric')]
        for case in design['cases']:
            case['pairs'][0]['required_evidence'] = ['input', 'output', 'rubric']
        save_json(project.path('evals'), design)
        self.apply_design()
        self.audit(project)
        code, result = self.cli('eval', 'run', '--history', 'h1', '--poll-timeout', '0')
        self.assertEqual(code, 0, result)
        run_path = project.root / 'runs' / result['id'] / 'run.json'
        record = read_json(run_path)
        from codeer_cli.evidence import classify
        row = record['results'][0]['result']
        self.assertEqual(classify(row, ['input', 'rubric'], run=record), 'passed')
        for change in ('snapshot', 'history', 'pair', 'result'):
            wrong = copy.deepcopy(record)
            sample = copy.deepcopy(row)
            if change == 'snapshot':
                wrong['snapshot']['cases'].clear()
            elif change == 'history':
                sample['agent_history_id'] = 'h0'
            elif change == 'pair':
                sample['evaluator_id'] = 'other'
            else:
                sample['id'] = 'old-result'
            self.assertEqual(classify(sample, ['input', 'rubric'], run=wrong), 'unjudgeable')
            self.assertEqual(classify(sample, ['output'], run=wrong), 'unjudgeable')
        code, preview = self.cli('agent', 'publish', '--history', 'h1', '--dry-run')
        self.assertEqual(code, 0)
        code, release = self.cli('agent', 'publish', '--history', 'h1', '--expect', preview['token'])
        self.assertEqual(code, 0)
        bundle_path = project.root.parent / (project.root.name + '-static-delivery')
        self.addCleanup(shutil.rmtree, bundle_path)
        code, bundle = self.cli('eval', 'delivery', '--run-id', result['id'], '--release-id', release['id'], '--out-dir', str(bundle_path))
        self.assertEqual(code, 0, bundle)
        self.assertEqual(self.cli('eval', 'delivery', '--verify', str(bundle_path))[0], 0)
        # Reproduce a legacy classification defect without rewriting it on inspection.
        record.pop('evidence_contract_version')
        record['status'] = 'incomplete'
        for outcome in record['results']:
            outcome['state'] = 'unjudgeable'
        save_json(run_path, record)
        before = tree_bytes(project.root)
        calls = len(self.api.calls)
        code, inspected = self.cli('eval', 'inspect-run', '--run-id', result['id'])
        self.assertEqual(code, 0)
        self.assertEqual(inspected['recorded_status'], 'incomplete')
        self.assertEqual(inspected['derived_counts'], {'passed': 2})
        self.assertEqual(tree_bytes(project.root), before)
        self.assertEqual(len(self.api.calls), calls)
        swapped = copy.deepcopy(record)
        swapped['results'][0]['result'], swapped['results'][1]['result'] = swapped['results'][1]['result'], swapped['results'][0]['result']
        save_json(run_path, swapped)
        inspected = self.cli('eval', 'inspect-run', '--run-id', result['id'])[1]
        self.assertEqual(inspected['derived_counts'], {'unjudgeable': 2})
        self.assertTrue(all(set(p['evidence_sources'].values()) == {'missing'} for p in inspected['pairs']))
        save_json(run_path, record)
        omitted = copy.deepcopy(record)
        omitted['results'] = []
        save_json(run_path, omitted)
        self.assertEqual(self.cli('eval', 'inspect-run', '--run-id', result['id'])[1]['derived_counts'], {'missing': 2})
        save_json(run_path, record)
        self.assertEqual(tree_bytes(project.root), before)
        self.artifact = project.root


if __name__ == '__main__':
    unittest.main()
