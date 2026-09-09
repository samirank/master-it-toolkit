#!/usr/bin/env python3
"""Optional inventory for Windows/Linux/macOS, Python 3.9+. Dashboard needs no Python.
Recognized ZIP downloads are organized during CLI scans. Never executes a tool. --what-if does not write.
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
import zipfile
import hashlib
import stat
import sys

def installer_file(path, tool):
    name=path.name.casefold()
    return path.suffix.lower()=='.msi' or (path.suffix.lower()=='.exe' and (tool.get('kind')=='Installer' or
        re.search(r'setup|(?:^|[-_.])install(?:er)?(?:[-_.]|$)',name) or (tool['id']=='7zip' and re.match(r'^7z\d+',name))))

def archive_target(archive):
    info=archive.stat();signature={'size':info.st_size,'mtimeNs':info.st_mtime_ns}
    relative=archive.relative_to(ROOT).as_posix()
    identity=hashlib.sha256((relative+json.dumps(signature,sort_keys=True)).encode()).hexdigest()[:16]
    target=safe_path((archive.parent/'Ready'/(archive.stem[:80]+'-'+identity)).relative_to(ROOT).as_posix())
    return target,signature

def extracted(archive, known_files=None):
    try:
        target,signature=archive_target(archive);marker=target/'.toolkit-extracted.json'
        if not (marker.is_file() and not reparse(marker) and json.loads(marker.read_text())==signature): return False
        with zipfile.ZipFile(archive) as source:
            for member in source.infolist():
                if member.is_dir(): continue
                path=target.joinpath(*member.filename.replace('\\','/').split('/'))
                if known_files is not None:
                    if known_files.get(path)!=member.file_size:return False
                elif reparse(path) or not path.is_file() or path.stat().st_size!=member.file_size:return False
        return True
    except (OSError,ValueError,zipfile.BadZipFile):return False

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
    indexed={}; failures={}; abandoned=[]
    for folder in roots:
        entries=[]
        try:
            base=safe_path(folder)
            def walk(directory):
                with os.scandir(directory) as children:
                    for entry in children:
                        st=entry.stat(follow_symlinks=False)
                        if entry.is_symlink() or getattr(st,'st_file_attributes',0)&0x400: continue
                        if entry.is_dir(follow_symlinks=False):
                            if entry.name.startswith('.extract-'):
                                if datetime.datetime.now().timestamp()-st.st_mtime>86400: abandoned.append(Path(entry.path))
                            else: walk(entry.path)
                        elif entry.is_file(follow_symlinks=False): entries.append((Path(entry.path),st))
            if base.is_dir(): walk(base)
        except (OSError, ValueError) as error: failures[folder]=str(error)
        indexed[folder]=entries
    candidates={}; known_files={p:s.st_size for values in indexed.values() for p,s in values}; archive_checks={}
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
                runnable=[(f,st) for f,st in matches if not installer_file(f,tool) and not f.name.lower().endswith(('.zip','.7z','.tar.gz','.tar.xz','.tar.bz2','.tgz'))]
                complete=bool(runnable)
                if tool.get('inventoryMatch')=='all': complete=complete and all(any(fnmatch.fnmatchcase(f.name.casefold(),p.casefold()) for f,st in runnable) for p in patterns)
                packages=[(f,st) for f,st in pool if any(fnmatch.fnmatchcase(f.name.casefold(),p.casefold()) for p in tool.get('packagePatterns',[]))]
                trusted=[]
                for receipt in receipts.get(tool['id'],[]):
                    for f,st in pool:
                        if f.relative_to(ROOT).as_posix()==receipt.get('path') and st.st_size==receipt.get('size'):
                            packages.append((f,st)); trusted.append(receipt)
                combined={str(f):(f,st) for f,st in matches+packages}
                if combined:
                    selected=max(runnable or list(combined.values()),key=lambda pair:pair[1].st_mtime)
                    if tool.get('localExecutable'):
                        expected=safe_path(tool['localExecutable'])
                        selected=next((pair for pair in runnable if pair[0]==expected),selected)
                    f,st=selected
                    record.update(installed=complete,ready=complete,downloaded=bool(combined),localPath=f.relative_to(ROOT).as_posix(),sizeBytes=sum(st.st_size for f,st in combined.values()),lastModified=iso_time(st.st_mtime),files=[dict(path=f.relative_to(ROOT).as_posix(),sizeBytes=st.st_size,lastModified=iso_time(st.st_mtime)) for f,st in combined.values()])
                    if trusted: record['version']=max(trusted,key=lambda r:r.get('savedAt','')).get('version','')
                    if not record['version'] and tool.get('packageVersionPattern'):
                        parsed=re.search(tool['packageVersionPattern'],f.name,re.I)
                        if parsed: record['version']='.'.join(parsed.groups())
                    record['latestVersion']=receipts.get('_latest',{}).get(tool['id'],'')
                record['needsExtraction']=[]
                record['cleanupReview']=[]
                for path,st in ((p,s) for p,s in indexed[root] if base in p.parents):
                    name=path.name.lower()
                    if 'Ready' not in path.parts and str(path) in combined and name.endswith(('.zip','.7z','.tar.gz','.tar.xz','.tar.bz2','.tgz')):
                        if path not in archive_checks:archive_checks[path]=name.endswith('.zip') and extracted(path,known_files)
                        if not archive_checks[path]:
                            record['needsExtraction'].append({'path':path.relative_to(ROOT).as_posix(),'automatic':name.endswith('.zip')})
                    if name.endswith(('.partial','.part','.crdownload','.tmp')) and datetime.datetime.now().timestamp()-st.st_mtime>86400:
                        record['cleanupReview'].append(path.relative_to(ROOT).as_posix())
                record['cleanupReview'] += [p.relative_to(ROOT).as_posix() for p in abandoned if base in p.parents]
                record['packageState']='ready' if complete else 'needs-extraction' if record['needsExtraction'] else 'installer' if any(installer_file(f,tool) for f,st in combined.values()) else 'downloaded' if record['downloaded'] else 'missing'
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

def organize(inventory):
    """Extract recognized ZIP packages transactionally; retain source downloads."""
    result = {'extracted': [], 'skipped': [], 'errors': []}
    candidates = {f['path'] for t in inventory['tools'].values() for f in t['files']
                  if f['path'].lower().endswith('.zip') and 'Ready' not in Path(f['path']).parts}
    pending={item['path'] for record in inventory['tools'].values() for item in record.get('needsExtraction',[]) if item['automatic']}
    for relative in sorted(candidates):
        if relative not in pending:
            result['skipped'].append(relative);continue
        stage = None
        try:
            archive = safe_path(relative)
            info = archive.stat()
            signature = {'size': info.st_size, 'mtimeNs': info.st_mtime_ns}
            identity = hashlib.sha256((relative + json.dumps(signature, sort_keys=True)).encode()).hexdigest()[:16]
            target = safe_path((archive.parent / 'Ready' / (archive.stem[:80] + '-' + identity)).relative_to(ROOT).as_posix())
            marker = target / '.toolkit-extracted.json'
            if target.exists():
                raise ValueError('Extraction folder exists but is incomplete or changed; preserving its contents. Review the Ready folder before extracting again.')
            with zipfile.ZipFile(archive) as source:
                members = source.infolist()
                total = sum(m.file_size for m in members)
                if len(members) > 50000 or total > 8 * 1024**3:
                    raise ValueError('Archive exceeds automatic extraction limits')
                if total + 256 * 1024**2 > shutil.disk_usage(ROOT).free:
                    raise ValueError('Insufficient free space to retain and extract archive')
                names = set()
                for member in members:
                    name = member.filename.replace('\\', '/')
                    parts = name.rstrip('/').split('/')
                    mode = member.external_attr >> 16
                    if (not name or name.startswith('/') or any(p in ('', '.', '..') or ':' in p or p.endswith((' ', '.')) or
                        re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', p, re.I) for p in parts)
                        or any(c in name for c in '<>"|?*') or any(ord(c) < 32 for c in name)
                        or (stat.S_IFMT(mode) and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)))
                        or member.flag_bits & 1 or name.casefold().rstrip('/') in names
                        or name.casefold().rstrip('/') == '.toolkit-extracted.json'):
                        raise ValueError('Unsafe, encrypted, or duplicate archive member: ' + name)
                    names.add(name.casefold().rstrip('/'))
                target.parent.mkdir(parents=True, exist_ok=True)
                stage = Path(tempfile.mkdtemp(prefix='.extract-', dir=target.parent))
                for member in members:
                    output = stage.joinpath(*member.filename.replace('\\', '/').rstrip('/').split('/'))
                    if member.is_dir():
                        output.mkdir(parents=True, exist_ok=True)
                    else:
                        output.parent.mkdir(parents=True, exist_ok=True)
                        with source.open(member) as src, output.open('xb') as dst:
                            shutil.copyfileobj(src, dst, 1024 * 1024)  # ZipFile verifies CRC while reading.
                        if os.name != 'nt' and (member.external_attr >> 16) & 0o111:
                            output.chmod(0o755)
                if archive.stat().st_mtime_ns != info.st_mtime_ns or archive.stat().st_size != info.st_size:
                    raise ValueError('Archive changed during extraction; retry scan')
                (stage / '.toolkit-extracted.json').write_text(json.dumps(signature), encoding='utf-8')
                stage.rename(target)
                stage = None
                result['extracted'].append(relative)
        except (OSError, ValueError, RuntimeError, zipfile.BadZipFile, NotImplementedError) as error:
            result['errors'].append(relative + ': ' + str(error))
        finally:
            if stage is not None:
                # Only this invocation's validated, uniquely created staging directory.
                stage.resolve().relative_to(ROOT.resolve())
                shutil.rmtree(stage)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--what-if', action='store_true', help='Scan without writing')
    parser.add_argument('--full-storage', action='store_true', help='Also measure every storage folder; slower on large SSDs')
    parser.add_argument('--no-organize', action='store_true', help='Inventory only; leave ZIP packages untouched')
    args = parser.parse_args()
    inventory = scan(args.full_storage)
    if not args.what_if and not args.no_organize:
        organization = organize(inventory)
        if organization['extracted']:
            inventory = scan(args.full_storage)
        inventory['organization'] = organization
        for record in inventory['tools'].values():
            record['organizationErrors']=[error for error in organization['errors'] if any(error.startswith(f['path']+': ') for f in record['files'])]
        print('ZIP organization:', len(organization['extracted']), 'extracted;', len(organization['skipped']), 'already organized;', len(organization['errors']), 'issues.')
        for error in organization['errors']: print(error)
    sys.path.insert(0,str(ROOT))
    import host_inventory
    text=safe_path('assets/js/tools-data.js').read_text('utf-8-sig')
    catalog=json.loads(re.search(r'window\.TOOLKIT_DATA\s*=\s*(\[.*\])\s*;?\s*$',text,re.S).group(1))
    host_inventory.apply(catalog,inventory)
    print('Host detection:',sum(t.get('hostInstalled') is True for t in inventory['tools'].values()),'catalog tools registered on',inventory['host']['name'],';',inventory['host']['durationMs'],'ms.')
    print('Needs extraction:',sum(bool(t.get('needsExtraction')) for t in inventory['tools'].values()),'; cleanup review:',sum(bool(t.get('cleanupReview')) for t in inventory['tools'].values()),'(no original downloads or recovery records deleted).')
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
