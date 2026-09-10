"""Encrypted incremental NAS/cloud-folder backups using the official restic executable."""
import base64,json,os,shutil,subprocess,queue,threading,sys
from pathlib import Path
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import secure_vault

def executable(root):
    installed=shutil.which('restic')
    if installed:return installed
    folder=root/'20_PORTABLE_APPS/Backup/restic'
    files=[p for p in folder.rglob('*') if p.is_file() and (p.name=='restic' or p.name=='restic.exe' or p.name.startswith('restic_') and p.suffix=='.exe')]
    if len(files)!=1:raise ValueError('Download and extract the official restic package first; one restic executable is required.')
    return str(files[0])

def recover_key(metadata,secret,recovery=False):
    """Unwrap the repository key even if the original SSD no longer exists."""
    if not isinstance(secret,str) or len(secret)>1024:raise ValueError('Invalid recovery secret')
    try:
        doc=json.loads(Path(metadata).read_text(encoding='utf-8'))
        field='recovery' if recovery else 'password'
        key=secure_vault.open_seal(secure_vault.derive(secret,secure_vault.un64(doc['salt'])),doc[field],('mit-'+field+'-v1').encode())
        if len(key)!=32:raise ValueError('Invalid key')
        return key
    except Exception:raise ValueError('Incorrect secret or damaged backup key file') from None

def run(root,settings,progress,cancelled=lambda:False,repository_key=None):
    root=Path(root).resolve();db=root/'70_DOCUMENTATION/Service-Notes/Activity/activity.sqlite'
    key=repository_key if repository_key is not None else secure_vault.KEYS.get(str(db.resolve()))
    if key is None:raise ValueError('Set up and unlock the private vault before encrypted backup.')
    keep=settings.get('keepLast',0)
    if type(keep) is not int or not 0<=keep<=100:raise ValueError('Invalid retention count')
    if settings.get('scope','workspace') not in ('workspace','full'):raise ValueError('Invalid backup scope')
    target=Path(settings['destination'])
    if not target.is_absolute() or not target.is_dir():raise ValueError('Backup destination is unavailable')
    target=target.resolve()
    if target==root or root in target.parents:raise ValueError('Repository must be outside the toolkit')
    repo=target/'restic-repository';binary=executable(root)
    if repo.resolve().parent!=target:raise ValueError('Repository cannot redirect outside the destination')
    env={k:v for k,v in os.environ.items() if not k.upper().startswith('RESTIC_')}
    env.update(RESTIC_PASSWORD=base64.urlsafe_b64encode(key).decode(),RESTIC_REPOSITORY=str(repo))
    def command(args):
        if cancelled():raise InterruptedError('Encrypted backup cancelled')
        proc=subprocess.Popen([binary,'--no-cache',*args],cwd=root.parent,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',bufsize=1,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        pending=queue.Queue(maxsize=128)
        def read_output():
            try:
                for line in proc.stdout:pending.put(line)
            finally:pending.put(None)
        reader=threading.Thread(target=read_output,daemon=True);reader.start()
        lines=[]
        try:
            while True:
                if cancelled():raise InterruptedError('Encrypted backup cancelled')
                try:line=pending.get(timeout=.2)
                except queue.Empty:continue
                if line is None:break
                lines.append(line.rstrip());lines=lines[-40:]
                progress({'stage':'backup','message':line.rstrip()[:500]})
            if proc.wait()!=0:raise RuntimeError('Restic failed: '+'\n'.join(lines)[-4000:])
            return '\n'.join(lines)
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
            while reader.is_alive():
                try:pending.get(timeout=.2)
                except queue.Empty:pass
            proc.stdout.close()
    operation=settings.get('operation','backup')
    if operation not in ('backup','snapshots','restore'):raise ValueError('Unknown backup operation')
    if operation=='snapshots':return command(['snapshots','--json'])
    if operation=='restore':
        snapshot=settings.get('snapshot','')
        import re
        if not re.fullmatch('[a-f0-9]{8,64}',snapshot):raise ValueError('Select a snapshot ID from this repository')
        output=Path(settings.get('restoreDestination',''))
        if not output.is_absolute() or not output.is_dir() or any(output.iterdir()):raise ValueError('Restore into an existing empty folder')
        output=output.resolve()
        if output==root or root in output.parents or output==target or target in output.parents:raise ValueError('Restore outside the toolkit and backup repository')
        return command(['restore',snapshot,'--target',str(output),'--verify'])
    if repository_key is not None:raise ValueError('Recovery mode only lists or restores backups')
    marker=target/'toolkit-backup-key.json'
    if (repo/'config').exists():
        if not marker.is_file():raise ValueError('Existing repository has no toolkit recovery metadata; choose a new destination')
        saved=json.loads(marker.read_text(encoding='utf-8'));current=secure_vault.header(db)
        if any(saved.get(k)!=current[k] for k in ('salt','password','recovery')):raise ValueError('This repository belongs to another vault; choose a different backup folder')
    else:command(['init'])
    # Wrapping metadata permits recovery with the saved recovery key without exposing the backup password.
    doc=secure_vault.header(db);secure_vault.atomic(target/'toolkit-backup-key.json',json.dumps({k:doc[k] for k in ('salt','password','recovery')}).encode())
    paths=[str(root)] if settings.get('scope')=='full' else [str(root/p) for p in ('assets','60_SCRIPTS','70_DOCUMENTATION') if (root/p).exists()]
    if settings.get('scope')=='full':
        for name in ('Master-IT-Toolkit.exe','Start-Master-IT-Toolkit','Master-IT-Toolkit'):
            launcher=root.parent/name
            if launcher.is_file() and not launcher.is_symlink():paths.append(str(launcher))
    # Relative sources avoid archiving unrelated drive/user parent ACLs and make
    # restores portable when the SSD drive letter changes.
    args=['backup','--json','--tag','master-it-toolkit',*[str(Path(p).relative_to(root.parent)) for p in paths]]
    for pattern in ['**/90_TEMP/**','**/.toolkit-backups/**','**/BrowserProfile/**','**/*.partial','**/__pycache__/**']:args+=['--exclude',pattern]
    message=command(args)
    command(['check'])
    if keep:command(['forget','--keep-last',str(keep),'--tag','master-it-toolkit','--prune'])
    return 'Encrypted incremental backup completed and repository metadata checked.\n'+message

if __name__=='__main__':
    import argparse,getpass
    parser=argparse.ArgumentParser(description='Recover an encrypted toolkit backup after SSD loss. Secrets are prompted locally.')
    parser.add_argument('destination');parser.add_argument('--recovery-key',action='store_true')
    parser.add_argument('--snapshot');parser.add_argument('--restore-to')
    args=parser.parse_args()
    if bool(args.snapshot)!=bool(args.restore_to):parser.error('--snapshot and --restore-to must be used together')
    key=recover_key(Path(args.destination)/'toolkit-backup-key.json',getpass.getpass('Recovery key: ' if args.recovery_key else 'Vault passphrase: '),args.recovery_key)
    settings={'destination':args.destination,'operation':'restore' if args.snapshot else 'snapshots','snapshot':args.snapshot,'restoreDestination':args.restore_to}
    print(run(Path(__file__).resolve().parents[2],settings,lambda event:print(event['message']),repository_key=key))
