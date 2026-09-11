"""Versioned toolkit ZIP snapshots to an existing local, NAS or cloud-sync folder."""
import hashlib,json,os,secrets,shutil,sqlite3,tempfile,time,zipfile
from pathlib import Path
DB='70_DOCUMENTATION/Service-Notes/Activity/activity.sqlite'
EXCLUDED={'90_TEMP','.toolkit-backups','.git','__pycache__'}

def linked(path):
    return path.is_symlink() or bool(getattr(path.lstat(),'st_file_attributes',0)&0x400)

def destination(root,value):
    if not isinstance(value,str) or not value.strip():raise ValueError('Choose an existing destination folder')
    path=Path(value).expanduser()
    if not path.is_absolute() or not path.is_dir():raise ValueError('Use an absolute path to an existing mounted, NAS or cloud-sync folder')
    path=path.resolve();root=root.resolve()
    if path==root or root in path.parents:raise ValueError('Backup destination must be outside the toolkit folder')
    return path

def runtime_cache_patterns(root):
    """Back up verified runtime archives, not rebuildable expanded browser caches."""
    patterns=[]
    for label in ('windows-x64','linux-x64','macos-arm64'):
        folder=root/'runtimes'/label;archive=folder/'browser.zip';manifest=folder/'platform.json'
        if not archive.is_file():continue
        if linked(folder) or linked(archive) or linked(manifest):raise ValueError('Linked runtime archive is not supported')
        expected=json.loads(manifest.read_text('utf-8')).get('browserArchiveSha256')
        digest=hashlib.sha256()
        with archive.open('rb') as source:
            for block in iter(lambda:source.read(1024*1024),b''):digest.update(block)
        if digest.hexdigest()!=expected:raise ValueError('Damaged browser runtime archive: '+label+'. Replace it before a full backup, or back up the workspace separately.')
        patterns.extend('runtimes/'+label+'/'+name for name in ('browser','.browser-*','.previous-browser-*'))
    return patterns

def files(root,scope):
    import fnmatch
    caches=runtime_cache_patterns(root) if scope=='full' else []
    result=[];skipped=[]
    for folder,dirs,names in os.walk(root,followlinks=False):
        folder=Path(folder)
        kept=[]
        for name in dirs:
            path=folder/name;relative=path.relative_to(root)
            if name in EXCLUDED or relative.as_posix()=='70_DOCUMENTATION/Service-Notes/BrowserProfile':continue
            if any(fnmatch.fnmatchcase(relative.as_posix(),pattern) for pattern in caches):continue
            if linked(path):skipped.append(str(relative));continue
            if scope=='workspace' and len(relative.parts)==1 and name not in ('assets','60_SCRIPTS','70_DOCUMENTATION'):continue
            kept.append(name)
        dirs[:]=kept
        for name in names:
            path=folder/name;relative=path.relative_to(root).as_posix()
            if name.endswith(('.partial','.pyc')) or relative in (DB+'-wal',DB+'-shm',DB+'-journal'):continue
            if linked(path):skipped.append(relative);continue
            if not path.is_file():continue
            result.append((path,'MASTER-IT-TOOLKIT/'+relative))
    if scope=='full' and not (root.parent/'.git').exists():
        for name in ('Start-Windows.exe','Start-Linux.sh','Start-macOS.command','Master-IT-Toolkit.exe','Start-Master-IT-Toolkit','Master-IT-Toolkit'):
            p=root.parent/name
            if p.is_file() and not linked(p):result.append((p,name))
    return result,skipped

def backup(root,body,progress,cancelled=lambda:False):
    root=Path(root).resolve();scope=body.get('scope','workspace')
    if scope not in ('workspace','full'):raise ValueError('Unknown backup scope')
    target=destination(root,body.get('destination'))
    progress({'stage':'scan','message':'Preparing backup file list…'})
    selected,skipped=files(root,scope)
    total=sum(p.stat().st_size for p,_ in selected)
    if shutil.disk_usage(target).free < total+32*1024*1024:raise ValueError('Destination needs at least the uncompressed source size plus 32 MB free')
    name='master-it-'+scope+'-'+time.strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(4)+'.zip'
    final=target/name;partial=target/(name+'.partial')
    manifest={'schema':1,'scope':scope,'createdAt':time.time(),'files':{},'skippedLinks':skipped,'excluded':['temporary files','browser sessions','update rollback archives']}
    done=0;owned=False
    try:
        with tempfile.TemporaryDirectory(prefix='master-it-snapshot-') as temporary:
            snapshot=Path(temporary)/'activity.sqlite'
            dbpath=root/DB
            if any(name=='MASTER-IT-TOOLKIT/'+DB for _,name in selected) and not dbpath.read_bytes().startswith(b'MITVAULT1\n'):
                if linked(dbpath):raise ValueError('Linked database cannot be backed up')
                source=sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True,timeout=5)
                dest=sqlite3.connect(snapshot)
                try:
                    source.backup(dest,pages=256,progress=lambda *_: (_ for _ in ()).throw(InterruptedError('Backup cancelled')) if cancelled() else None)
                    if dest.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('SQLite snapshot integrity check failed')
                finally:dest.close();source.close()
            with zipfile.ZipFile(partial,'x',compression=zipfile.ZIP_STORED if scope=='full' else zipfile.ZIP_DEFLATED,allowZip64=True) as archive:
                owned=True
                for original,arcname in selected:
                    if cancelled():raise InterruptedError('Backup cancelled')
                    path=snapshot if arcname=='MASTER-IT-TOOLKIT/'+DB and snapshot.exists() else original
                    before=path.stat();sha=hashlib.sha256();size=0
                    info=zipfile.ZipInfo(arcname);info.external_attr=(before.st_mode & 0xFFFF)<<16;info.compress_type=archive.compression
                    with path.open('rb') as source,archive.open(info,'w',force_zip64=True) as output:
                        while True:
                            if cancelled():raise InterruptedError('Backup cancelled')
                            block=source.read(4*1024*1024)
                            if not block:break
                            output.write(block);sha.update(block);size+=len(block);done+=len(block)
                            progress({'stage':'backup','message':'Backing up '+arcname,'received':done,'total':total})
                    after=path.stat()
                    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('File changed during backup: '+arcname+'. Close the application and retry.')
                    manifest['files'][arcname]={'size':size,'sha256':sha.hexdigest()}
                archive.writestr('toolkit-backup-manifest.json',json.dumps(manifest,indent=2))
            verify(partial,progress,cancelled)
            if cancelled():raise InterruptedError('Backup cancelled')
            with partial.open('rb+') as completed:os.fsync(completed.fileno())
            partial.rename(final)
            if os.name!='nt':
                fd=os.open(str(target),os.O_RDONLY)
                try:os.fsync(fd)
                finally:os.close(fd)
        return 'Backup saved and verified: '+str(final)+'\n'+str(len(selected))+' files; '+str(len(skipped))+' linked paths skipped. Browser sessions, temporary files and old update backups excluded.\nCloud upload completion must be checked in your sync client. Archive is not encrypted.'
    finally:
        if owned and partial.exists():partial.unlink()

def verify(path,progress=lambda _:None,cancelled=lambda:False):
    if not Path(path).is_file():raise ValueError('Choose an existing backup ZIP file')
    progress({'stage':'verify','message':'Verifying backup checksums…'})
    with zipfile.ZipFile(path) as archive:
        names=archive.namelist()
        if len(names)!=len(set(names)):raise ValueError('Duplicate archive entries')
        info=archive.getinfo('toolkit-backup-manifest.json')
        if info.file_size>20_000_000:raise ValueError('Invalid backup manifest')
        manifest=json.loads(archive.read(info))
        if manifest.get('schema')!=1 or not isinstance(manifest.get('files'),dict):raise ValueError('Not a toolkit backup')
        if set(names)!=(set(manifest['files'])|{'toolkit-backup-manifest.json'}):raise ValueError('Backup file list mismatch')
        for name,expected in manifest['files'].items():
            if name.startswith(('/','\\')) or '..' in Path(name).parts or ':' in name or '\\' in name:raise ValueError('Unsafe backup path')
            sha=hashlib.sha256();size=0
            with archive.open(name) as source:
                while True:
                    if cancelled():raise InterruptedError('Backup cancelled')
                    block=source.read(4*1024*1024)
                    if not block:break
                    sha.update(block);size+=len(block)
            if size!=expected['size'] or sha.hexdigest()!=expected['sha256']:raise ValueError('Backup checksum mismatch: '+name)
    return 'Backup checksums verified. Close the toolkit and extract into an empty folder to restore. Workspace-only backups need a fresh toolkit installation for application payloads.'

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--destination');parser.add_argument('--scope',choices=['workspace','full'],default='workspace');parser.add_argument('--verify');args=parser.parse_args()
    if args.verify:print(verify(Path(args.verify)))
    elif args.destination:print(backup(Path(__file__).resolve().parents[2],vars(args),lambda p:print(p['message'])))
    else:parser.error('Specify --destination or --verify')
