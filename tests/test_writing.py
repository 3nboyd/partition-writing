import base64
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import writing as w
import partition as core

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);core.init(self.root);self.lib=w.Library(self.root)
    def upload(self,name='paper.txt',text='This is a sufficiently long academic writing sample with careful evidence and a thoughtful conclusion.'):
        return self.lib.upload({'name':name,'data':base64.b64encode(text.encode()).decode()})
    def result(self,docs):
        return {'documents':[{'id':d['id'],'kind':'sample','style':'academic','confidence':.9,'reason':'Analytical essay with evidence.'} for d in docs],
        'styles':[{'id':'academic','guide':'A guide grounded in the supplied analytical writing samples and their organization.','new_prompt':'Write a new academic essay for [audience] on [task] using verified [sources].','edit_prompt':'Edit my draft while preserving its meaning, claims and verified source citations.','source_ids':[d['id'] for d in docs]}]}
    def build(self,docs):
        with patch.object(self.lib,'ask_model',return_value=self.result(docs)):return self.lib.build()
    def test_upload_needs_no_metadata(self):
        d=self.upload();self.assertEqual(d['tone'],'auto');self.assertTrue(self.lib.path(d['original']).exists())
    def test_build_organizes_without_touching_originals_and_exports(self):
        d=self.upload();original=self.lib.path(d['original']).read_bytes();self.build([d]);a=self.lib.analysis();self.assertEqual(len(a['documents']),1)
        self.assertEqual(self.lib.path(d['original']).read_bytes(),original);self.assertTrue(self.lib.path(a['documents'][0]['path']).exists())
        prompt=self.lib.bundle({'style':'academic','mode':'edit','task':'Revise my seminar draft'})['text'];self.assertIn('Revise my seminar draft',prompt);self.assertIn('careful evidence',prompt)
    def test_unchanged_build_skips_model(self):
        d=self.upload();self.build([d])
        with patch.object(self.lib,'ask_model',side_effect=AssertionError('Should not call model')):self.assertTrue(self.lib.build()['unchanged'])
    def test_resume_cannot_support_guide(self):
        d=self.upload();result=self.result([d]);result['documents'][0]['kind']='resume'
        with self.assertRaises(core.PartitionError):self.lib.validate(result,[d])
    def test_cross_style_sources_rejected(self):
        d=self.upload();result=self.result([d]);result['documents'][0]['style']='personal'
        with self.assertRaises(core.PartitionError):self.lib.validate(result,[d])
    def test_missing_or_duplicate_document_ids_rejected(self):
        d=self.upload();result=self.result([d]);result['documents'].append(copy.deepcopy(result['documents'][0]))
        with self.assertRaises(core.PartitionError):self.lib.validate(result,[d])
    def test_low_confidence_needs_review(self):
        d=self.upload();result=self.result([d]);result['documents'][0]['confidence']=.4;result['styles']=[]
        self.assertEqual(self.lib.validate(result,[d])['documents'][0]['style'],'needs-review')
    def test_failed_analysis_preserves_previous_guides(self):
        d=self.upload();self.build([d]);before=self.lib.path('writing/library.json').read_bytes();guide=self.lib.path('writing/styles/academic/GUIDE.md').read_bytes()
        with patch.object(self.lib,'ask_model',return_value={'documents':[],'styles':[]}):
            with self.assertRaises(core.PartitionError):self.lib.build(True)
        self.assertEqual(self.lib.path('writing/library.json').read_bytes(),before);self.assertEqual(self.lib.path('writing/styles/academic/GUIDE.md').read_bytes(),guide)
    def test_concurrent_upload_rejects_stale_analysis(self):
        d=self.upload();response=self.result([d])
        def model(*_):self.upload('personal.txt','A different sufficiently long personal letter about an ordinary day and a warm greeting.');return response
        with patch.object(self.lib,'ask_model',side_effect=model):
            with self.assertRaisesRegex(core.PartitionError,'changed'):self.lib.build()
        self.assertFalse(self.lib.path('writing/library.json').exists())
    def test_preferences_persist_and_invalidate_fingerprint(self):
        d=self.upload();self.build([d]);old=self.lib.analysis()['fingerprint'];self.lib.save_preferences({'text':'Avoid ornate transitions.'});self.assertNotEqual(self.lib.fingerprint(self.lib.data()),old);self.assertEqual(self.lib.public_state()['writing_preferences'].strip(),'Avoid ornate transitions.')
    def test_unapproved_memory_not_sent_to_analysis(self):
        data=self.lib.data();data['draft']['memory_text']='Raw private summary SECRETONE';data['draft']['memory_items']=[{'text':'SECRETTWO unapproved fact','kind':'user-stated','selected':False},{'text':'Use concrete wording.','kind':'user-stated','selected':True}]
        self.lib.save_data(data);guidance=self.lib.guidelines(self.lib.data());self.assertNotIn('SECRET',guidance);self.assertIn('concrete wording',guidance)
    def test_corrected_category_enforced(self):
        d=self.upload();self.lib.override({'id':d['id'],'kind':'sample','style':'personal'})
        with patch.object(self.lib,'ask_model',return_value=self.result([d])):
            with self.assertRaisesRegex(core.PartitionError,'correction'):self.lib.build()
    def test_archiving_invalidates_guide_and_retains_original(self):
        d=self.upload();self.build([d]);self.lib.archive(d['id']);self.assertEqual(self.lib.analysis()['styles'],[])
        self.assertTrue(any(self.lib.path('onboarding/archive/'+d['id']).iterdir()))
        with self.assertRaises(core.PartitionError):self.lib.bundle({'style':'academic'})
    def test_regeneration_preserves_history(self):
        d=self.upload();self.build([d]);self.lib.save_preferences({'text':'Prefer short sentences.'});self.build([d]);self.assertTrue(list(self.lib.path('writing/history').rglob('GUIDE.md')))
    def test_model_disabled_tools_stdin_and_timeout(self):
        d=self.upload();schema=self.lib.schema([d]);seen={}
        def run(cmd,**kwargs):
            seen.update({'cmd':cmd,**kwargs});Path(cmd[cmd.index('--output-last-message')+1]).write_text(json.dumps(self.result([d])));return subprocess.CompletedProcess(cmd,0,'','')
        with patch.object(w.shutil,'which',return_value='/test/codex'),patch.object(w.subprocess,'run',side_effect=run):self.lib.ask_model('PRIVATE SAMPLE TEXT',schema)
        self.assertNotIn('PRIVATE SAMPLE TEXT',seen['cmd']);self.assertEqual(seen['input'],'PRIVATE SAMPLE TEXT');self.assertIn('features.shell_tool=false',seen['cmd']);self.assertIn('--ephemeral',seen['cmd']);self.assertEqual(seen['timeout'],360)
    def test_invalid_model_output_does_not_write(self):
        self.upload()
        with patch.object(self.lib,'ask_model',return_value={'documents':[{'id':'../../outside'}],'styles':[]}):
            with self.assertRaises(core.PartitionError):self.lib.build()
        self.assertFalse(self.lib.path('writing/library.json').exists())
if __name__=='__main__':unittest.main()
