import errno
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
installer=module('mac_installer',ROOT/'install_macos.py')
launcher=module('mac_start',ROOT/'macos/start.py')

class MacSetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.codex=self.root/'Codex executable';self.codex.write_text('test executable')
    def test_configuration_records_the_installation_without_shell_text(self):
        (self.root/'relay.py').touch();cfg=installer.configuration(self.root,Path(sys.executable),self.codex)
        self.assertEqual(cfg['PartitionMode'],'code');self.assertEqual(cfg['PartitionCodex'],str(self.codex));self.assertEqual(cfg['CFBundleName'],'Partition Code')
    def test_writing_configuration(self):
        (self.root/'writing.py').touch();self.assertEqual(installer.configuration(self.root,Path(sys.executable),self.codex)['PartitionMode'],'writing')
    def test_backup_supports_a_different_filesystem(self):
        app=self.root/'existing.app';app.mkdir();(app/'binary').write_bytes(b'original app')
        backup=self.root/'another-volume/backup.app'
        with patch.object(installer.shutil.os,'rename',side_effect=OSError(errno.EXDEV,'Cross-device move')):
            installer.backup_application(app,backup)
        self.assertEqual((backup/'binary').read_bytes(),b'original app');self.assertFalse(app.exists())
    def test_invalid_repository_rejected(self):
        with self.assertRaises(ValueError):installer.configuration(self.root,Path(sys.executable),self.codex)
    def test_unmanaged_existing_app_is_preserved(self):
        (self.root/'relay.py').touch();apps=self.root/'Applications';app=apps/'Partition Code.app';app.mkdir(parents=True);(app/'keep.txt').write_text('existing application')
        with patch.object(installer.sys,'platform','darwin'),patch.object(installer.shutil,'which',return_value='/test/swiftc'):
            with self.assertRaisesRegex(ValueError,'existing application'):installer.install(self.root,apps,Path(sys.executable),self.codex)
        self.assertEqual((app/'keep.txt').read_text(),'existing application')
    def test_code_launcher_handles_spaces_and_quotes_as_arguments(self):
        (self.root/'relay.py').touch();target=self.root/"My coding folder's files";target.mkdir()
        with patch.object(launcher,'ROOT',self.root),patch.object(launcher.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'','')) as run:
            self.assertEqual(launcher.main(['--codex',str(self.codex),'--project',str(target)]),0)
        self.assertEqual(run.call_args_list[0].args[0][-2:],['--project',str(target.resolve())]);self.assertEqual(run.call_args_list[1].args[0][2],'run')
        self.assertNotIn('shell',run.call_args.kwargs)
    def test_install_conflict_stops_before_starting_codex(self):
        (self.root/'relay.py').touch()
        with patch.object(launcher,'ROOT',self.root),patch.object(launcher.subprocess,'run',return_value=subprocess.CompletedProcess([],1,'','Conflicting file preserved')) as run:
            self.assertEqual(launcher.main(['--codex',str(self.codex),'--project',str(self.root)]),1)
        self.assertEqual(run.call_count,1)
    def test_writing_launcher_reuses_bootstrap_and_existing_server_detection(self):
        (self.root/'writing.py').touch()
        with patch.object(launcher,'ROOT',self.root),patch.object(launcher.subprocess,'run',return_value=subprocess.CompletedProcess([],0)) as run:
            self.assertEqual(launcher.main(['--codex',str(self.codex)]),0)
        self.assertIn('--bootstrap',run.call_args.args[0]);self.assertIn(str(self.root),run.call_args.args[0])
