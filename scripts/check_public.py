#!/usr/bin/env python3
"""Check the complete tracked tree before publication. Never reads private contents."""
from pathlib import Path
import re
import subprocess
import sys
root=Path(__file__).resolve().parents[1]
r=subprocess.run(['git','ls-files','-z'],cwd=root,capture_output=True,check=True)
files=[p for p in r.stdout.decode().split('\0') if p];errors=[]
for rel in files:
    p=Path(rel)
    if any(s in p.parts for s in ['private','__pycache__','onboarding-runtime','uploads','history','.venv']) or rel.startswith(('.partition/','.relay/')) or p.name.startswith('.env') or p.suffix.lower() in ['.pdf','.docx','.png','.jpg','.zip','.log']:
        errors.append('Private, generated, or binary file tracked: '+rel)
        continue
    f=root/p
    if f.is_symlink():errors.append('Symlink tracked: '+rel);continue
    if not f.is_file():continue
    text=f.read_text(errors='replace')
    for pattern in [r'gh[pousr]_[A-Za-z0-9]{25,}',r'sk-[A-Za-z0-9_-]{24,}',r'-----BEGIN [A-Z ]*PRIVATE KEY-----',r'/Use'+r'rs/[^/]+/',r'(?i)authorization:\s*bearer\s+[A-Za-z0-9._-]{20,}']:
        if re.search(pattern,text):errors.append('Potential secret or machine-specific path: '+rel);break
if not files:errors.append('No tracked files: git add the intended public sources before auditing.')
if errors:print('\n'.join(errors),file=sys.stderr);sys.exit(1)
print(f'Public source audit passed: {len(files)} tracked files; no private/generated data or detected credentials.')
