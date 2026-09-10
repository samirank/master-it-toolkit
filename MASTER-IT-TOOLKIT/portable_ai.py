"""SSD-local model preparation and ephemeral, authenticated loopback inference."""
import atexit,hashlib,json,os,platform,posixpath,secrets,shutil,socket,stat,subprocess,tarfile,threading,time,urllib.request,zipfile
from pathlib import Path,PurePosixPath

JOBS={};GUARD=threading.Lock();PROCESSES=set()
FOLDER='20_PORTABLE_APPS/AI/ToolkitAssistant'

def host():
    architecture=platform.machine().lower()
    return {'Darwin':'macOS'}.get(platform.system(),platform.system())+'-'+('arm64' if architecture in ('arm64','aarch64') else 'x64' if architecture in ('amd64','x86_64') else architecture)

def safe(base,relative):
    p=PurePosixPath(relative)
    if not relative or p.is_absolute() or any(x in ('..','') or ':' in x or '\\' in x for x in p.parts):raise ValueError('Unsafe AI package path')
    target=base.joinpath(*p.parts)
    if base.resolve() not in target.resolve().parents:raise ValueError('AI path leaves toolkit folder')
    for parent in [target,*target.parents]:
        if parent==base.parent:break
        if parent.is_symlink() or parent.exists() and bool(getattr(parent.lstat(),'st_file_attributes',0)&0x400):raise ValueError('AI package links are not allowed')
    return target

def folder(root):return safe(Path(root),FOLDER)
def manifest(root):return json.loads((Path(root)/'assets/portable-ai.json').read_text('utf-8'))
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def valid(path,artifact):return path.is_file() and path.stat().st_size==artifact['size'] and digest(path)==artifact['sha256']

class HTTPSOnly(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if not newurl.startswith('https://'):raise ValueError('Insecure AI download redirect rejected')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def download(artifact,target,progress,cancelled):
    if valid(target,artifact):return
    if not artifact['url'].startswith('https://'):raise ValueError('AI downloads require HTTPS')
    target.parent.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(target.parent).free<artifact['size']+100*1024*1024:raise ValueError('Not enough free space for AI download')
    partial=target.with_name('.'+target.name+'.'+secrets.token_hex(8)+'.partial')
    try:
        request=urllib.request.Request(artifact['url'],headers={'User-Agent':'Master-IT-Toolkit','Accept-Encoding':'identity'})
        count=0;checksum=hashlib.sha256()
        with urllib.request.build_opener(HTTPSOnly()).open(request,timeout=30) as response,partial.open('xb') as output:
            while True:
                if cancelled():raise InterruptedError('AI preparation cancelled')
                block=response.read(1024*1024)
                if not block:break
                count+=len(block)
                if count>artifact['size']:raise ValueError('AI download exceeded the pinned size')
                output.write(block);checksum.update(block)
                progress(dict(message='Downloading '+artifact['name'],received=count,total=artifact['size']))
            output.flush();os.fsync(output.fileno())
        if count!=artifact['size'] or checksum.hexdigest()!=artifact['sha256']:raise ValueError('AI download checksum mismatch')
        os.replace(partial,target)
    finally:
        if partial.exists():partial.unlink()

def extract(archive,destination):
    """Extract bounded files; archive-local tar library links become ordinary copies."""
    hashes={};total=0
    def write(name,source,size,mode):
        nonlocal total
        total+=size
        if total>512*1024*1024 or len(hashes)>=2000:raise ValueError('AI runtime extraction limit exceeded')
        target=safe(destination,name)
        if name.casefold() in {x.casefold() for x in hashes}:raise ValueError('Duplicate runtime file')
        target.parent.mkdir(parents=True,exist_ok=True)
        with source,target.open('xb') as output:shutil.copyfileobj(source,output)
        if target.stat().st_size!=size:raise ValueError('Incomplete runtime file')
        target.chmod(0o755 if mode&0o111 else 0o644);hashes[name]=digest(target)
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as z:
            for item in z.infolist():
                if item.is_dir():continue
                if stat.S_ISLNK(item.external_attr>>16):raise ValueError('ZIP links are not allowed')
                write(item.filename,z.open(item),item.file_size,item.external_attr>>16)
    else:
        with tarfile.open(archive) as tar:
            members=tar.getmembers();by_name={m.name:m for m in members}
            if len(members)>2000:raise ValueError('Too many runtime files')
            for item in members:
                if item.isdir():continue
                target=item
                for _ in range(8):
                    if not (target.issym() or target.islnk()):break
                    name=posixpath.normpath(posixpath.join(posixpath.dirname(target.name),target.linkname) if target.issym() else target.linkname)
                    safe(destination,name);target=by_name.get(name)
                    if target is None:raise ValueError('Missing library link target')
                if not target.isfile():raise ValueError('Unsupported runtime archive entry')
                write(item.name,tar.extractfile(target),target.size,target.mode)
    return hashes

def prepare(root,selection,progress,cancelled=lambda:False):
    doc=manifest(root);base=folder(root);base.mkdir(parents=True,exist_ok=True)
    platforms=list(doc['runtimes']) if selection=='All' else [selection]
    if any(p not in doc['runtimes'] for p in platforms):raise ValueError('No portable runtime for this platform')
    for license in doc.get('licenses',[]):download(license,safe(base,license['name']),progress,cancelled)
    download(doc['model'],safe(base,doc['model']['name']),progress,cancelled)
    for name in platforms:
        if cancelled():raise InterruptedError('AI preparation cancelled')
        artifact=doc['runtimes'][name];runtime=safe(base,name+'-'+artifact['sha256'][:12])
        if runtime.is_dir():
            verify_runtime(runtime);continue
        package=safe(base,artifact['name']);download(artifact,package,progress,cancelled)
        staging=safe(base,'.prepare-'+secrets.token_hex(8));staging.mkdir()
        try:
            progress(dict(message='Verifying and unpacking '+name,received=0,total=0))
            hashes=extract(package,staging)
            if cancelled():raise InterruptedError('AI preparation cancelled')
            (staging/'files.json').write_text(json.dumps(hashes),encoding='utf-8')
            verify_runtime(staging);os.replace(staging,runtime)
        finally:
            if staging.exists():shutil.rmtree(staging)
            if package.exists():package.unlink()
    progress(dict(message='Portable AI ready on the SSD. Select Portable AI chat.',received=0,total=0))

def verify_runtime(runtime):
    hashes=json.loads(safe(runtime,'files.json').read_text('utf-8'))
    if not hashes or len(hashes)>2000:raise ValueError('Invalid AI runtime receipt')
    for name,checksum in hashes.items():
        if digest(safe(runtime,name))!=checksum:raise ValueError('AI runtime changed; restore its verified package')
    candidates=[safe(runtime,n) for n in hashes if PurePosixPath(n).name in ('llama-server','llama-server.exe')]
    if len(candidates)!=1:raise ValueError('AI server executable is missing or ambiguous')
    return candidates[0]

def status(root):
    doc=manifest(root);base=folder(root);current=host();artifact=doc['runtimes'].get(current)
    installed=[]
    for name,a in doc['runtimes'].items():
        if safe(base,name+'-'+a['sha256'][:12]+'/files.json').is_file():installed.append(name)
    model=safe(base,doc['model']['name'])
    result=dict(platform=current,platforms=list(doc['runtimes']),installed=installed,path=str(base),ready=bool(artifact and current in installed and model.is_file() and model.stat().st_size==doc['model']['size']))
    with GUARD:result.update({k:v for k,v in JOBS.get(str(Path(root).resolve()),{}).items() if k!='cancel'})
    return result

def start_prepare(root,selection,on_progress=None,on_done=None):
    key=str(Path(root).resolve());doc=manifest(root)
    if selection not in [*doc['runtimes'],'All']:raise ValueError('Unsupported AI platform')
    with GUARD:
        if JOBS.get(key,{}).get('busy'):raise ValueError('AI download already running')
        cancel=threading.Event();JOBS[key]=dict(busy=True,message='Preparing portable AI…',received=0,total=0,cancel=cancel)
    def progress(value):
        with GUARD:JOBS[key].update(value)
        if on_progress:on_progress(value)
    def worker():
        try:prepare(root,selection,progress,cancel.is_set)
        except Exception as error:progress(dict(message=str(error),error=True))
        finally:
            progress(dict(busy=False))
            if on_done:on_done()
    threading.Thread(target=worker,daemon=True).start();return {'busy':True,'message':'Portable AI preparation started.'}

def cancel_prepare(root):
    with GUARD:
        job=JOBS.get(str(Path(root).resolve()),{})
        if job.get('cancel'):job['cancel'].set()
    return {'message':'Stopping AI preparation; verified files are retained.'}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('Local AI redirects rejected')

def stop_process(proc):
    if proc.poll() is None:
        proc.terminate()
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()
    PROCESSES.discard(proc)

@atexit.register
def shutdown():
    for proc in list(PROCESSES):stop_process(proc)

def chat(root,messages):
    doc=manifest(root);base=folder(root);artifact=doc['runtimes'].get(host())
    if not artifact:raise ValueError('Portable AI is unavailable for this platform')
    model=safe(base,doc['model']['name'])
    if not valid(model,doc['model']):raise ValueError('Prepare or repair the portable model first')
    runtime=safe(base,host()+'-'+artifact['sha256'][:12]);binary=verify_runtime(runtime)
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    token=secrets.token_urlsafe(32)
    env={k:v for k,v in os.environ.items() if not k.upper().startswith(('LLAMA_','HF_','HUGGINGFACE_'))}
    env['LLAMA_API_KEY']=token
    command=[str(binary),'--model',str(model),'--host','127.0.0.1','--port',str(port),'--ctx-size','8192','--parallel','1','--threads',str(min(os.cpu_count() or 2,8)),'--n-gpu-layers','0','--offline','--no-webui','--log-disable']
    proc=subprocess.Popen(command,cwd=binary.parent,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    PROCESSES.add(proc)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    def request(path,body=None,timeout=2):
        req=urllib.request.Request('http://127.0.0.1:'+str(port)+path,data=json.dumps(body).encode() if body is not None else None,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        with opener.open(req,timeout=timeout) as response:raw=response.read(2000001)
        if len(raw)>2000000:raise ValueError('AI response too large')
        return json.loads(raw)
    try:
        deadline=time.monotonic()+90
        while True:
            if proc.poll() is not None:raise ValueError('Portable AI could not start on this CPU/OS. Catalog guidance remains available.')
            try:
                if request('/health').get('status')=='ok':break
            except (OSError,ValueError):pass
            if time.monotonic()>deadline:raise ValueError('Portable AI startup timed out')
            time.sleep(.2)
        result=request('/v1/chat/completions',dict(messages=messages,max_tokens=500,temperature=.2,stream=False,chat_template_kwargs={'enable_thinking':False}),timeout=240)
        return result['choices'][0]['message']['content']
    finally:stop_process(proc)
