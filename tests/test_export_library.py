import base64
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import test_writing as fixtures
import export_library as export
import partition as core

# Reuse fixture helpers without inheriting the existing test suite.
class ExportTests(unittest.TestCase):
    setUp=fixtures.Tests.setUp
    upload=fixtures.Tests.upload
    result=fixtures.Tests.result
    build=fixtures.Tests.build

    def test_build_creates_readable_folder_and_preserves_original(self):
        d=self.upload();original=self.lib.path(d['original']).read_bytes();self.build([d]);folder=export.destination(self.lib)
        self.assertTrue((folder/'START HERE.md').exists());self.assertTrue((folder/'PROJECT INSTRUCTIONS.txt').exists())
        copies=list((folder/'Academic/Samples').iterdir());self.assertEqual(len(copies),1);self.assertEqual(copies[0].read_bytes(),original)
        self.assertIn('careful evidence',(folder/'Upload to ChatGPT/STYLE-academic.md').read_text())
        self.assertIn('No new template or copied prompt is required',(folder/'START HERE.md').read_text())
    def test_background_does_not_enter_style_sources(self):
        d=self.upload();r=self.upload('resume.txt','BACKGROUNDONLY curriculum vitae education and employment information for a specific application.')
        response=self.result([d]);response['documents'].append({'id':r['id'],'kind':'resume','style':'professional','confidence':1,'reason':'A resume, only background.'})
        with patch.object(self.lib,'ask_model',return_value=response):self.lib.build()
        folder=export.destination(self.lib)/'Upload to ChatGPT'
        self.assertIn('BACKGROUNDONLY',(folder/'BACKGROUND.md').read_text());self.assertNotIn('BACKGROUNDONLY',(folder/'STYLE-academic.md').read_text())
    def test_review_material_excluded_from_chatgpt_uploads(self):
        d=self.upload();r=self.upload('mixed.txt','UNCERTAINAUTHOR combines material from several people and cannot teach a personal writing style.')
        response=self.result([d]);response['documents'].append({'id':r['id'],'kind':'sample','style':'needs-review','confidence':.8,'reason':'Mixed authorship.'})
        with patch.object(self.lib,'ask_model',return_value=response):self.lib.build()
        folder=export.destination(self.lib);self.assertTrue(list((folder/'Needs review/Samples').iterdir()))
        self.assertNotIn('UNCERTAINAUTHOR',''.join(p.read_text() for p in (folder/'Upload to ChatGPT').iterdir()))
    def test_export_no_model_request(self):
        d=self.upload();self.build([d])
        with patch.object(self.lib,'ask_model',side_effect=AssertionError('no analysis needed')):self.assertTrue(self.lib.export_folder()['unchanged'])
    def test_stale_analysis_cannot_export(self):
        d=self.upload();self.build([d]);self.upload('new.txt','Additional writing that must be classified before it becomes part of an exported voice reference.')
        with self.assertRaisesRegex(core.PartitionError,'Organize'):self.lib.export_folder()
    def test_regeneration_preserves_previous_folder_and_updates_guides(self):
        d=self.upload();self.build([d]);folder=export.destination(self.lib);(folder/'my-notes.txt').write_text('User-added note must survive in history.')
        response=self.result([d]);response['styles'][0]['guide']='UPDATEDGUIDE describes sentence rhythm based on the supplied academic source sample.'
        with patch.object(self.lib,'ask_model',return_value=response):self.lib.build(True)
        self.assertIn('UPDATEDGUIDE',(folder/'Upload to ChatGPT/STYLE-academic.md').read_text())
        self.assertTrue(list(self.lib.path('writing/export-history').rglob('my-notes.txt')))
    def test_unrecognized_existing_folder_preserved(self):
        folder=export.destination(self.lib);folder.mkdir();(folder/'my-notes.txt').write_text('Keep these notes.')
        d=self.upload()
        with self.assertRaisesRegex(core.PartitionError,'unrecognized'):self.build([d])
        self.assertEqual((folder/'my-notes.txt').read_text(),'Keep these notes.')
    def test_export_history_excluded_from_context(self):
        d=self.upload();self.build([d]);folder=export.destination(self.lib);(folder/'secret.md').write_text('Exportuniquesecretxyz')
        response=self.result([d]);response['styles'][0]['guide']+=' Updated guide.'
        with patch.object(self.lib,'ask_model',return_value=response):self.lib.build(True)
        self.assertEqual(core.context_search(self.root,'Exportuniquesecretxyz'),[])
    def test_folder_opener_uses_fixed_generated_path(self):
        d=self.upload();self.build([d])
        with patch('subprocess.Popen') as opened:self.lib.open_folder()
        self.assertEqual(opened.call_args.args[0][-1],str(export.destination(self.lib)))
