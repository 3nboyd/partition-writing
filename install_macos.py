#!/usr/bin/env python3
"""Build a local Mac launcher in ~/Applications. Requires Apple Command Line Tools."""
import argparse
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import uuid

ROOT=Path(__file__).resolve().parent

def configuration(root,python,codex):
    mode='writing' if (root/'writing.py').is_file() else 'code'
    title='Partition Writing' if mode=='writing' else 'Partition Code'
    if not (root/('writing.py' if mode=='writing' else 'relay.py')).is_file():
        raise ValueError('Run this installer from a Partition repository.')
    return {'CFBundleName':title,'CFBundleDisplayName':title,'CFBundleIdentifier':'local.partition.'+mode,
            'CFBundleVersion':'1','CFBundleShortVersionString':'1.0','CFBundlePackageType':'APPL',
            'CFBundleExecutable':'PartitionLauncher','NSHighResolutionCapable':True,
            'PartitionManagedBy':'partition-macos','PartitionSource':str(root),'PartitionPython':str(python),
            'PartitionCodex':str(codex),'PartitionMode':mode}

def install(root,applications,python,codex):
    config=configuration(root,python,codex)
    if sys.platform!='darwin':raise ValueError('This installer requires macOS.')
    if not shutil.which('swiftc'):raise ValueError('Install Apple Command Line Tools with xcode-select --install first.')
    applications.mkdir(parents=True,exist_ok=True)
    target=applications/(config['CFBundleName']+'.app')
    if target.is_symlink():raise ValueError('Preserving a symlink at the application path.')
    if target.exists():
        info=target/'Contents/Info.plist'
        if not info.is_file() or plistlib.loads(info.read_bytes()).get('PartitionManagedBy')!='partition-macos':
            raise ValueError('Preserving an existing application with the same name.')
    with tempfile.TemporaryDirectory(prefix='.partition-install-',dir=applications) as temp:
        app=Path(temp)/target.name;binary=app/'Contents/MacOS/PartitionLauncher'
        binary.parent.mkdir(parents=True)
        (app/'Contents/Info.plist').write_bytes(plistlib.dumps(config))
        subprocess.run(['swiftc','-O','-framework','AppKit',str(root/'macos/Launcher.swift'),'-o',str(binary)],check=True)
        if target.exists():
            backup=Path.home()/'Library/Application Support/Partition/Backups'/uuid.uuid4().hex/target.name
            backup.parent.mkdir(parents=True,exist_ok=True);target.replace(backup)
        app.replace(target)
    return target

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--applications',type=Path,default=Path.home()/'Applications')
    p.add_argument('--codex',type=Path,default=Path(shutil.which('codex') or '/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex'))
    args=p.parse_args(argv)
    try:
        codex=args.codex.expanduser().resolve()
        if not codex.is_file():raise ValueError('Install Codex before creating the launcher.')
        app=install(ROOT,args.applications.expanduser().resolve(),Path(sys.executable).resolve(),codex)
        print('Installed '+str(app));return 0
    except (OSError,ValueError,subprocess.CalledProcessError) as exc:
        print('Mac setup: '+str(exc),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
