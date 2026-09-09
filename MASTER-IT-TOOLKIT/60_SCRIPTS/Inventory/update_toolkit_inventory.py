#!/usr/bin/env python3
"""Optional inventory for Windows/Linux/macOS, Python 3.9+. Dashboard needs no Python.
Reads filenames and metadata only. Never executes a tool. --what-if does not write.
"""
import argparse
import datetime
import fnmatch
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[2]
FOLDERS = ['00_BOOT','10_WINDOWS_TOOLBOX','20_PORTABLE_APPS','30_DRIVERS',
           '40_INSTALLERS','50_FIRMWARE','60_SCRIPTS','70_DOCUMENTATION',
           '80_LICENSED_TOOLS','90_TEMP']

def reparse(p):
    return p.is_symlink() or (p.exists() and bool(getattr(p.lstat(), 'st_file_attributes', 0) & 0x400))

def safe_path(relative):
    if not isinstance(relative, str) or not relative or ':' in relative:
        raise ValueError('Expected toolkit-relative path')
    relative = relative.replace('\\', '/')
    if Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('Path escapes toolkit')
    p = ROOT
    for part in Path(relative).parts:
        p = p / part
        if reparse(p): raise ValueError('Symlinks/junctions are not scanned')
    p.resolve().relative_to(ROOT.resolve())
    return p

def files(folder):
    base = safe_path(folder)
    if not base.is_dir(): return []
    result = []
    def failure(error): raise error
    for current, dirs, names in os.walk(base, followlinks=False, onerror=failure):
        dirs[:] = [d for d in dirs if not reparse(Path(current)/d)]
        for name in names:
            f = Path(current)/name
            if not reparse(f) and f.is_file(): result.append(f)
    return result

def iso_time(timestamp):
    return datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc).isoformat()

def scan():
    text = safe_path('assets/js/tools-data.js').read_text(encoding='utf-8-sig')
    match = re.search(r'window\.TOOLKIT_DATA\s*=\s*(\[.*\])\s*;?\s*$', text, re.S)
    if not match: raise ValueError('Catalog must contain a JSON array assignment')
    catalog = json.loads(match.group(1))
    inventory = dict(schemaVersion=1, generatedAt=iso_time(datetime.datetime.now().timestamp()),
                     tools={}, storage={'folders':{}, 'volume':None}, errors=[])
    cache = {}
    for tool in catalog:
        record = dict(installed=False, localPath='', files=[], sizeBytes=0,
                      lastModified='', version='', scanError='')
        folder, patterns = tool.get('localFolder'), tool.get('inventoryPatterns', [])
        if folder and patterns:
            try:
                if folder not in cache: cache[folder] = files(folder)
                matches = [f for f in cache[folder] if f.stat().st_size > 0 and
                           any(fnmatch.fnmatchcase(f.name.casefold(), p.casefold()) for p in patterns)]
                complete = bool(matches)
                if tool.get('inventoryMatch') == 'all':
                    complete = complete and all(any(fnmatch.fnmatchcase(f.name.casefold(), p.casefold())
                                                   for f in matches) for p in patterns)
                if matches:
                    selected = max(matches, key=lambda f:f.stat().st_mtime)
                    expected = tool.get('localExecutable')
                    if expected and safe_path(expected) in matches: selected = safe_path(expected)
                    record.update(installed=complete, localPath=selected.relative_to(ROOT).as_posix(),
                                  sizeBytes=sum(f.stat().st_size for f in matches),
                                  lastModified=iso_time(selected.stat().st_mtime),
                                  files=[dict(path=f.relative_to(ROOT).as_posix(), sizeBytes=f.stat().st_size,
                                              lastModified=iso_time(f.stat().st_mtime)) for f in matches])
                    # No subprocess or binary parsing: version remains explicitly unknown.
            except (OSError, ValueError) as error:
                record['scanError'] = str(error)
                inventory['errors'].append(tool['id'] + ': ' + str(error))
        inventory['tools'][tool['id']] = record
    for folder in FOLDERS:
        try: inventory['storage']['folders'][folder] = sum(f.stat().st_size for f in files(folder))
        except (OSError, ValueError) as error:
            inventory['storage']['folders'][folder] = None
            inventory['errors'].append(folder + ': ' + str(error))
    usage = shutil.disk_usage(ROOT)
    inventory['storage']['volume'] = dict(totalBytes=usage.total, freeBytes=usage.free)
    return inventory

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--what-if', action='store_true', help='Scan without writing')
    args = parser.parse_args()
    inventory = scan()
    print('Expected files present for', sum(t['installed'] for t in inventory['tools'].values()),
          'records;', len(inventory['errors']), 'scan errors.')
    if args.what_if:
        print('Preview only; no files written.')
        return
    destination = safe_path('assets/js/local-inventory.js')
    payload = '// Generated inventory; no software was executed.\nwindow.LOCAL_INVENTORY = ' + json.dumps(inventory, indent=2) + ';\n'
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=destination.parent,
                                     prefix='inventory-', suffix='.tmp', delete=False) as f:
        f.write(payload)
        temporary = f.name
    os.replace(temporary, destination)
    print('Saved', destination, '\nReload the dashboard. File presence is not compatibility verification.')

if __name__ == '__main__': main()
