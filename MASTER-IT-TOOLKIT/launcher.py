"""Optional loopback launcher. Python 3.9+, standard library only."""
import hashlib
import io
import json
import mimetypes
import os
from pathlib import Path, PurePosixPath
import secrets
import socket
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(sys.executable if getattr(sys, 'frozen', False) else __file__).resolve().parent
if (ROOT / 'MASTER-IT-TOOLKIT' / 'launcher.py').is_file(): ROOT = ROOT / 'MASTER-IT-TOOLKIT'
# New bundles place Linux/macOS executables inside platform runtime folders.
if getattr(sys, 'frozen', False) and not (ROOT / 'launcher.py').is_file():
    for candidate in list(ROOT.parents)[:3]:
        if (candidate / 'launcher.py').is_file() and (candidate / 'assets/toolkit-manifest.json').is_file():
            ROOT = candidate
            break
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "60_SCRIPTS/Runtime"))
# The frozen bootstrap imports these for dependency collection. Load updated SSD
# source modules on restart instead of reusing the copies cached inside the EXE.
if getattr(sys, 'frozen', False):
    for module in ('tool_downloads','install_tools','host_inventory','portable_tools','activity_store','browser_host','offline_assistant','secure_vault','portable_ai','migration_tools','setup_wizard','trusted_computers','platform_runtime'):
        sys.modules.pop(module,None)
REPO = 'samirank/master-it-toolkit'
MANIFEST = 'assets/distribution-files.json'
SCRIPTS = {
    'check-updates': ('Check downloaded tool updates', 'tool_downloads.py', 'all'),
    'inventory': ('Scan local inventory', '60_SCRIPTS/Inventory/update_toolkit_inventory.py', 'all'),
    'pc': ('PC diagnostics', '60_SCRIPTS/Diagnostics/Get-PCDiagnostics.ps1', 'windows'),
    'network': ('Network diagnostics', '60_SCRIPTS/Network/Get-NetworkDiagnostics.ps1', 'windows'),
    'repair': ('Repair Windows system files', '60_SCRIPTS/Windows-Repair/Repair-WindowsFiles.ps1', 'windows'),
    'metadata': ('Refresh publisher metadata', '60_SCRIPTS/Inventory/Update-ToolkitMetadata.ps1', 'windows'),
    'manifest': ('Export catalog manifest', '60_SCRIPTS/Inventory/Export-ToolkitManifest.ps1', 'windows'),
}

def safe_path(root, name):
    if not isinstance(name, str) or '\\' in name or ':' in name:
        raise ValueError('Invalid path')
    parts = PurePosixPath(name).parts
    if not parts or name.startswith('/') or any(p in ('.', '..') for p in parts):
        raise ValueError('Invalid path')
    target = root.joinpath(*parts)
    for parent in [target, *target.parents]:
        if parent == root: break
        if parent.is_symlink() or (hasattr(parent, 'is_junction') and parent.is_junction()):
            raise ValueError('Linked paths are not supported')
    target.resolve().relative_to(root.resolve())
    return target

def managed_name(name):
    if name.startswith('runtime-extensions/ubol/'): return True
    if name == '70_DOCUMENTATION/Service-Notes/README.txt': return True
    if name == '10_WINDOWS_TOOLBOX/06_Account-OOBE/Unattended/autounattend.xml': return True
    if name in ('index.html', 'README.txt', 'START-HERE.txt', 'LICENSE.txt', 'launcher.py', 'tool_downloads.py', 'install_tools.py', 'host_inventory.py', 'portable_tools.py', 'activity_store.py', 'browser_host.py', 'offline_assistant.py', 'secure_vault.py', 'portable_ai.py', 'migration_tools.py', 'setup_wizard.py', 'Start-Toolkit.cmd', 'Start-Toolkit.command'):
        return True
    if name.startswith('assets/'):
        return name not in (MANIFEST, 'assets/js/local-inventory.js', 'assets/download-receipts.json', 'assets/download-catalog-cache.json') and Path(name).suffix in ('.js', '.css', '.json', '.png', '.svg')
    if name.startswith(('60_SCRIPTS/', '70_DOCUMENTATION/')):
        return '/Service-Notes/' not in name and Path(name).suffix in ('.ps1', '.py', '.html', '.txt')
    return name.endswith('/PLACE-FILES-HERE.txt') or name == '90_TEMP/README.txt'

def digest(data):
    return hashlib.sha256(data).hexdigest()


def sync_directory(path):
    if os.name=='nt': return  # File fsync is available; Windows has no portable directory fsync.
    fd=os.open(str(path),os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)

def durable_write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name('.'+path.name+'.'+secrets.token_hex(8)+'.tmp')
    try:
        with temporary.open('xb') as output:
            output.write(data);output.flush();os.fsync(output.fileno())
        os.replace(temporary,path);sync_directory(path.parent)
    finally:
        if temporary.exists():temporary.unlink()

def recover_update(root):
    journal=safe_path(root,'.toolkit-backups/pending-update.json')
    if not journal.exists():return False
    plan=json.loads(journal.read_text('utf-8'));folder=plan['backup']
    if not isinstance(folder,str) or not folder.startswith('.toolkit-backups/') or len(PurePosixPath(folder).parts)!=2:raise ValueError('Invalid update recovery folder')
    restored={}
    if not isinstance(plan['files'],dict) or len(plan['files'])>5001:raise ValueError('Invalid recovery plan')
    for name,expected in plan['files'].items():
        if name!=MANIFEST and not managed_name(name):raise ValueError('Invalid recovery path')
        safe_path(root,name)
        before=safe_path(root,folder+'/'+name).read_bytes() if expected is not None else None
        if before is not None and digest(before)!=expected:raise ValueError('Recovery backup checksum mismatch')
        restored[name]=before
    for name,before in restored.items():
        p=safe_path(root,name)
        if before is None:
            if p.exists():p.unlink();sync_directory(p.parent)
        else:durable_write(p,before)
    journal.unlink();sync_directory(journal.parent)
    return True

if __name__=='__main__' and recover_update(ROOT):
    print('Interrupted update recovered. Restart the launcher to load the restored files.',flush=True)
    sys.exit(0)

import tool_downloads
import install_tools
import host_inventory
import portable_tools
import activity_store
import browser_host
import offline_assistant
import secure_vault
import trusted_computers

def cleanup_update_archives(root):
    """Remove known installer ZIPs from an installed launcher root, never a repo."""
    root = Path(root).absolute()
    parent = root.parent
    if root.name != 'MASTER-IT-TOOLKIT' or (parent / '.git').exists():
        return ''
    if not any((parent / name).is_file() for name in ('Start-Windows.exe','Start-Linux.sh','Start-macOS.command','Master-IT-Toolkit.exe', 'Master-IT-Toolkit')):
        return ''
    messages = []
    for name in ('MASTER-IT-TOOLKIT.zip', 'standalone-windows-x64.zip',
                 'standalone-linux-x64.zip', 'standalone-macos-arm64.zip', 'standalone-all-platforms.zip'):
        try:
            path = safe_path(parent, name)
            if not path.is_file():
                continue
            with zipfile.ZipFile(path) as package:
                required = {'MASTER-IT-TOOLKIT/launcher.py', 'MASTER-IT-TOOLKIT/index.html',
                            'MASTER-IT-TOOLKIT/' + MANIFEST}
                if not required.issubset(package.namelist()):
                    continue
            path.unlink()
            messages.append('Removed installer archive: ' + name + '.')
        except (OSError, ValueError, zipfile.BadZipFile) as error:
            messages.append('Installer cleanup skipped for ' + name + ': ' + str(error))
    return ('\n' + '\n'.join(messages)) if messages else ''


def install_archive(blob, root=ROOT):
    recover_update(root)
    """Validate first; preserve changes; back up originals; roll back failed writes."""
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        prefix = 'MASTER-IT-TOOLKIT/'
        names = archive.namelist()
        if len(names) != len(set(names)) or sum(i.file_size for i in archive.infolist()) > 100_000_000:
            raise ValueError('Invalid or oversized archive')
        manifest_bytes = archive.read(prefix + MANIFEST)
        incoming = json.loads(manifest_bytes)
        if not isinstance(incoming, dict) or len(incoming) > 5000:
            raise ValueError('Invalid distribution manifest')
        old = json.loads((root / MANIFEST).read_text('utf-8'))
        replacements = {}
        for name, expected in incoming.items():
            safe_path(root, name)
            if not managed_name(name): raise ValueError('Unmanaged update path: ' + name)
            data = archive.read(prefix + name)
            if digest(data) != expected: raise ValueError('Checksum mismatch: ' + name)
            replacements[name] = data
    changes = {}
    for name in set(old) | set(incoming):
        # Older packages tracked this generated metadata file; retain local refreshes.
        if name == 'assets/js/metadata.js': continue
        if not managed_name(name): raise ValueError('Invalid existing manifest')
        p = safe_path(root, name)
        current = p.read_bytes() if p.exists() else None
        desired = replacements.get(name)
        if current == desired: continue
        if current is not None and digest(current) != old.get(name):
            raise ValueError('Local changes preserved; update stopped: ' + name)
        changes[name] = (current, desired)
    if not changes: return 'Already up to date.' + cleanup_update_archives(root)
    changes[MANIFEST] = ((root / MANIFEST).read_bytes(), manifest_bytes)
    backup = safe_path(root, '.toolkit-backups/' + time.strftime('%Y%m%d-%H%M%S') + '-' + secrets.token_hex(3))
    backup.mkdir(parents=True)
    recovery = {}
    for name, (before, after) in changes.items():
        if before is not None:
            p = safe_path(root, backup.relative_to(root).as_posix()+'/'+name)
            durable_write(p, before)
        recovery[name] = digest(before) if before is not None else None
    journal = safe_path(root, '.toolkit-backups/pending-update.json')
    durable_write(journal,json.dumps({'backup':backup.relative_to(root).as_posix(),'files':recovery}).encode())
    try:
        for name, (before, after) in changes.items():
            p = safe_path(root, name)
            if after is None:
                if p.exists(): p.unlink(); sync_directory(p.parent)
            else: durable_write(p,after)
        journal.unlink(); sync_directory(journal.parent)
    except Exception:
        recover_update(root)
        raise
    return 'Updated toolkit files. Backup: ' + str(backup) + '. Close and restart the launcher to load the new version.' + cleanup_update_archives(root)

def download(url, limit):
    request = urllib.request.Request(url, headers={'User-Agent': 'MasterITToolkit-Updater', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=45) as response:
        data = response.read(limit + 1)
    if len(data) > limit: raise ValueError('Download exceeds size limit')
    return data

def update():
    commit = json.loads(download('https://api.github.com/repos/' + REPO + '/commits/main', 1_000_000))['sha']
    if len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit): raise ValueError('Invalid commit')
    blob = download('https://raw.githubusercontent.com/' + REPO + '/' + commit + '/MASTER-IT-TOOLKIT.zip', 50_000_000)
    return install_archive(blob) + ' Source commit: ' + commit[:12]

def powershell_command(powershell, script, key):
    return [powershell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-NoExit', '-File', str(script), *(['-Repair'] if key == 'repair' else [])]

def run_script(key):
    if key == 'check-updates':
        message=tool_downloads.check_updates(ROOT,safe_path)
        run_script('inventory')
        return message
    label, relative, platform = SCRIPTS[key]
    script = safe_path(ROOT, relative)
    if platform == 'windows':
        if os.name != 'nt': raise ValueError('This script requires Windows')
        powershell = shutil.which('powershell.exe')
        if not powershell: raise ValueError('Windows PowerShell is unavailable')
        process = subprocess.Popen(powershell_command(powershell, script, key), cwd=ROOT, creationflags=subprocess.CREATE_NEW_CONSOLE)
        process.wait()
        return label + ': terminal closed. Review the terminal output for the script result.'
    command = [sys.executable, '--inventory'] if getattr(sys, 'frozen', False) else [sys.executable, str(script)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=600)
    if result.returncode: raise RuntimeError((result.stderr or result.stdout)[-3000:])
    return label + ' completed. ' + result.stdout[-3000:]

class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def server_bind(self):
        # Windows SO_REUSEADDR can let two launchers bind the same port and
        # deliver a new session URL to the old process. Never share a listener.
        if os.name == 'nt':
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    def __init__(self, root=ROOT, port=0):
        if recover_update(root):
            raise RuntimeError("Interrupted update recovered. Restart the launcher to load the restored files.")
        self.root = root
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.Lock()
        self.state = {'busy': False, 'message': 'Ready.'}
        self.events = threading.Condition()
        self.revision = 0
        self.workflow = None
        vault_path = safe_path(root, '70_DOCUMENTATION/Service-Notes/Activity/activity.sqlite')
        trusted_computers.auto_unlock(vault_path)
        self.history = activity_store.Store(root, safe_path, self.token)
        self.cancel_backup = threading.Event()
        self.browser = browser_host.Host(self, safe_path, lambda: run_script('inventory'))
        self.cancel_downloads = threading.Event()
        self.catalog_lock = threading.Lock()
        super().__init__(('127.0.0.1', port), Handler)
        self.origin = 'http://127.0.0.1:' + str(self.server_port)
        self.auto_backup_check = 0
        self.vault_touch=time.time()
    def service_actions(self):
        if time.time()-self.vault_touch>900 and not self.lock.locked():secure_vault.lock(self.history.path)

        if time.time()-self.auto_backup_check<60:return
        self.auto_backup_check=time.time()
        threading.Thread(target=self.auto_backup_tick,daemon=True).start()
    def auto_backup_tick(self):
        # An inactive backup scheduler must not make a user action appear busy.
        if secure_vault.status(self.history.path)['locked']:return
        try:
            preferences=self.history.workspace().get('backupSettings',{})
            if not preferences.get('automatic') or not preferences.get('destination'):return
        except Exception:return
        if not self.lock.acquire(False):return
        handed_off=False
        try:
            settings=self.history.workspace().get('backupSettings',{})
            if not settings.get('automatic') or not settings.get('destination'):return
            key=digest(json.dumps([settings['destination'],settings.get('scope','full')]).encode())
            with self.history.lock:
                db=self.history.connect()
                try:
                    with db:
                        db.execute('CREATE TABLE IF NOT EXISTS automatic_backups (destination TEXT PRIMARY KEY, success REAL, attempt REAL)')
                        row=db.execute('SELECT success,attempt FROM automatic_backups WHERE destination=?',(key,)).fetchone() or (0,0)
                        now=time.time()
                        if now-row[0]<settings.get('intervalHours',24)*3600 or now-row[1]<300:return
                        db.execute('INSERT OR REPLACE INTO automatic_backups VALUES (?,?,?)',(key,row[0],now))
                finally:db.close()
            # Probe the actual destination, not internet access: supports LAN-only NAS and mounted drives.
            if not Path(settings['destination']).is_dir():return
            self.state={'busy':True,'startedAt':time.time(),'message':'Automatic backup: destination available...'}
            handed_off=True
            self.job('backup-toolkit',dict(settings,automaticKey=key))
        except Exception as error:
            self.state={'busy':False,'stage':'error','message':'Automatic backup postponed: '+str(error)}
            self.history.record('automatic-backup',self.state)
        finally:
            if not handed_off:self.lock.release()
    def publish_completion(self):
        with self.events:
            self.revision += 1
            self.events.notify_all()
    def prepare_workflow_step(self, flow, step):
        import platform
        tool=step['tool'];selection={'platform':{'Windows':'Windows','Darwin':'macOS','Linux':'Linux'}.get(platform.system(),'Linux'),'architecture':'arm64' if platform.machine().lower() in ('arm64','aarch64') else 'x86' if platform.machine().lower() in ('x86','i386','i686') else 'x64','mode':'latest' if flow.setup.get('updates') else 'missing','tools':[tool]}
        flow.state('Preparing required tool: '+tool)
        if flow.stop:return 'Preparation cancelled.'
        try:tool_downloads.refresh_catalog(self.root,safe_path)
        except Exception:pass  # Saved catalog supports offline use of already downloaded packages.
        message=tool_downloads.bulk_download(self.root,selection,safe_path,lambda p:flow.state(p.get('message','Preparing tool...')),lambda:run_script('inventory'),self.publish_completion,lambda:flow.stop)
        if flow.stop:return message
        # Inventory also organizes recognized archives; deletion of original files remains excluded.
        message+='\n'+run_script('inventory')
        if step.get('action')=='install' and flow.setup.get('install'):
            info=install_tools.options(self.root,tool,safe_path)
            if info['installedOnHost']:
                import re
                text=(self.root/'assets/js/local-inventory.js').read_text('utf-8-sig')
                inventory=json.loads(text.split('window.LOCAL_INVENTORY =',1)[1].strip().rstrip(';'))
                version=inventory.get('tools',{}).get(tool,{}).get('version','')
                def numeric(value):
                    value=str(value or '').lstrip('v')
                    if not re.fullmatch(r'\d+(\.\d+)*',value):return None
                    return tuple(int(n) for n in value.split('.'))
                latest=numeric(version);installed=[numeric(m.get('version')) for m in info.get('hostMatches',[])]
                newer=bool(latest and installed and all(v and (latest+(0,)*10)[:10]>(v+(0,)*10)[:10] for v in installed))
                if not flow.setup.get('updates') or not newer:return message+'\nAlready installed on this PC; no proven newer package version. Verify or review manually.'
            signed=[f for f in info.get('files',[]) if f.get('signature',{}).get('status')=='Valid']
            if len(signed)==1 and not info.get('reason'):
                file=signed[0]
                flow.state('Installing '+info['name']+' with recovery tracking; follow UAC and installer prompts.')
                message+='\n'+install_tools.install(self.root,{'tool':tool,'package':file['path'],'sha256':file['sha256']},safe_path)
                message+='\n'+run_script('inventory')
            else:message+='\nInstallation needs review: '+(info.get('reason') or 'Choose a single trusted installer.')
        return message
    def job(self, action, body=None):
        context = {'tool': (body or {}).get('tool'), 'startedAt': self.state.get('startedAt',time.time())}
        try:
            if action in ('backup-toolkit','verify-backup'):
                import importlib.util
                spec=importlib.util.spec_from_file_location('toolkit_backup',safe_path(self.root,'60_SCRIPTS/Backup/toolkit_backup.py'))
                backup_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(backup_module)
                self.cancel_backup.clear()
                progress=lambda state:setattr(self,'state',dict(context,busy=True,**state))
                if action=='backup-toolkit' and body.get('engine')=='restic':
                    spec=importlib.util.spec_from_file_location('encrypted_backup',safe_path(self.root,'60_SCRIPTS/Backup/encrypted_backup.py'))
                    encrypted_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(encrypted_module)
                    message=encrypted_module.run(self.root,body,progress,self.cancel_backup.is_set)
                elif action=='backup-toolkit':message=backup_module.backup(self.root,body,progress,self.cancel_backup.is_set)
                else:message=backup_module.verify(Path(body['archive']),progress,self.cancel_backup.is_set)
            elif action == 'catalog-refresh':
                tool_downloads.refresh_catalog(self.root,safe_path)
                message='✓ Download catalog refreshed from the toolkit repository'
            elif action == 'bulk-download':
                self.cancel_downloads.clear()
                try: tool_downloads.refresh_catalog(self.root,safe_path)
                except Exception as error:
                    self.state=dict(context,busy=True,message='Catalog refresh unavailable; using the last saved catalog: '+str(error),stage='resolve')
                message=tool_downloads.bulk_download(self.root,body,safe_path,
                    lambda progress:setattr(self,'state',dict(context,busy=True,**{k:v for k,v in progress.items() if k!='tool'},tool=progress.get('tool'))),
                    lambda:run_script('inventory'),self.publish_completion,self.cancel_downloads.is_set)
            elif action == 'run-portable':
                message = portable_tools.launch(self.root, body['tool'], body['executable'], safe_path,
                    lambda message: setattr(self, 'state', dict(context, busy=True, message=message, stage='running')))
            elif action == 'workflow':
                self.workflow = portable_tools.Workflow(self.root, body['workflow'], body['mode'], safe_path,
                    lambda state: setattr(self, 'state', dict(context, busy=True, stage='workflow', **state)),setup=(body or {}).get('setup'),prepare=self.prepare_workflow_step)
                message = self.workflow.run()
                context['jobId'] = self.workflow.id
                context['machine'] = self.workflow.record['machine']
                context['workflowRecord'] = self.workflow.history
                context['migrationResult'] = self.workflow.record.get('migrationResult')
                context['workflowName'] = self.workflow.definition['name']
                context['workflowProfile'] = body['workflow']
            elif action == 'install':
                message = install_tools.install(self.root, body, safe_path)
                message += '\n' + run_script('inventory')
            elif action in ('installed-apps','system-restore'):
                message = install_tools.recovery(action)
            elif action == 'download':
                message = tool_downloads.save_selected(self.root, body['tool'], body['assets'], safe_path,
                    lambda progress: setattr(self, 'state', dict(context, busy=True, **progress)))
                self.state = dict(context, busy=True, message='Scanning and organizing saved packages…', stage='scan')
                message += '\n' + run_script('inventory')
            else: message = update() if action == 'update' else run_script(action)
            if action=='backup-toolkit' and (body or {}).get('automaticKey'):
                with self.history.lock:
                    db=self.history.connect()
                    try:
                        with db:db.execute('UPDATE automatic_backups SET success=? WHERE destination=?',(time.time(),body['automaticKey']))
                    finally:db.close()
            self.state = dict(context, busy=False, message=message, stage='complete')
        except Exception as error:
            self.state = dict(context, busy=False, message='Stopped: ' + str(error), stage='error')
        finally:
            self.history.record(action, self.state)
            self.workflow = None
            self.lock.release()
            self.publish_completion()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass  # Never log the session token.
    def reply(self, code, data, kind='application/json'):
        if not isinstance(data, bytes): data = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)
    def route(self):
        if self.headers.get('Host') != self.server.origin.split('//')[1]: return None
        prefix = '/' + self.server.token + '/'
        if not self.path.startswith(prefix): return None
        return self.path[len(prefix):].split('?')[0]
    def do_GET(self):
        route = self.route()
        if route is None:
            # Recover only an address-bar/reload navigation to the dashboard.
            # Old API tokens, cross-site links, frames and alternate Host headers stay denied.
            path=urllib.parse.urlsplit(self.path).path
            if (self.headers.get('Host')==self.server.origin.split('//')[1]
                and self.headers.get('Sec-Fetch-Mode')=='navigate'
                and self.headers.get('Sec-Fetch-Dest')=='document'
                and self.headers.get('Sec-Fetch-Site') in ('none','same-origin')
                and (path=='/' or re.fullmatch(r'/[A-Za-z0-9_-]{20,100}/index\.html',path))):
                self.send_response(302)
                self.send_header('Location','/'+self.server.token+'/index.html')
                self.send_header('Cache-Control','no-store')
                self.send_header('Referrer-Policy','no-referrer')
                self.send_header('Content-Length','0')
                self.end_headers();return
            return self.reply(403, {'error': 'This launcher address has expired. Reopen Master-IT-Toolkit to connect to the current session.'})
        if route == 'api/vault':return self.reply(200,trusted_computers.status(self.server.history.path))
        if route == 'api/platforms':
            import platform_runtime
            return self.reply(200,platform_runtime.available(self.server.root))
        if route == 'api/setup':
            if secure_vault.status(self.server.history.path)['locked']:return self.reply(200,{'locked':True})
            try:
                import setup_wizard
                return self.reply(200,setup_wizard.status(self.server.root,self.server.history))
            except Exception as error:return self.reply(503,{'error':str(error)})
        if route == 'api/workspace' and secure_vault.status(self.server.history.path)['locked']:
            return self.reply(200,{'_vaultLocked':True,'preferences':{},'favorites':[],'notes':{},'checklists':{},'capacity':256,'customWorkflows':{},'backupSettings':{}})
        if route == 'api/workspace':
            try: return self.reply(200, self.server.history.workspace())
            except Exception as error: return self.reply(503, {'error': str(error)})
        if route.startswith('api/') and route not in ('api/vault','api/workspace','api/catalog') and secure_vault.status(self.server.history.path)['locked']:
            return self.reply(423,{'error':'Private workspace is locked.'})
        if route == 'api/events':
            self.send_response(200)
            self.send_header('Content-Type','text/event-stream')
            self.send_header('Cache-Control','no-store')
            self.send_header('Referrer-Policy','no-referrer')
            self.end_headers()
            revision = -1
            try:
                while True:
                    with self.server.events:
                        self.server.events.wait_for(lambda: self.server.revision != revision, timeout=15)
                        revision = self.server.revision
                    self.wfile.write(('data: '+json.dumps({'revision':revision})+'\n\n').encode())
                    self.wfile.flush()
            except (BrokenPipeError,ConnectionResetError,OSError): return
        if route == 'api/workflow-jobs':
            try:
                machine=host_inventory.machine_identity()
                all_hosts=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get('all')==['1']
                jobs=self.server.history.workflow_job(machine=None if all_hosts else machine['id'])
                return self.reply(200,{'machine':machine,'jobs':jobs,'activeJob':self.server.workflow.id if self.server.workflow else None})
            except Exception as error:return self.reply(503,{'error':str(error)})
        if route == 'api/history':
            try: return self.reply(200, self.server.history.recent())
            except Exception as error: return self.reply(500, {'error':str(error)})
        if route == 'api/catalog':
            warning=''
            if urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get('refresh')==['1']:
                if self.server.catalog_lock.acquire(False):
                    try: tool_downloads.refresh_catalog(self.server.root,safe_path)
                    except Exception as error: warning=str(error)
                    finally: self.server.catalog_lock.release()
            data=tool_downloads.cached_catalog(self.server.root)
            return self.reply(200,dict(data,warning=warning))
        if route == 'api/run-options':
            try:
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                return self.reply(200, portable_tools.options(self.server.root, query.get('tool',[''])[0], safe_path))
            except Exception as error: return self.reply(400, {'error':str(error)})
        if route == 'api/install-options':
            try:
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                return self.reply(200, install_tools.options(self.server.root, query.get('tool',[''])[0], safe_path))
            except Exception as error: return self.reply(400, {'error':str(error)})
        if route == 'api/tool-files':
            try:
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                folder = tool_folder(self.server.root, query.get('tool', [''])[0])
                files = []
                if folder.exists():
                    for entry in folder.iterdir():
                        try:
                            p = safe_path(self.server.root, entry.relative_to(self.server.root).as_posix())
                            if (p.is_file() or p.is_dir()) and p.name != 'PLACE-FILES-HERE.txt' and not p.name.startswith('.extract-'):
                                st = p.stat()
                                files.append(dict(name=p.name, path=str(p), size=st.st_size if p.is_file() else 0, kind='folder' if p.is_dir() else 'file', modified=st.st_mtime_ns,
                                    partial=p.name.lower().endswith(('.partial', '.crdownload', '.part', '.tmp'))))
                        except (ValueError, OSError): continue
                        if len(files) >= 1000: break
                return self.reply(200, dict(folder=str(folder), files=sorted(files, key=lambda f: f['name'])))
            except (ValueError, OSError, StopIteration) as error: return self.reply(400, {'error': str(error)})
        if route == 'api/download-options':
            try:
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                info=tool_downloads.options(self.server.root, query.get('tool', [''])[0])
                info['adBlocking']=self.server.browser.filtering.get(query.get('tool',[''])[0],True)
                return self.reply(200,info)
            except Exception as error: return self.reply(400, {'error': str(error)})
        if route == 'api/status':
            return self.reply(200, dict(self.server.state, browserNotice=self.server.browser.notice, managedBrowser=self.server.browser.available(), historyError=self.server.history.error, scripts=[{'id': key, 'name': label, 'enabled': platform == 'all' or os.name == 'nt', 'path': path} for key, (label, path, platform) in SCRIPTS.items()]))
        if route == 'api/inventory':
            try:
                text=(self.server.root/'assets/js/local-inventory.js').read_text('utf-8-sig')
                inventory=json.loads(text.split('window.LOCAL_INVENTORY =',1)[1].strip().rstrip(';'))
                if inventory.get('host',{}).get('id') != host_inventory.host_id():
                    for record in inventory.get('tools',{}).values(): record.update(hostInstalled=None,hostMatches=[],hostVersion='')
                    if inventory.get('host'): inventory['host']['stale']=True
                return self.reply(200,inventory)
            except (OSError,ValueError,IndexError): return self.reply(200,{'tools':{}})
        try:
            route = route or 'index.html'
            if route not in ('index.html', 'README.txt', 'START-HERE.txt', 'LICENSE.txt') and not route.startswith(('assets/', '70_DOCUMENTATION/')): raise ValueError()
            if '/Service-Notes/' in route: raise ValueError()
            p = safe_path(self.server.root, route)
            if not p.is_file(): raise ValueError()
            data = p.read_bytes()
            if route == 'index.html':
                config = '<script>window.TOOLKIT_LAUNCHER=true;window.TOOLKIT_HOST_ID=' + json.dumps(host_inventory.host_id()) + ';window.TOOLKIT_LOCAL_BASE=' + json.dumps((self.server.root / 'index.html').as_uri()) + ';</script>'
                data = data.replace(b'</head>', config.encode() + b'<script defer src="assets/js/launcher-client.js"></script></head>')
            return self.reply(200, data, mimetypes.guess_type(route)[0] or 'text/plain')
        except (ValueError, OSError): return self.reply(404, {'error': 'Unavailable'})
    def do_POST(self):
        if self.route() == 'api/focus':
            if self.headers.get('Origin') != self.server.origin:
                return self.reply(403, {'error': 'Invalid local session'})
            url = self.server.origin + '/' + self.server.token + '/index.html'
            if self.server.browser.available(): self.server.browser.focus_dashboard(url)
            else: open_app(url)
            return self.reply(200, {'focused': True})
        if self.route()=='api/vault' and self.headers.get('Origin')==self.server.origin:
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=5000:raise ValueError('Invalid vault request')
                body=json.loads(self.rfile.read(size));operation=body.get('operation')
                if operation=='touch':
                    self.server.vault_touch=time.time()
                    return self.reply(200,secure_vault.status(self.server.history.path))
            except Exception as error:return self.reply(400,{'error':str(error)})
            if not self.server.lock.acquire(False):return self.reply(409,{'error':'Wait for the current job before changing vault state.'})
            try:
                recovery=None
                with self.server.history.lock:
                    if operation=='setup':recovery=secure_vault.setup(self.server.history.path,body.get('secret'))
                    elif operation=='unlock':secure_vault.unlock(self.server.history.path,body.get('secret'),body.get('recovery') is True)
                    elif operation=='lock':secure_vault.lock(self.server.history.path)
                    elif operation=='trust':trusted_computers.enroll(self.server.history.path,body.get('secret'),body.get('recovery') is True,body.get('name',''))
                    elif operation=='revoke':trusted_computers.revoke(self.server.history.path,body.get('id'))
                    elif operation=='master-unlock':
                        if not trusted_computers.auto_unlock(self.server.history.path):raise ValueError('This OS account could not unlock the vault. Use your passphrase or recovery key.')
                    else:raise ValueError('Unknown vault operation')
                self.server.vault_touch=time.time()
                if operation in ('setup','unlock','trust','master-unlock'):self.server.history=activity_store.Store(self.server.root,safe_path,self.server.token)
                return self.reply(200,dict(trusted_computers.status(self.server.history.path),recoveryKey=recovery))
            except Exception as error:return self.reply(400,{'error':str(error)})
            finally:self.server.lock.release()
        if self.route() and self.route().startswith('api/') and secure_vault.status(self.server.history.path)['locked']:
            return self.reply(423,{'error':'Workspace locked. Unlock the vault to use recorded actions or save data.'})

        if self.route()=='api/setup' and self.headers.get('Origin')==self.server.origin:
            try:
                import setup_wizard
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=1000:raise ValueError('Invalid setup request')
                return self.reply(200,setup_wizard.save(self.server.root,self.server.history,json.loads(self.rfile.read(size))))
            except Exception as error:return self.reply(400,{'error':str(error)})
        if self.route()=='api/migration-plan' and self.headers.get('Origin')==self.server.origin:
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=2000:raise ValueError('Invalid copy preview request')
                body=json.loads(self.rfile.read(size))
                if not self.server.workflow:raise ValueError('Start a migration workflow first')
                return self.reply(200,self.server.workflow.preview_copy(body.get('run'),body.get('step')))
            except Exception as error:return self.reply(400,{'error':str(error)})
        if self.route() == 'api/assistant' and self.headers.get('Origin') == self.server.origin:
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 20000: raise ValueError('Assistant request too large')
                body = json.loads(self.rfile.read(size))
                if isinstance(body,dict) and body.get('operation')=='portable-prepare':
                    if not self.server.lock.acquire(False):return self.reply(409,{'error':'Wait for the current toolkit job before preparing AI.'})
                    self.server.state={'busy':True,'startedAt':time.time(),'message':'Preparing portable AI on the SSD…'}
                    def progress(value):self.server.state.update(value)
                    def done():
                        self.server.state.update(busy=False,stage='error' if self.server.state.get('error') else 'complete')
                        try:self.server.history.record('portable-ai',self.server.state)
                        finally:self.server.lock.release();self.server.publish_completion()
                    try:result=offline_assistant.portable_ai.start_prepare(self.server.root,body.get('platform',offline_assistant.portable_ai.host()),progress,done)
                    except Exception as error:
                        self.server.state.update(busy=False,stage='error',message=str(error))
                        self.server.lock.release();raise
                    return self.reply(202,result)
                return self.reply(200, offline_assistant.handle(self.server.root, self.server.history, body))
            except (ValueError, TypeError, KeyError) as error: return self.reply(400, {'error': str(error)})
            except Exception as error: return self.reply(503, {'error': str(error)})
        if self.route() == 'api/workspace' and self.headers.get('Origin') == self.server.origin:
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 2_100_000: raise ValueError('Workspace request is too large')
                body = json.loads(self.rfile.read(size))
                if body.get('key')=='setupState':raise ValueError('Use the setup wizard to save its progress')
                if not isinstance(body.get('key'), str): raise ValueError('Invalid workspace key')
                self.server.history.workspace(body['key'], body['value'])
                return self.reply(200, {'saved': True})
            except (ValueError, KeyError, TypeError) as error: return self.reply(400, {'error': str(error)})
            except Exception as error: return self.reply(503, {'error': str(error)})
        if self.route() != 'api/action' or self.headers.get('Origin') != self.server.origin:
            return self.reply(403, {'error': 'Invalid local session'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 32000: raise ValueError()
            body = json.loads(self.rfile.read(size))
            action = body['action']
            if body.get('confirmed') is not True or action not in (*SCRIPTS, 'backup-toolkit','verify-backup','cancel-backup','update', 'download', 'bulk-download', 'cancel-downloads', 'catalog-refresh', 'install', 'installed-apps', 'system-restore', 'run-portable', 'workflow', 'workflow-control', 'vendor-window', 'open-folder', 'adblock-site'): raise ValueError()
            if action=='backup-toolkit' and (not isinstance(body.get('destination'),str) or body.get('scope') not in ('workspace','full')):raise ValueError()
            if action=='verify-backup' and (not isinstance(body.get('archive'),str) or not Path(body['archive']).is_absolute()):raise ValueError()
            if action=='bulk-download' and (body.get('platform') not in ('Windows','Linux','macOS','All') or body.get('architecture') not in ('x64','x86','arm64','All') or body.get('mode') not in ('missing','latest')): raise ValueError()
            if action == 'run-portable' and not all(isinstance(body.get(k),str) for k in ('tool','executable')): raise ValueError()
            if action == 'workflow' and not all(isinstance(body.get(k),str) for k in ('workflow','mode')): raise ValueError()
            if action == 'install':
                if not all(isinstance(body.get(key), str) for key in ('tool','package','sha256')): raise ValueError()
            if action == 'download':
                if not isinstance(body.get('tool'), str) or not isinstance(body.get('assets'), list) or not 1 <= len(body['assets']) <= 50 or any(not isinstance(a, str) for a in body['assets']): raise ValueError()
        except (ValueError, KeyError, TypeError): return self.reply(400, {'error': 'Invalid action'})
        if action=='cancel-backup':
            self.cancel_backup.set()
            return self.reply(200,{'message':'Stopping backup; incomplete archive will be removed.'})
        if action=='cancel-downloads':
            self.server.cancel_downloads.set()
            return self.reply(200,{'message':'Queue will stop after the active transfer. Completed packages are kept.'})
        if action == 'adblock-site':
            try:
                tool_folder(self.server.root,body.get('tool'))
                if type(body.get('enabled')) is not bool: raise ValueError('Invalid ad blocking setting')
                self.server.browser.filtering[body['tool']] = body['enabled']
                return self.reply(200,{'message':'Publisher-site ad blocking '+('enabled' if body['enabled'] else 'disabled')})
            except Exception as error: return self.reply(400,{'error':str(error)})
        if action == 'open-folder':
            try:
                folder=tool_folder(self.server.root,body.get('tool'))
                folder.mkdir(parents=True,exist_ok=True)
                if os.name=='nt': os.startfile(str(folder))
                else: subprocess.Popen(['open' if sys.platform=='darwin' else 'xdg-open',str(folder)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                return self.reply(200,{'message':'Opened destination folder','folder':str(folder)})
            except Exception as error:return self.reply(400,{'error':str(error)})
        if action == 'vendor-window':
            try:
                catalog = json.loads((self.server.root/'assets/toolkit-manifest.json').read_text('utf-8'))
                tool = next((t for t in catalog if t['id'] == body.get('tool')), None)
                if not tool or not tool.get('officialDownload','').startswith('https://'): raise ValueError('Unknown publisher')
                self.server.browser.open(tool['officialDownload'], tool['id'])
                return self.reply(202, {'message':'Publisher window opening. Downloads will be saved in this tool’s folder and scanned automatically.'})
            except Exception as error: return self.reply(400, {'error':str(error)})
        if action == 'workflow-control':
            try:
                if not self.server.workflow: raise ValueError('No workflow is running')
                self.server.workflow.control(body)
                return self.reply(200, {'message':'Workflow control accepted'})
            except ValueError as error: return self.reply(409, {'error':str(error)})
        if not self.server.lock.acquire(False): return self.reply(409, {'error': 'Another action is still running. Close its script terminal first.'})
        label = SCRIPTS[action][0] if action in SCRIPTS else {'backup-toolkit':'Backing up toolkit','verify-backup':'Verifying toolkit backup','catalog-refresh':'Refreshing repository download catalog','bulk-download':'Downloading toolkit packages','run-portable':'Opening portable application','workflow':'Starting reviewed workflow','update':'Updating toolkit from GitHub','download':'Downloading selected packages','install':'Preparing recovery checkpoint and installing application (check UAC and installer prompts)','installed-apps':'Opening installed programs','system-restore':'Opening System Restore'}[action]
        self.server.state = {'busy': True, 'startedAt': time.time(), 'tool': body.get('tool'), 'message': label + '…' + (' Check the script terminal for prompts; close it when finished.' if action in SCRIPTS and SCRIPTS[action][2] == 'windows' else '')}
        threading.Thread(target=self.server.job, args=(action, body), daemon=True).start()
        self.reply(202, self.server.state)

    def do_PUT(self):
        if self.route() != 'api/import' or self.headers.get('Origin') != self.server.origin:
            return self.reply(403, {'error': 'Invalid local session'})
        if not self.server.lock.acquire(False): return self.reply(409, {'error': 'Another action is running'})
        temporary = None
        handed_off = False
        started_at = time.time()
        try:
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            tool = query.get('tool', [''])[0]; name = query.get('name', [''])[0]
            folder = tool_folder(self.server.root, tool)
            if not name or Path(name).name != name or '/' in name or '\\' in name or ':' in name or name.startswith('.'):
                raise ValueError('Invalid package filename')
            catalog=json.loads((self.server.root/'assets/toolkit-manifest.json').read_text('utf-8'))
            item=next(t for t in catalog if t['id']==tool)
            if not browser_host.allowed_package(item,name):
                raise ValueError('Select a downloaded software package')
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 8_000_000_000: raise ValueError('Package must be between 1 byte and 8 GB')
            folder.mkdir(parents=True, exist_ok=True)
            if size * 2 + 100_000_000 > shutil.disk_usage(folder).free: raise ValueError('Not enough free space')
            destination = safe_path(self.server.root, (folder / name).relative_to(self.server.root).as_posix())
            if destination.exists(): raise ValueError('A file with that name already exists; it was preserved')
            temporary = folder / ('.import-' + secrets.token_hex(8) + '.partial')
            self.connection.settimeout(60)
            received = 0
            with temporary.open('xb') as output:
                while received < size:
                    chunk = self.rfile.read(min(1024 * 1024, size-received))
                    if not chunk: raise ValueError('Import interrupted')
                    output.write(chunk); received += len(chunk)
                    self.server.state = dict(busy=True, startedAt=started_at, tool=tool, message='Importing ' + name, stage='import', received=received, total=size, file=name)
            with destination.open('xb') as output, temporary.open('rb') as source:
                try: shutil.copyfileobj(source, output)
                except Exception:
                    output.close(); destination.unlink(); raise
            self.server.state = dict(busy=True, startedAt=started_at, tool=tool, message='Scanning imported package…', stage='scan')
            threading.Thread(target=self.server.job, args=('inventory', {'tool': tool}), daemon=True).start()
            handed_off = True
            # The job now owns the lock.
            self.reply(202, self.server.state)
            return
        except Exception as error:
            if not handed_off:
                self.server.state = dict(busy=False, message='Import stopped: ' + str(error), stage='error')
                self.reply(400, {'error': str(error)})
        finally:
            if not handed_off: self.server.lock.release()
            if temporary is not None and temporary.exists(): temporary.unlink()


def tool_folder(root, tool_id):
    catalog = json.loads((root / 'assets/toolkit-manifest.json').read_text('utf-8'))
    tool = next((t for t in catalog if t['id'] == tool_id), None)
    if not tool or not tool.get('localFolder'): raise ValueError('Unknown tool destination')
    return safe_path(root, tool['localFolder'])


def open_app(url):
    """Use the installed browser engine in a dedicated window, without new dependencies."""
    candidates = [shutil.which(n) for n in ('msedge', 'google-chrome', 'chromium', 'chromium-browser')]
    if os.name == 'nt':
        candidates = [str(Path(os.environ.get(key, 'C:/Program Files')) / relative)
            for key in ('PROGRAMFILES(X86)', 'PROGRAMFILES', 'LOCALAPPDATA')
            for relative in ('Microsoft/Edge/Application/msedge.exe', 'Google/Chrome/Application/chrome.exe')] + candidates
    elif sys.platform == 'darwin':
        candidates += ['/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            subprocess.Popen([candidate, '--app=' + url, '--window-size=1280,860'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
    print('Edge or Chromium was not found; opening the default browser instead.', flush=True)
    webbrowser.open(url)

if __name__ == '__main__':
    if '--portable-ai-self-test' in sys.argv:
        answer=offline_assistant.portable_ai.chat(ROOT,[{'role':'user','content':'Reply with just the word READY.'}])
        if 'READY' not in answer.upper():raise RuntimeError('Portable model did not return the expected test response')
        print('Portable AI runtime and local model ready. No chat history was stored.')
        sys.exit(0)
    from launcher_instance import Instance
    import atexit
    instance = Instance(ROOT)
    if not instance.acquire():
        if instance.focus():
            print('Returned to the existing toolkit window.', flush=True)
            sys.exit(0)
        raise RuntimeError('The toolkit is already running but is not responding. Close its launcher before retrying.')
    atexit.register(instance.close)
    server = Server()
    instance.publish(server.origin, server.token)
    url = server.origin + '/' + server.token + '/index.html'
    print('Master IT Toolkit launcher. Keep this terminal open; Ctrl+C stops it.\n' + url, flush=True)
    if '--no-startup-scan' not in sys.argv:
        server.lock.acquire()
        server.state = {'busy':True,'startedAt':time.time(),'message':'Scanning this PC and organizing SSD packages…'}
        threading.Thread(target=server.job,args=('inventory',),daemon=True).start()
    if server.browser.available(): server.browser.open(url)
    else: open_app(url)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        server.browser.stop.set()
        server.server_close()
