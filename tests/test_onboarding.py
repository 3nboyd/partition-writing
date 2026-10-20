import base64
import http.client
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import onboarding as ui
import partition as core


def upload_body(text="A thoughtful academic argument begins with evidence. We examine the evidence and state the limits.", **overrides):
    return {"name": "paper.txt", "data": base64.b64encode(text.encode()).decode(), "tone": "academic", "kind": "sample", **overrides}


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        core.init(self.root)
        self.ui = ui.Onboarding(self.root)

    def test_upload_is_staged_until_apply(self):
        record = self.ui.upload(upload_body())
        self.assertFalse(self.ui.path(record["extracted"]).exists())
        self.assertTrue(self.ui.path(record["staged"]).exists())
        self.assertEqual(core.context_search(self.root, "thoughtful"), [])
        self.ui.apply()
        self.assertTrue(self.ui.path(record["extracted"]).exists())
        self.assertTrue(core.context_search(self.root, "thoughtful"))

    def test_installed_project_start_command_uses_installed_cli(self):
        state = self.ui.public_state()
        self.assertIn("python3 .partition/partition.py run", state["commands"]["start"])
        self.assertFalse(state["has_launcher"])

    def test_purpose_only_custom_tone_is_activated(self):
        draft = self.ui.data()["draft"]
        draft["profiles"].append({"id":"personal", "name":"Personal", "purpose":"Reflective personal essays", "guide":""})
        self.ui.save_draft(draft)
        self.ui.apply()
        self.assertIn("Reflective personal essays", self.ui.path("references/voice-profiles/personal.md").read_text())

    def test_docx_extracts_paragraphs_and_tables(self):
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, "w") as doc:
            doc.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>A sufficiently long academic paragraph.</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Table content is included.</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
        extracted = ui.extract_text("paper.docx", raw.getvalue())
        self.assertIn("academic paragraph", extracted)
        self.assertIn("Table content", extracted)

    def test_invalid_docx_is_explained(self):
        with self.assertRaisesRegex(core.PartitionError, "Could not read"):
            ui.extract_text("paper.docx", b"not a zip")

    def test_unsupported_file_rejected(self):
        with self.assertRaisesRegex(core.PartitionError, "Supported files"):
            ui.extract_text("paper.exe", b"some bytes")

    def test_binary_text_rejected(self):
        with self.assertRaisesRegex(core.PartitionError, "binary"):
            ui.extract_text("paper.txt", b"hello\x00world")

    def test_too_large_file_rejected(self):
        with self.assertRaisesRegex(core.PartitionError, "12 MB"):
            ui.extract_text("paper.txt", b"a" * (ui.MAX_FILE + 1))

    def test_empty_extraction_mentions_ocr(self):
        with self.assertRaisesRegex(core.PartitionError, "OCR"):
            ui.extract_text("paper.txt", b"short")

    def test_duplicate_upload_rejected_without_duplicates(self):
        self.ui.upload(upload_body())
        with self.assertRaisesRegex(core.PartitionError, "already"):
            self.ui.upload(upload_body())
        self.assertEqual(len(self.ui.data()["library"]), 1)

    def test_filename_cannot_escape_private_storage(self):
        record = self.ui.upload(upload_body(name="../../private-paper.txt"))
        self.assertEqual(record["name"], "private-paper.txt")
        self.assertTrue(self.ui.path(record["staged"]).is_relative_to(self.root))
        self.assertFalse((self.root / "private-paper.txt").exists())

    def test_resume_is_not_a_voice_sample(self):
        self.ui.upload(upload_body(kind="resume"))
        with self.assertRaisesRegex(core.PartitionError, "Résumé"):
            self.ui.suggest("academic")

    def test_local_guide_only_uses_selected_tone(self):
        self.ui.upload(upload_body())
        self.ui.upload(upload_body("This is a casual message with short sentences and a relaxed rhythm.", name="casual.txt", tone="casual"))
        result = self.ui.suggest("academic")
        self.assertEqual(result["samples"], 1)
        self.assertIn("Academic", result["guide"])
        self.assertEqual(result["method"], "local")

    def test_uncertain_items_are_unselected(self):
        items = ui.memory_candidates("# Preferences\n- I prefer concise replies.\n- Possibly interested in music.\n")
        self.assertEqual(len(items), 2)
        self.assertTrue(items[0]["selected"])
        self.assertFalse(items[1]["selected"])

    def test_uncertainty_section_carries_to_its_items(self):
        items = ui.memory_candidates("## Uncertain or outdated\n- Interested in climbing.\n## Confirmed preferences\n- Prefers concrete examples.")
        self.assertFalse(items[0]["selected"])
        self.assertTrue(items[1]["selected"])

    def test_memory_needs_explicit_selection_boolean(self):
        draft = self.ui.data()["draft"]
        draft["memory_items"] = [{"text": "some factual context", "selected": "yes", "kind": "user-stated"}]
        with self.assertRaises(core.PartitionError):
            self.ui.save_draft(draft)

    def test_only_selected_memories_activate(self):
        draft = self.ui.data()["draft"]
        draft["memory_text"] = "- Approvedxyz context.\n- Rejectedxyz context."
        draft["memory_items"] = [{"text": "Approvedxyz context.", "selected": True, "kind": "user-stated"},
                                 {"text": "Rejectedxyz context.", "selected": False, "kind": "inferred"}]
        self.ui.save_draft(draft)
        self.ui.apply()
        self.assertEqual(len(core.memory_records(self.root)), 1)
        self.assertEqual(core.context_search(self.root, "Rejectedxyz"), [])
        self.assertTrue(core.context_search(self.root, "Approvedxyz"))

    def test_repeated_activation_deduplicates_memory(self):
        draft = self.ui.data()["draft"]
        item = {"text": "I prefer a clear explanation.", "selected": True, "kind": "user-stated"}
        draft["memory_items"] = [item, item.copy()]
        self.ui.save_draft(draft)
        self.ui.apply()
        self.ui.apply()
        self.assertEqual(len(core.memory_records(self.root)), 1)

    def test_deselection_preserves_manual_memories(self):
        manual = core.memory_add(self.root, "Manually added context", "global", "user", "user-stated")
        draft = self.ui.data()["draft"]
        draft["memory_items"] = [{"text": "Imported context to remove", "selected": True, "kind": "user-stated"}]
        self.ui.save_draft(draft)
        self.ui.apply()
        draft["memory_items"][0]["selected"] = False
        self.ui.save_draft(draft)
        self.ui.apply()
        self.assertEqual([m["id"] for m in core.memory_records(self.root)], [manual["id"]])

    def test_existing_preferences_preserved_and_marker_updated(self):
        before = self.ui.path("preferences.md").read_text()
        draft = self.ui.data()["draft"]
        draft["name"] = "Test Person"
        self.ui.save_draft(draft)
        self.ui.apply()
        draft["name"] = "New Name"
        self.ui.save_draft(draft)
        self.ui.apply()
        after = self.ui.path("preferences.md").read_text()
        self.assertIn(before.strip(), after)
        self.assertIn("New Name", after)
        self.assertNotIn("Test Person", after)
        self.assertEqual(after.count("partition-onboarding:preferences:begin"), 1)

    def test_archive_removes_active_sample_but_preserves_copy(self):
        record = self.ui.upload(upload_body())
        self.ui.apply()
        self.ui.archive(record["id"])
        self.assertEqual(core.context_search(self.root, "thoughtful"), [])
        self.assertEqual(self.ui.data()["library"], [])
        self.assertTrue(list(self.ui.path("onboarding/archive").rglob("*.txt")))

    def test_invalid_tone_cannot_write_paths(self):
        with self.assertRaises(core.PartitionError):
            self.ui.upload(upload_body(tone="../../outside"))

    def test_codex_refinement_uses_stdin_and_readonly(self):
        self.ui.upload(upload_body())
        with patch.object(core, "catalog", return_value={"gpt-6.1-sol": {}}), patch.object(ui.subprocess, "run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "Use clear arguments and measured transitions."
            result = self.ui.suggest("academic", True)
        args, kwargs = run.call_args
        self.assertEqual(args[0][-1], "-")
        self.assertIn("read-only", args[0])
        self.assertIn("academic argument", kwargs["input"])
        self.assertEqual(result["method"], "codex")

    @unittest.skipUnless(importlib.util.find_spec("pypdf"), "pypdf is optional")
    def test_text_pdf_extraction(self):
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
        writer = PdfWriter()
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 72 720 Td (A sample academic PDF with extractable text.) Tj ET")
        page[NameObject("/Contents")] = writer._add_object(stream)
        output = io.BytesIO()
        writer.write(output)
        self.assertIn("academic PDF", ui.extract_text("paper.pdf", output.getvalue()))

    @unittest.skipUnless(importlib.util.find_spec("pypdf"), "pypdf is optional")
    def test_scanned_or_blank_pdf_is_not_claimed_as_extracted(self):
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        output = io.BytesIO()
        writer.write(output)
        with self.assertRaisesRegex(core.PartitionError, "OCR"):
            ui.extract_text("scan.pdf", output.getvalue())

    @unittest.skipUnless(importlib.util.find_spec("pypdf"), "pypdf is optional")
    def test_encrypted_pdf_is_rejected(self):
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        writer.encrypt("test-password")
        output = io.BytesIO()
        writer.write(output)
        with self.assertRaisesRegex(core.PartitionError, "Unlock"):
            ui.extract_text("locked.pdf", output.getvalue())


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name).resolve()
        core.init(root)
        self.server = ui.Server(("127.0.0.1", 0), ui.Onboarding(root), ROOT / "onboarding-web")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path, data=None, extra=None, authorized=True):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        headers = {"Content-Type": "application/json"}
        if authorized:
            headers["X-Partition-Token"] = self.server.token
        headers.update(extra or {})
        connection.request(method, path, body=json.dumps(data) if data is not None else None, headers=headers)
        response = connection.getresponse()
        content = response.read()
        connection.close()
        return response.status, content

    def test_page_works_and_contains_session_token(self):
        status, raw = self.request("GET", "/", authorized=False)
        self.assertEqual(status, 200)
        self.assertIn(self.server.token.encode(), raw)

    def test_reopening_finds_only_the_same_project_server(self):
        service = self.server.service
        core.write(service.path("onboarding/server.json"), core.dump({"port":self.server.server_port}))
        self.assertEqual(ui.running_url(service), f"http://127.0.0.1:{self.server.server_port}")
        with tempfile.TemporaryDirectory() as folder:
            other = Path(folder).resolve()
            core.init(other)
            different = ui.Onboarding(other)
            core.write(different.path("onboarding/server.json"), core.dump({"port":self.server.server_port}))
            self.assertIsNone(ui.running_url(different))

    def test_api_requires_token(self):
        self.assertEqual(self.request("GET", "/api/state", authorized=False)[0], 403)

    def test_cross_origin_rejected(self):
        self.assertEqual(self.request("POST", "/api/apply", {}, {"Origin":"https://evil.example"})[0], 403)

    def test_rebinding_host_rejected(self):
        self.assertEqual(self.request("GET", "/", extra={"Host":"evil.example"})[0], 403)

    def test_upload_to_activation_http_flow(self):
        self.assertEqual(self.request("POST", "/api/upload", upload_body())[0], 200)
        status, raw = self.request("GET", "/api/state")
        state = json.loads(raw)
        self.assertEqual(status, 200)
        self.assertEqual(len(state["library"]), 1)
        self.assertEqual(self.request("POST", "/api/draft", state["draft"])[0], 200)
        status, raw = self.request("POST", "/api/apply", {})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["documents"], 1)

    def test_static_traversal_is_not_served(self):
        self.assertEqual(self.request("GET", "/../partition.py")[0], 404)

    def test_open_workspace_uses_exact_local_path_without_shell(self):
        with patch.object(ui.shutil, "which", return_value="/usr/bin/codex"), patch.object(ui.subprocess, "run") as run:
            run.return_value.returncode = 0
            status, raw = self.request("POST", "/api/open-codex", {})
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(raw)["opened"])
        self.assertEqual(run.call_args.args[0], ["codex", "app", str(self.server.service.root)])
        self.assertNotIn("shell", run.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()
