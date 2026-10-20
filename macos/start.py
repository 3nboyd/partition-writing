#!/usr/bin/env python3
"""Start the installed project from its Mac launcher."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex',required=True)
    parser.add_argument('--project')
    args=parser.parse_args(argv)
    codex=Path(args.codex)
    if not codex.is_file():
        print('Codex was not found. Reinstall the launcher after installing Codex.',file=sys.stderr)
        return 1
    env={**os.environ,'PATH':str(codex.parent)+os.pathsep+os.environ.get('PATH','/usr/bin:/bin:/usr/sbin:/sbin')}
    if (ROOT/'writing.py').exists():
        return subprocess.run([sys.executable,str(ROOT/'writing.py'),'serve','--project',str(ROOT),'--bootstrap'],env=env).returncode
    if not args.project or not Path(args.project).is_dir():
        print('Choose an existing coding folder.',file=sys.stderr)
        return 1
    target=str(Path(args.project).resolve())
    installed=subprocess.run([sys.executable,str(ROOT/'relay.py'),'install','--project',target],env=env,capture_output=True,text=True)
    if installed.returncode:
        print(installed.stderr or installed.stdout,file=sys.stderr)
        return installed.returncode
    return subprocess.run([sys.executable,str(ROOT/'relay.py'),'run','--project',target],env=env).returncode

if __name__=='__main__':raise SystemExit(main())
