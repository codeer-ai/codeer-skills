from __future__ import annotations

import contextlib
import io
import json
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import httpx

from codeer_cli import skills
from codeer_cli.cli import main

COMMIT = "a" * 40
NAME = "codeer-agent"
MANIFEST = b"---\nname: codeer-agent\ndescription: Agent workflows.\n---\n# Agent\n"
FILES = {"SKILL.md": (MANIFEST, 0o644), "scripts/check.py": (b"print('ok')\n", 0o755)}


def archive(entries=None, *, name=NAME, commit=COMMIT):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as bundle:
        for relative, (content, mode) in (entries or FILES).items():
            info = zipfile.ZipInfo(f"codeer-skills-{commit}/skills/{name}/{relative}")
            info.external_attr = mode << 16
            bundle.writestr(info, content)
    return stream.getvalue()


class SkillLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.addCleanup(self.temporary.cleanup)
        home = patch.object(Path, "home", return_value=self.root / "home")
        cwd = patch.object(Path, "cwd", return_value=self.root / "project")
        fetch = patch.object(skills, "_fetch_skill", return_value=(COMMIT, FILES))
        home.start()
        cwd.start()
        self.fetch = fetch.start()
        self.addCleanup(home.stop)
        self.addCleanup(cwd.stop)
        self.addCleanup(fetch.stop)

    def destination(self, target="codex", scope="user"):
        return skills.skill_root(target, scope) / NAME

    def test_target_and_scope_paths(self):
        for target, folder in (("codex", ".agents"), ("claude", ".claude")):
            for scope, base in (("user", "home"), ("project", "project")):
                self.assertEqual(
                    skills.skill_root(target, scope),
                    self.root / base / folder / "skills",
                )

    def test_install_copies_support_files_and_records_hashes(self):
        result = skills.install(NAME, target="codex")
        destination = self.destination()
        self.assertEqual(result["status"], "installed")
        self.assertEqual(
            (destination / "scripts/check.py").read_bytes(),
            FILES["scripts/check.py"][0],
        )
        self.assertTrue(
            (destination / "scripts/check.py").stat().st_mode & stat.S_IXUSR
        )
        receipt = json.loads((destination / skills.RECEIPT).read_text())
        self.assertEqual(receipt["commit"], COMMIT)
        self.assertEqual(receipt["files"], skills._fingerprint(destination))

    def test_install_dry_run_does_not_create_target_directories(self):
        result = skills.install(
            NAME, target="claude", scope="project", ref="release", dry_run=True
        )
        self.assertEqual(result["status"], "would_install")
        self.assertFalse((self.root / "project").exists())
        self.fetch.assert_called_once_with(NAME, "release")

    def test_repeated_identical_install_is_noop(self):
        skills.install(NAME, target="codex")
        before = (self.destination() / skills.RECEIPT).read_bytes()
        self.fetch.return_value = ("b" * 40, FILES)
        result = skills.install(NAME, target="codex")
        self.assertEqual(result["status"], "already_installed")
        self.assertEqual(result["installed_commit"], COMMIT)
        self.assertEqual((self.destination() / skills.RECEIPT).read_bytes(), before)

    def test_install_updates_entire_package_and_receipt(self):
        skills.install(NAME, target="codex")
        other = self.destination().parent / "unrelated"
        other.mkdir()
        (other / "keep.txt").write_text("keep")
        self.fetch.return_value = (
            "b" * 40,
            {"SKILL.md": (MANIFEST + b"Changed", 0o644)},
        )
        result = skills.install(NAME, target="codex", ref="release")
        self.assertEqual(result["status"], "updated")
        self.assertEqual(result["previous_commit"], COMMIT)
        self.assertEqual(
            (self.destination() / "SKILL.md").read_bytes(), MANIFEST + b"Changed"
        )
        self.assertFalse((self.destination() / "scripts").exists())
        receipt = json.loads((self.destination() / skills.RECEIPT).read_text())
        self.assertEqual(receipt["commit"], "b" * 40)
        self.assertEqual(receipt["ref"], "release")
        self.assertEqual(receipt["files"], skills._fingerprint(self.destination()))
        self.assertEqual((other / "keep.txt").read_text(), "keep")
        self.assertEqual(
            sorted(p.name for p in other.parent.iterdir()), [NAME, "unrelated"]
        )
        self.assertEqual(
            skills.uninstall(NAME, target="codex")["status"], "uninstalled"
        )

    def test_update_dry_run_keeps_old_files_and_receipt(self):
        skills.install(NAME, target="codex")
        before = (self.destination() / skills.RECEIPT).read_bytes()
        self.fetch.return_value = (
            "b" * 40,
            {"SKILL.md": (MANIFEST + b"Changed", 0o644)},
        )
        result = skills.install(NAME, target="codex", dry_run=True)
        self.assertEqual(result["status"], "would_update")
        self.assertEqual(result["previous_commit"], COMMIT)
        self.assertEqual((self.destination() / skills.RECEIPT).read_bytes(), before)
        self.assertEqual((self.destination() / "SKILL.md").read_bytes(), MANIFEST)
        self.assertTrue((self.destination() / "scripts/check.py").exists())
        self.assertEqual(
            list(self.destination().parent.iterdir()), [self.destination()]
        )

    def test_download_failure_preserves_installed_package(self):
        skills.install(NAME, target="codex")
        before = skills._fingerprint(self.destination())
        self.fetch.side_effect = skills.SkillError("Download failed")
        with self.assertRaisesRegex(skills.SkillError, "Download failed"):
            skills.install(NAME, target="codex")
        self.assertEqual(skills._fingerprint(self.destination()), before)

    def test_failed_update_restores_old_package(self):
        skills.install(NAME, target="codex")
        before = (self.destination() / skills.RECEIPT).read_bytes()
        self.fetch.return_value = (
            "b" * 40,
            {"SKILL.md": (MANIFEST + b"Changed", 0o644)},
        )
        rename = Path.rename

        def fail_receipt(source, target):
            if (
                source.name == skills.RECEIPT
                and Path(target) == self.destination() / skills.RECEIPT
            ):
                raise OSError("Simulated publication failure")
            return rename(source, target)

        with (
            patch.object(Path, "rename", fail_receipt),
            self.assertRaisesRegex(OSError, "publication failure"),
        ):
            skills.install(NAME, target="codex")
        self.assertEqual((self.destination() / skills.RECEIPT).read_bytes(), before)
        self.assertEqual(
            skills._fingerprint(self.destination()), json.loads(before)["files"]
        )
        self.assertEqual(
            list(self.destination().parent.iterdir()), [self.destination()]
        )

    def test_failed_restore_retains_backup_for_manual_recovery(self):
        skills.install(NAME, target="codex")
        self.fetch.return_value = (
            "b" * 40,
            {"SKILL.md": (MANIFEST + b"Changed", 0o644)},
        )
        rename = Path.rename

        def fail_publication_and_restore(source, target):
            if Path(target) in (self.destination(), self.destination() / "SKILL.md"):
                raise OSError("Simulated filesystem failure")
            return rename(source, target)

        with (
            patch.object(Path, "rename", fail_publication_and_restore),
            self.assertRaisesRegex(skills.SkillError, "backup"),
        ):
            skills.install(NAME, target="codex")
        backups = list(self.destination().parent.glob(".codeer-skill-backup-*/" + NAME))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "SKILL.md").read_bytes(), MANIFEST)
        self.assertEqual(
            skills._read_receipt(backups[0], NAME)["files"],
            skills._fingerprint(backups[0]),
        )

    def test_local_edit_during_download_blocks_update(self):
        skills.install(NAME, target="codex")

        def fetch_with_local_edit(name, ref):
            (self.destination() / "notes.md").write_text("local notes")
            return "b" * 40, {"SKILL.md": (MANIFEST + b"Changed", 0o644)}

        self.fetch.side_effect = fetch_with_local_edit
        with self.assertRaisesRegex(skills.SkillError, "local changes"):
            skills.install(NAME, target="codex")
        self.assertEqual((self.destination() / "notes.md").read_text(), "local notes")
        self.assertEqual((self.destination() / "SKILL.md").read_bytes(), MANIFEST)

    def test_staging_failure_keeps_old_package(self):
        skills.install(NAME, target="codex")
        before = (self.destination() / skills.RECEIPT).read_bytes()
        self.fetch.return_value = (
            "b" * 40,
            {"SKILL.md": (MANIFEST + b"Changed", 0o644)},
        )
        with (
            patch.object(Path, "write_bytes", side_effect=OSError("Disk full")),
            self.assertRaisesRegex(OSError, "Disk full"),
        ):
            skills.install(NAME, target="codex")
        self.assertEqual((self.destination() / skills.RECEIPT).read_bytes(), before)
        self.assertEqual(
            skills._fingerprint(self.destination()), json.loads(before)["files"]
        )

    def test_local_edit_during_staging_blocks_update(self):
        skills.install(NAME, target="codex")
        self.fetch.return_value = (
            "b" * 40,
            {"SKILL.md": (MANIFEST + b"Changed", 0o644)},
        )
        write_bytes = Path.write_bytes

        def write_with_local_edit(path, data):
            (self.destination() / "notes.md").write_text("local notes")
            return write_bytes(path, data)

        with (
            patch.object(Path, "write_bytes", write_with_local_edit),
            self.assertRaisesRegex(skills.SkillError, "local changes"),
        ):
            skills.install(NAME, target="codex")
        self.assertEqual((self.destination() / "notes.md").read_text(), "local notes")
        self.assertEqual((self.destination() / "SKILL.md").read_bytes(), MANIFEST)

    def test_cli_reports_preview_and_successful_update(self):
        skills.install(NAME, target="codex")
        self.fetch.return_value = (
            "b" * 40,
            {"SKILL.md": (MANIFEST + b"Changed", 0o644)},
        )
        for flags, expected in ((["--dry-run"], "would_update"), ([], "updated")):
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(
                    main(["skill", "install", NAME, "--target", "codex", *flags]), 0
                )
            self.assertEqual(json.loads(stdout.getvalue())["status"], expected)

    def test_manual_install_is_neither_overwritten_nor_removed(self):
        destination = self.destination()
        destination.mkdir(parents=True)
        (destination / "SKILL.md").write_bytes(MANIFEST)
        for operation in (skills.install, skills.uninstall):
            with self.assertRaisesRegex(skills.SkillError, "Unmanaged"):
                operation(NAME, target="codex")
        self.fetch.assert_not_called()
        self.assertEqual((destination / "SKILL.md").read_bytes(), MANIFEST)

    def test_modified_missing_or_added_files_block_update_and_removal(self):
        for change in ("modified", "missing", "added"):
            with self.subTest(change=change):
                target = "codex" if change != "missing" else "claude"
                scope = "project" if change == "added" else "user"
                skills.install(NAME, target=target, scope=scope)
                destination = self.destination(target, scope)
                if change == "modified":
                    (destination / "SKILL.md").write_text("local work")
                elif change == "missing":
                    (destination / "SKILL.md").unlink()
                else:
                    (destination / "notes.md").write_text("local notes")
                for operation in (skills.install, skills.uninstall):
                    with self.assertRaisesRegex(skills.SkillError, "local changes"):
                        operation(NAME, target=target, scope=scope)
                self.assertTrue(destination.exists())

    def test_uninstall_preview_then_remove_only_selected_skill(self):
        skills.install(NAME, target="codex")
        other = self.destination().parent / "unrelated"
        other.mkdir()
        (other / "keep.txt").write_text("keep")
        result = skills.uninstall(NAME, target="codex", dry_run=True)
        self.assertEqual(result["status"], "would_uninstall")
        self.assertTrue(self.destination().exists())
        self.assertEqual(
            skills.uninstall(NAME, target="codex")["status"], "uninstalled"
        )
        self.assertEqual((other / "keep.txt").read_text(), "keep")

    def test_added_empty_directory_blocks_removal(self):
        skills.install(NAME, target="codex")
        (self.destination() / "local-notes").mkdir()
        with self.assertRaisesRegex(skills.SkillError, "local changes"):
            skills.uninstall(NAME, target="codex")
        self.assertEqual(
            skills.list_skills(target="codex")[0]["installations"][0]["status"],
            "modified",
        )

    def test_uninstall_missing_is_noop(self):
        self.assertEqual(
            skills.uninstall(NAME, target="codex")["status"], "not_installed"
        )
        self.assertFalse((self.root / "home").exists())

    def test_symlinked_target_or_ancestor_is_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        parent = self.destination().parent
        parent.mkdir(parents=True)
        self.destination().symlink_to(outside, target_is_directory=True)
        for operation in (skills.install, skills.uninstall):
            with self.assertRaisesRegex(skills.SkillError, "symlinked"):
                operation(NAME, target="codex")
        self.destination().unlink()
        parent.rmdir()
        parent.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(skills.SkillError, "symlinked"):
            skills.install(NAME, target="codex")
        self.assertTrue(outside.exists())

    def test_symlinked_support_file_blocks_removal(self):
        skills.install(NAME, target="codex")
        support = self.destination() / "scripts/check.py"
        support.unlink()
        support.symlink_to(self.root / "outside")
        with self.assertRaisesRegex(skills.SkillError, "symlink"):
            skills.uninstall(NAME, target="codex")

    def test_invalid_receipt_blocks_removal(self):
        skills.install(NAME, target="codex")
        (self.destination() / skills.RECEIPT).write_text("[]")
        with self.assertRaisesRegex(skills.SkillError, "Invalid installation receipt"):
            skills.uninstall(NAME, target="codex")

    def test_offline_list_reports_managed_modified_and_manual_installs(self):
        skills.install(NAME, target="codex")
        rows = skills.list_skills()
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["installations"][0]["status"], "installed")
        self.assertEqual(rows[0]["installations"][1]["status"], "not_installed")
        (self.destination() / "SKILL.md").write_text("local work")
        manual = self.destination("claude")
        manual.mkdir(parents=True)
        (manual / "SKILL.md").write_bytes(MANIFEST)
        self.fetch.reset_mock()
        rows = skills.list_skills()
        self.assertEqual(
            [i["status"] for i in rows[0]["installations"]], ["modified", "unmanaged"]
        )
        self.fetch.assert_not_called()

    def test_commands_work_without_codeer_credentials(self):
        with patch(
            "codeer_cli.cli.CodeerClient.from_env",
            side_effect=AssertionError("Must not authenticate"),
        ):
            for argv in (
                ["skill", "list"],
                ["skill", "install", NAME, "--target", "codex", "--dry-run"],
                ["skill", "uninstall", NAME, "--target", "claude"],
            ):
                with self.subTest(argv=argv), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(argv), 0)

    def test_command_failure_has_nonzero_status(self):
        self.fetch.side_effect = skills.SkillError("Missing SKILL.md")
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(main(["skill", "install", NAME, "--target", "codex"]), 1)
        self.assertIn("Missing SKILL.md", stderr.getvalue())

    def test_unknown_skill_cannot_escape_install_root(self):
        with self.assertRaises(skills.SkillError):
            skills.install("../outside", target="codex")
        self.fetch.assert_not_called()


class SkillDownloadTests(unittest.TestCase):
    def test_download_resolves_ref_then_uses_immutable_commit(self):
        calls = []

        def respond(request):
            calls.append(request)
            if request.url.host == "api.github.com":
                return httpx.Response(200, json={"sha": COMMIT})
            return httpx.Response(200, content=archive())

        client = httpx.Client(transport=httpx.MockTransport(respond))
        with patch.object(skills.httpx, "Client", return_value=client):
            commit, files = skills._fetch_skill(NAME, "release/v1")
        self.assertEqual(commit, COMMIT)
        self.assertEqual(files["SKILL.md"][0], MANIFEST)
        self.assertIn("release%2Fv1", str(calls[0].url))
        self.assertTrue(str(calls[1].url).endswith(COMMIT))
        self.assertTrue(
            all(
                "x-api-key" not in r.headers and "authorization" not in r.headers
                for r in calls
            )
        )

    def test_http_failure_is_propagated(self):
        client = httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(404))
        )
        with (
            patch.object(skills.httpx, "Client", return_value=client),
            self.assertRaises(httpx.HTTPStatusError),
        ):
            skills._fetch_skill(NAME, "missing")

    def test_download_size_limit_is_enforced(self):
        def respond(request):
            return (
                httpx.Response(200, json={"sha": COMMIT})
                if request.url.host == "api.github.com"
                else httpx.Response(200, content=b"oversized")
            )

        client = httpx.Client(transport=httpx.MockTransport(respond))
        with (
            patch.object(skills.httpx, "Client", return_value=client),
            patch.object(skills, "MAX_ARCHIVE_BYTES", 2),
            self.assertRaisesRegex(skills.SkillError, "archive exceeds"),
        ):
            skills._fetch_skill(NAME, "main")

    def test_archive_rejects_traversal_symlinks_and_reserved_receipt(self):
        for relative, mode in (
            ("../outside", 0o644),
            ("C:/outside", 0o644),
            ("link", stat.S_IFLNK | 0o777),
            (skills.RECEIPT, 0o644),
        ):
            with self.subTest(relative=relative), self.assertRaises(skills.SkillError):
                skills._archive_files(
                    archive({**FILES, relative: (b"bad", mode)}), NAME, COMMIT
                )

    def test_invalid_manifest_or_old_repo_layout_is_rejected(self):
        for manifest in (
            b"not a skill",
            MANIFEST.replace(b"codeer-agent", b"wrong-name"),
        ):
            with self.assertRaisesRegex(skills.SkillError, "SKILL.md"):
                skills._archive_files(
                    archive({"SKILL.md": (manifest, 0o644)}), NAME, COMMIT
                )
        with self.assertRaisesRegex(skills.SkillError, "SKILL.md"):
            skills._archive_files(archive(name="other-skill"), NAME, COMMIT)

    def test_expanded_size_limit_is_enforced(self):
        with (
            patch.object(skills, "MAX_SKILL_BYTES", 2),
            self.assertRaisesRegex(skills.SkillError, "Expanded skill"),
        ):
            skills._archive_files(archive(), NAME, COMMIT)

    def test_invalid_commit_metadata_is_rejected(self):
        for metadata in ({"sha": "main"}, []):
            client = httpx.Client(
                transport=httpx.MockTransport(
                    lambda request, metadata=metadata: httpx.Response(
                        200, json=metadata
                    )
                )
            )
            with (
                patch.object(skills.httpx, "Client", return_value=client),
                self.assertRaisesRegex(skills.SkillError, "commit SHA"),
            ):
                skills._fetch_skill(NAME, "main")

    def test_all_repository_skill_packages_install_and_remove_through_cli(self):
        repository = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary).resolve()
            for name in skills.CATALOG:
                with self.subTest(skill=name):
                    source = repository / "skills" / name
                    entries = {
                        path.relative_to(source).as_posix(): (
                            path.read_bytes(),
                            stat.S_IFREG | 0o644,
                        )
                        for path in source.rglob("*")
                        if path.is_file()
                    }
                    package = archive(entries, name=name)

                    def respond(request, package=package):
                        return (
                            httpx.Response(200, json={"sha": COMMIT})
                            if request.url.host == "api.github.com"
                            else httpx.Response(200, content=package)
                        )

                    client = httpx.Client(transport=httpx.MockTransport(respond))
                    with (
                        patch.object(Path, "home", return_value=home),
                        patch.object(skills.httpx, "Client", return_value=client),
                        patch(
                            "codeer_cli.cli.CodeerClient.from_env",
                            side_effect=AssertionError("Must not authenticate"),
                        ),
                        contextlib.redirect_stdout(io.StringIO()),
                    ):
                        self.assertEqual(
                            main(["skill", "install", name, "--target", "codex"]), 0
                        )
                        installed = home / ".agents/skills" / name
                        self.assertEqual(
                            set(skills._fingerprint(installed)), set(entries)
                        )
                        self.assertEqual(
                            main(["skill", "uninstall", name, "--target", "codex"]), 0
                        )
                        self.assertFalse(installed.exists())


if __name__ == "__main__":
    unittest.main()
