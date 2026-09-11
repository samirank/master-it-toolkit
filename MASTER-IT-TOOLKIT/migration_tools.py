"""Reviewed regular-file migration into a job-owned destination; never mirrors or deletes sources."""
import hashlib,json,os,re,secrets,shutil,time
from pathlib import Path

def linked(path):return path.is_symlink() or bool(getattr(path.lstat(),'st_file_attributes',0)&0x400)
def fingerprint(path):
    s=path.stat();return [s.st_size,s.st_mtime_ns]
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def within(base,name):
    p=Path(name)
    if p.is_absolute() or '..' in p.parts or ':' in name or '\\' in name:raise ValueError('Unsafe migration path')
    target=base/p;target.resolve().relative_to(base.resolve())
    for part in [target,*target.parents]:
        if part==base.parent:break
        if part.is_symlink() or part.exists() and linked(part):raise ValueError('Migration path contains a link or placeholder')
    return target

def plan(source,destination,job):
    if not re.fullmatch('[a-f0-9]{24}',job):raise ValueError('Invalid migration job')
    src=Path(source);dst=Path(destination)
    if not src.is_absolute() or not dst.is_absolute() or not src.is_dir() or not dst.is_dir():raise ValueError('Choose existing absolute source and destination folders')
    if linked(src) or linked(dst):raise ValueError('Use actual folders instead of links or cloud placeholders')
    src=src.resolve();dst=dst.resolve()
    if src.parent==src or dst==src or src in dst.parents or dst in src.parents:raise ValueError('Choose separate folders; entire drive roots and overlapping paths are not supported')
    files=[];directories=[];skipped=[];total=0
    def walk(folder):
        nonlocal total
        with os.scandir(folder) as children:
            for entry in children:
                p=Path(entry.path);name=p.relative_to(src).as_posix()
                if entry.is_symlink() or getattr(entry.stat(follow_symlinks=False),'st_file_attributes',0)&0x400:
                    skipped.append(name);continue
                if entry.is_dir(follow_symlinks=False):
                    directories.append(name);walk(p)
                elif entry.is_file(follow_symlinks=False):
                    state=fingerprint(p);files.append([name,*state]);total+=state[0]
                else:skipped.append(name)
                if len(files)+len(directories)+len(skipped)>100000:raise ValueError('Migration exceeds 100,000 entries; split it into smaller jobs')
    walk(src);files.sort();directories.sort();skipped.sort()
    names=[f[0] for f in files]+directories
    if len({n.casefold() for n in names})!=len(names):raise ValueError('Source has names that collide on a case-insensitive destination')
    for name in names:within(src,name)
    identity=hashlib.sha256(json.dumps([str(src),str(dst),files,directories,skipped],sort_keys=True).encode()).hexdigest()
    remaining=total;output=dst/('Master-IT-Migration-'+job)
    if output.is_dir() and not linked(output):
        try:
            if json.loads(within(output,'migration.json').read_text('utf-8'))==dict(job=job,source=str(src),identity=identity):
                for name,size,_ in files:
                    existing=within(output/'data',name)
                    if existing.is_file() and existing.stat().st_size==size:remaining-=size
        except (ValueError,OSError):pass
    if remaining+256*1024**2>shutil.disk_usage(dst).free:raise ValueError('Destination does not have enough free space for the remaining migration copy')
    return dict(source=str(src),destination=str(dst),output=str(dst/('Master-IT-Migration-'+job)),job=job,files=files,directories=directories,skipped=skipped,total=total,identity=identity,token=secrets.token_hex(24),created=time.time())

def publish_file(source,target):
    if os.name=='nt':os.rename(source,target);return
    try:os.link(source,target)
    except FileExistsError:raise
    except OSError:
        import ctypes,sys
        libc=ctypes.CDLL(None,use_errno=True)
        if sys.platform.startswith('linux') and hasattr(libc,'renameat2'):
            result=libc.renameat2(-100,os.fsencode(source),-100,os.fsencode(target),1)
        elif sys.platform=='darwin' and hasattr(libc,'renamex_np'):
            result=libc.renamex_np(os.fsencode(source),os.fsencode(target),4)
        else:raise ValueError('Destination lacks safe exclusive file publishing')
        if result:raise OSError(ctypes.get_errno(),os.strerror(ctypes.get_errno()))
        return
    source.unlink()

def summary(p):return {k:v for k,v in p.items() if k not in ('files','directories','skipped')}|dict(fileCount=len(p['files']),directoryCount=len(p['directories']),skippedCount=len(p['skipped']),skipped=p['skipped'][:25])

def copy(p,progress,cancelled=lambda:False):
    if time.time()-p['created']>600:raise ValueError('Copy preview expired. Review a fresh plan.')
    fresh=plan(p['source'],p['destination'],p['job'])
    if fresh['identity']!=p['identity']:raise ValueError('Source or destination changed since preview. Review a fresh plan.')
    source=Path(p['source']);output=Path(p['output']);parent=Path(p['destination'])
    if output.parent!=parent or output.name!='Master-IT-Migration-'+p['job']:raise ValueError('Invalid job destination')
    if cancelled():raise InterruptedError('Migration cancelled before copying')
    ownership=dict(job=p['job'],source=p['source'],identity=p['identity'])
    if output.exists():
        if linked(output) or json.loads(within(output,'migration.json').read_text('utf-8'))!=ownership:raise ValueError('Existing migration folder does not match this job; preserving it')
    else:
        output.mkdir()
        with (output/'migration.json').open('x',encoding='utf-8') as f:json.dump(ownership,f);f.flush();os.fsync(f.fileno())
    data=within(output,'data');data.mkdir(exist_ok=True)
    for name in p['directories']:within(data,name).mkdir(parents=True,exist_ok=True)
    total=0;copied=0;reused=0;last=0
    def publish(name,force=False):
        nonlocal last
        if force or time.monotonic()-last>=1:
            progress(dict(message='Copying '+name,received=total,total=p['total'],copied=copied,reused=reused,output=str(data)));last=time.monotonic()
    for name,size,mtime in p['files']:
        if cancelled():raise InterruptedError('Migration stopped; verified copies remain available for this job to resume.')
        src=within(source,name);target=within(data,name)
        if fingerprint(src)!=[size,mtime]:raise ValueError('Source changed: '+name)
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():
            if not target.is_file() or target.stat().st_size!=size or digest(src)!=digest(target):raise ValueError('Existing destination file differs; preserving it: '+name)
            total+=size;reused+=1;publish(name);continue
        temporary=within(output,'partial-'+hashlib.sha256(name.encode()).hexdigest()+'.tmp')
        # This fixed partial path belongs only to this job/file; a restart can
        # safely replace its incomplete bytes while leaving verified files intact.
        try:
            checksum=hashlib.sha256();written=0
            with src.open('rb') as inp,temporary.open('wb') as out:
                while True:
                    if cancelled():raise InterruptedError('Migration stopped; originals and completed copies were retained.')
                    block=inp.read(1024*1024)
                    if not block:break
                    written+=len(block)
                    if written>size:raise ValueError('Source grew during copy: '+name)
                    out.write(block);checksum.update(block);total+=len(block);publish(name)
                out.flush();os.fsync(out.fileno())
            if written!=size or fingerprint(src)!=[size,mtime] or digest(src)!=checksum.hexdigest():raise ValueError('Source changed during copy: '+name)
            if digest(temporary)!=checksum.hexdigest():raise ValueError('Destination verification failed: '+name)
            os.utime(temporary,ns=(mtime,mtime))
            # link() is atomic and refuses to replace existing files. The job
            # folder may be on exFAT/SMB, where Windows rename also refuses replacement.
            publish_file(temporary,target)
            copied+=1
        finally:
            if temporary.exists():temporary.unlink()
    publish('Complete',True)
    return dict(output=str(data),copied=copied,reused=reused,bytes=total,skipped=len(p['skipped']),verified=True)
