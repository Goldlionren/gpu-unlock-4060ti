#!/usr/bin/env python3
"""Export an explicit source-only publication snapshot; never installs anything."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    dest = args.destination.resolve()
    if dest.exists():
        raise SystemExit('Destination already exists; choose a fresh directory')
    paths = [ROOT/name for name in ('README.md', 'LICENSE', 'NOTICE.md', '.gitignore')]
    for folder in ('src', 'scripts', 'tests', 'integration', 'reports'):
        for path in sorted((ROOT/folder).rglob('*')):
            if not path.is_file() or '__pycache__' in path.parts:
                continue
            if path.name == 'SESSION_STATE.md':
                continue
            if path.suffix in ('.c', '.h', '.py', '.md', '.json', '.service') or path.name in (
                    'Kbuild', 'Makefile', 'LICENSE', 'dkms.conf',
                    'before-nvidia', 'initramfs-hook', 'gpu-unlock'):
                # Kbuild's generated C file is not source.
                if not path.name.endswith('.mod.c'):
                    paths.append(path)
    paths.append(ROOT/'logs/README.md')
    records = []
    for path in paths:
        relative = path.relative_to(ROOT)
        target = dest/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        records.append({'path': str(relative), 'bytes': path.stat().st_size,
                        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    (ROOT/'logs/publication-files.json').write_text(json.dumps(records, indent=2)+'\n')
    print(json.dumps({'files': len(records), 'bytes': sum(p['bytes'] for p in records),
                      'destination': str(dest)}, indent=2))

if __name__ == '__main__':
    main()
