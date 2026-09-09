"""Build a clean archive and optional Pages directory from tracked source files.
No payloads, customer files, development folders or generated inventory are copied.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[2]
NAME='NEIGHBOR-CIRCUIT-TOOLKIT'
EMPTY=b'// Unscanned inventory; run a local updater to detect your files.\nwindow.LOCAL_INVENTORY = {"generatedAt":null,"tools":{},"storage":null,"errors":[]};\n'

def source_files():
    raw=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode('utf-8')
    result={}
    for name in raw.split('\0'):
        if not name:continue
        if name in ['index.html','README.md'] or name.startswith(NAME+'/'):
            p=ROOT/name
            if not p.is_file() or p.is_symlink():raise ValueError('Unexpected source path: '+name)
            if name.endswith('/local-inventory.js'):continue
            result[name]=p.read_bytes()
    if NAME+'/index.html' not in result:raise ValueError('Stage the toolkit source before building.')
    result[NAME+'/assets/js/local-inventory.js']=EMPTY
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--site',type=Path,help='Optional fresh Pages output directory')
    args=parser.parse_args()
    files=source_files()
    archive=ROOT/(NAME+'.zip')
    catalog=json.loads(files[NAME+'/assets/toolkit-manifest.json'])
    folders={t['localFolder'] for t in catalog if t['localFolder']}
    # Git has no empty directories. Include every defined destination in the archive.
    folders.update(json.loads((ROOT/'.github/folders.json').read_text('utf-8')))
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for folder in sorted(folders):
            info=zipfile.ZipInfo(NAME+'/'+folder.rstrip('/')+'/');info.external_attr=0o40755<<16;z.writestr(info,b'')
        for name,body in sorted(files.items()):
            info=zipfile.ZipInfo(name);info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,body)
    if args.site:
        if args.site.exists():raise ValueError('Pages staging destination must be new: '+str(args.site))
        args.site.mkdir(parents=True)
        for name,body in files.items():
            p=args.site/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body)
        (args.site/archive.name).write_bytes(archive.read_bytes())
        (args.site/'.nojekyll').write_text('',encoding='utf-8')
    print('Built',archive.name, 'SHA256',hashlib.sha256(archive.read_bytes()).hexdigest())

if __name__=='__main__':main()
