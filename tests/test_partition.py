import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("partition", ROOT / "partition.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def install(self):
        return p.init(self.root)

    def test_install_and_doctor(self):
        self.install()
        self.assertEqual(p.doctor(self.root)["errors"], [])
        self.assertTrue((self.root / ".partition/private/references").is_dir())

    def test_reinstall_is_idempotent(self):
        self.install()
        self.assertEqual(self.install()["changed"], [])

    def test_override_instructions_fail_with_clear_message(self):
        (self.root / "AGENTS.override.md").write_text("My overriding instructions")
        with self.assertRaisesRegex(p.PartitionError, "takes precedence"):
            self.install()
        self.assertFalse((self.root / ".partition/models.json").exists())

    def test_preserves_existing_instructions(self):
        (self.root / "AGENTS.md").write_text("Keep my rules.\n")
        self.install()
        self.assertIn("Keep my rules.", (self.root / "AGENTS.md").read_text())
        p.uninstall(self.root)
        self.assertEqual((self.root / "AGENTS.md").read_text(), "Keep my rules.\n")

    def test_existing_conflicting_file_aborts_preflight(self):
        dest = self.root / ".partition/models.json"
        p.write(dest, "my settings")
        with self.assertRaises(p.PartitionError):
            self.install()
        self.assertFalse((self.root / "AGENTS.md").exists())
        self.assertEqual(dest.read_text(), "my settings")

    def test_malformed_marker_aborts_without_partial_install(self):
        (self.root / "AGENTS.md").write_text(p.BEGIN)
        with self.assertRaises(p.PartitionError):
            self.install()
        self.assertFalse((self.root / ".partition/models.json").exists())

    def test_edited_managed_file_preserved_on_update(self):
        self.install()
        dest = self.root / ".partition/INSTRUCTIONS.md"
        dest.write_text("my edited agent")
        with self.assertRaises(p.PartitionError):
            self.install()
        self.assertEqual(dest.read_text(), "my edited agent")

    def test_uninstall_preserves_private_context_and_modified_files(self):
        self.install()
        m = p.memory_add(self.root, "A real preference", "global", "user", "user-stated")
        dest = self.root / ".partition/INSTRUCTIONS.md"
        dest.write_text("my local edits")
        result = p.uninstall(self.root)
        self.assertIn(".partition/INSTRUCTIONS.md", result["preserved"])
        self.assertEqual(dest.read_text(), "my local edits")
        self.assertTrue((self.root / ".partition/private/memories" / (m["id"] + ".json")).exists())

    def test_uninstall_keeps_later_instruction_additions(self):
        self.install()
        file = self.root / "AGENTS.md"
        file.write_text(file.read_text() + "Later rules.\n")
        p.uninstall(self.root)
        self.assertIn("Later rules.", file.read_text())
        self.assertNotIn(p.BLOCK, file.read_text())

    def test_symlink_managed_directory_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.root / ".partition").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(p.PartitionError):
                self.install()
            self.assertEqual(list(Path(outside).iterdir()), [])

    def test_symlink_private_subdir_rejected(self):
        (self.root / ".partition/private").mkdir(parents=True)
        with tempfile.TemporaryDirectory() as outside:
            (self.root / ".partition/private/memories").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(p.PartitionError):
                self.install()

    def test_manifest_traversal_rejected(self):
        self.install()
        manifest = p.state(self.root)
        manifest["files"]["../outside"] = {"sha256": "a"}
        p.write(self.root / ".partition/state.json", p.dump(manifest))
        with self.assertRaises(p.PartitionError):
            p.uninstall(self.root)

    def test_private_files_ignored_by_git(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.install()
        result = subprocess.run(["git", "-C", str(self.root), "check-ignore", ".partition/private/preferences.md"], capture_output=True)
        self.assertEqual(result.returncode, 0)

    def test_private_files_stay_ignored_after_uninstall(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.install()
        p.uninstall(self.root)
        result = subprocess.run(["git", "-C", str(self.root), "check-ignore", ".partition/private/preferences.md"], capture_output=True)
        self.assertEqual(result.returncode, 0)

    def test_doctor_detects_tracked_private_file(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.install()
        subprocess.run(["git", "-C", str(self.root), "add", "-f", ".partition/private/preferences.md"], check=True)
        self.assertTrue(any("already tracked" in x for x in p.doctor(self.root)["errors"]))

    def test_private_preferences_never_overwritten(self):
        self.install()
        file = self.root / ".partition/private/preferences.md"
        file.write_text("My real voice.")
        self.install()
        self.assertEqual(file.read_text(), "My real voice.")

    def test_copied_cli_runs_without_source_tree(self):
        self.install()
        result = subprocess.run(["python3", str(self.root / ".partition/partition.py"), "doctor", "--project", str(self.root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_memory_roundtrip_delete(self):
        self.install()
        record = p.memory_add(self.root, "Prefer short answers", "global", "explicit", "user-stated")
        self.assertEqual(p.memory_records(self.root)[0]["text"], "Prefer short answers")
        p.memory_delete(self.root, record["id"])
        self.assertEqual(p.memory_records(self.root), [])

    def test_memory_empty_rejected(self):
        self.install()
        with self.assertRaises(p.PartitionError):
            p.memory_add(self.root, " ", "global", "user", "user-stated")

    def test_invalid_memory_id_cannot_escape(self):
        self.install()
        with self.assertRaises(p.PartitionError):
            p.memory_delete(self.root, "../../AGENTS.md")

    def test_memory_scope_filters_unrelated_projects(self):
        self.install()
        p.memory_add(self.root, "likes concise", "global", "user", "user-stated")
        p.memory_add(self.root, "concise alpha detail", "alpha", "user", "user-stated")
        p.memory_add(self.root, "concise beta detail", "beta", "user", "user-stated")
        results = p.context_search(self.root, "concise", "alpha")
        self.assertEqual({r["scope"] for r in results}, {"global", "alpha"})

    def test_unscoped_search_does_not_load_project_memories_or_files(self):
        self.install()
        p.memory_add(self.root, "secretxyz alpha detail", "alpha", "user", "user-stated")
        p.write(self.root / ".partition/private/projects/alpha/context.md", "secretxyz project source")
        self.assertEqual(p.context_search(self.root, "secretxyz"), [])
        self.assertEqual(len(p.context_search(self.root, "secretxyz", "alpha")), 2)

    def test_search_cites_matching_line_and_skips_symlinks(self):
        self.install()
        file = self.root / ".partition/private/references/voice.md"
        file.write_text("# Samples\nPrefer vivid language.\n")
        (file.parent / "linked.md").symlink_to(file)
        hits = p.context_search(self.root, "vivid")
        self.assertEqual(len(hits), 1)
        self.assertTrue(hits[0]["source"].endswith("voice.md:2"))

    def test_no_context_match_does_not_invent_memory(self):
        self.install()
        self.assertEqual(p.context_search(self.root, "nonexistentxyz"), [])

    def test_models_edit_is_valid_and_doctor_reports_drift(self):
        self.install()
        path = self.root / ".partition/models.json"
        data = p.read_json(path)
        data["balanced"]["effort"] = "medium"
        p.write(path, p.dump(data))
        info = p.doctor(self.root)
        self.assertEqual(info["errors"], [])
        self.assertIn(".partition/models.json", info["locally_changed_managed_files"])

    def test_malformed_models_fail_cleanly(self):
        self.install()
        path = self.root / ".partition/models.json"
        for data in ([], {**p.DEFAULTS, "balanced": {"model": 123, "effort": "low"}}):
            p.write(path, p.dump(data))
            with self.assertRaises(p.PartitionError):
                p.policies(self.root)

    def test_malformed_manifest_fails_cleanly(self):
        self.install()
        p.write(self.root / ".partition/state.json", "[]")
        with self.assertRaises(p.PartitionError):
            p.state(self.root)

    def test_preexisting_identical_file_not_owned(self):
        template = p.templates()[".partition/models.json"]
        dest = self.root / ".partition/models.json"
        p.write(dest, template)
        self.install()
        p.uninstall(self.root)
        self.assertEqual(dest.read_bytes(), template)

    def test_launch_uses_argv_not_shell_and_readonly(self):
        self.install()
        args = p.parser().parse_args(["run", "--read-only", "--quality", "fast", "$(touch /tmp/should-not-exist)"])
        command, preview = p.launch_command(self.root, args)
        self.assertIn("read-only", command)
        self.assertEqual(preview["model"], "gpt-6-luna")
        self.assertIn("$(touch /tmp/should-not-exist)", command[-1])
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)

    def test_dry_run_never_launches_model(self):
        self.install()
        with patch.object(p, "catalog", side_effect=AssertionError("must not call catalog")):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                code = p.main(["run", "--project", str(self.root), "--dry-run", "hello"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["model"], "gpt-6.1-sol")

    def test_missing_cli_fails_cleanly(self):
        with patch.object(p.shutil, "which", return_value=None):
            with self.assertRaises(p.PartitionError):
                p.catalog()

    @unittest.skipUnless(p.shutil.which("codex"), "Codex CLI not installed")
    def test_real_cli_accepts_launcher_flags(self):
        self.install()
        for mode in ([], ["--exec"], ["--exec", "--search", "--read-only"]):
            args = p.parser().parse_args(["run", *mode, "hello"])
            command, _ = p.launch_command(self.root, args)
            result = subprocess.run(command[:-1] + ["--help"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


class ModelAndRoutingTests(unittest.TestCase):
    @unittest.skipUnless(p.shutil.which("zsh"), "zsh is required for the macOS launcher")
    def test_one_click_launcher_handles_spaces_and_starts_from_its_directory(self):
        with tempfile.TemporaryDirectory(prefix="partition launcher ") as temp:
            folder = Path(temp)
            launcher = folder / "Start Writing.command"
            launcher.write_bytes((ROOT / "Start Writing.command").read_bytes())
            tools = folder / "fake-bin"
            tools.mkdir()
            capture = folder / "capture"
            for name, script in {
                "python3": '#!/bin/sh\npwd > "$TEST_CAPTURE"\nprintf "%s\\n" "$@" >> "$TEST_CAPTURE"\n',
                "codex": '#!/bin/sh\nexit 0\n',
            }.items():
                file = tools / name
                file.write_text(script)
                file.chmod(0o755)
            result = subprocess.run([p.shutil.which("zsh"), str(launcher)], env={**os.environ, "PATH": str(tools), "TEST_CAPTURE": str(capture)}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(capture.read_text().splitlines(), [str(folder.resolve()), "writing.py", "serve", "--bootstrap"])

    def test_unsupported_model_rejected(self):
        with self.assertRaises(p.PartitionError):
            p.check_model({}, "unknown", "low")

    def test_unsupported_effort_rejected(self):
        with self.assertRaises(p.PartitionError):
            p.check_model({"m": {"supported_reasoning_levels": [{"effort": "low"}]}}, "m", "ultra")

    def test_supported_effort_accepted(self):
        p.check_model({"m": {"supported_reasoning_levels": [{"effort": "low"}]}}, "m", "low")

    def test_routing_hints_preserve_explicit_choice(self):
        self.assertEqual(p.route("debug python", "general")["work_area_hint"], "general")

    def test_representative_route_cases(self):
        cases = json.loads((ROOT / "evaluations/routing-cases.json").read_text())
        for case in cases:
            with self.subTest(prompt=case["prompt"]):
                self.assertEqual(p.route(case["prompt"])["work_area_hint"], case["hint"])


if __name__ == "__main__":
    unittest.main()
