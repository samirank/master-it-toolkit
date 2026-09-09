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

def scan(full_storage=False):
    text = safe_path('assets/js/tools-data.js').read_text(encoding='utf-8-sig')
    match = re.search(r'window\.TOOLKIT_DATA\s*=\s*(\[.*\])\s*;?\s*$', text, re.S)
    if not match: raise ValueError('Catalog must contain a JSON array assignment')
    catalog = json.loads(match.group(1))
    inventory = dict(schemaVersion=2, generatedAt=iso_time(datetime.datetime.now().timestamp()),
                     tools={}, storage={'folders':{}, 'volume':None}, errors=[], scanMode='full' if full_storage else 'quick')
    try: receipts = json.loads(safe_path('assets/download-receipts.json').read_text('utf-8'))
    except (OSError, ValueError): receipts = {}
    requested = sorted(set(t['localFolder'] for t in catalog if t.get('localFolder')) | (set(FOLDERS) if full_storage else set()), key=lambda x:(len(x),x))
    roots=[]
    for folder in requested:
        if not any(folder==r or folder.startswith(r+'/') for r in roots): roots.append(folder)
    indexed={}; failures={}
    for folder in roots:
        entries=[]
        try:
            base=safe_path(folder)
            def walk(directory):
                with os.scandir(directory) as children:
                    for entry in children:
                        st=entry.stat(follow_symlinks=False)
                        if entry.is_symlink() or getattr(st,'st_file_attributes',0)&0x400: continue
                        if entry.is_dir(follow_symlinks=False): walk(entry.path)
                        elif entry.is_file(follow_symlinks=False): entries.append((Path(entry.path),st))
            if base.is_dir(): walk(base)
        except (OSError, ValueError) as error: failures[folder]=str(error)
        indexed[folder]=entries
    candidates={}
    for tool in catalog:
        record=dict(installed=False, downloaded=False, ready=False, localPath='',files=[],sizeBytes=0,lastModified='',version='',scanError='')
        folder=tool.get('localFolder'); patterns=tool.get('inventoryPatterns',[])
        if folder:
            try:
                base=safe_path(folder)
                root=next(r for r in roots if folder==r or folder.startswith(r+'/'))
                if root in failures: raise ValueError(failures[root])
                if folder not in candidates: candidates[folder]=[(f,st) for f,st in indexed[root] if base in f.parents and st.st_size>0]
                pool=candidates[folder]
                matches=[(f,st) for f,st in pool if any(fnmatch.fnmatchcase(f.name.casefold(),p.casefold()) for p in patterns)]
                complete=bool(matches)
                if tool.get('inventoryMatch')=='all': complete=complete and all(any(fnmatch.fnmatchcase(f.name.casefold(),p.casefold()) for f,st in matches) for p in patterns)
                packages=[(f,st) for f,st in pool if any(fnmatch.fnmatchcase(f.name.casefold(),p.casefold()) for p in tool.get('packagePatterns',[]))]
                trusted=[]
                for receipt in receipts.get(tool['id'],[]):
                    for f,st in pool:
                        if f.relative_to(ROOT).as_posix()==receipt.get('path') and st.st_size==receipt.get('size'):
                            packages.append((f,st)); trusted.append(receipt)
                combined={str(f):(f,st) for f,st in matches+packages}
                if combined:
                    selected=max(combined.values(),key=lambda pair:pair[1].st_mtime)
                    if tool.get('localExecutable'):
                        expected=safe_path(tool['localExecutable'])
                        selected=next((pair for pair in matches if pair[0]==expected),selected)
                    f,st=selected
                    record.update(installed=complete,ready=complete,downloaded=bool(complete or packages),localPath=f.relative_to(ROOT).as_posix(),sizeBytes=sum(st.st_size for f,st in combined.values()),lastModified=iso_time(st.st_mtime),files=[dict(path=f.relative_to(ROOT).as_posix(),sizeBytes=st.st_size,lastModified=iso_time(st.st_mtime)) for f,st in combined.values()])
                    if trusted: record['version']=max(trusted,key=lambda r:r.get('savedAt','')).get('version','')
                    if not record['version'] and tool.get('packageVersionPattern'):
                        parsed=re.search(tool['packageVersionPattern'],f.name,re.I)
                        if parsed: record['version']='.'.join(parsed.groups())
                    record['latestVersion']=receipts.get('_latest',{}).get(tool['id'],'')
            except (OSError, ValueError, StopIteration) as error:
                record['scanError']=str(error);inventory['errors'].append(tool['id']+': '+str(error))
        inventory['tools'][tool['id']]=record
    for folder in FOLDERS:
        try:
            inventory['storage']['folders'][folder]=sum(st.st_size for f,st in indexed.get(folder,[])) if full_storage else (None if safe_path(folder).exists() else 0)
        except (OSError,ValueError): inventory['storage']['folders'][folder]=None
    usage=shutil.disk_usage(ROOT)
    inventory['storage']['volume']=dict(totalBytes=usage.total,freeBytes=usage.free)
    return inventory

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--what-if', action='store_true', help='Scan without writing')
    parser.add_argument('--full-storage', action='store_true', help='Also measure every storage folder; slower on large SSDs')
    args = parser.parse_args()
    inventory = scan(args.full_storage)
    print('Downloaded or ready files present for', sum(t['downloaded'] for t in inventory['tools'].values()),
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
