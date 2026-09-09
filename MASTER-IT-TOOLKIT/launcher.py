"""Optional loopback launcher. Python 3.9+, standard library only."""
import hashlib
import io
import json
import mimetypes
import os
from pathlib import Path, PurePosixPath
import secrets
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
sys.path.insert(0, str(ROOT))
import tool_downloads
REPO = 'samirank/master-it-toolkit'
MANIFEST = 'assets/distribution-files.json'
SCRIPTS = {
    'check-updates': ('Check downloaded tool updates', 'tool_downloads.py', 'all'),
    'inventory': ('Scan local inventory', '60_SCRIPTS/Inventory/update_toolkit_inventory.py', 'all'),
    'pc': ('PC diagnostics', '60_SCRIPTS/Diagnostics/Get-PCDiagnostics.ps1', 'windows'),
    'network': ('Network diagnostics', '60_SCRIPTS/Network/Get-NetworkDiagnostics.ps1', 'windows'),
    'repair': ('Repair Windows system files', '60_SCRIPTS/Windows-Repair/Repair-WindowsFiles.ps1', 'windows'),
    'metadata': ('Refresh publisher metadata', '60_SCRIPTS/Inventory/Update-ToolkitMetadata.ps1', 'windows'),
    'downloads': ('Download reviewed missing tools', '60_SCRIPTS/Inventory/Download-MissingTools.ps1', 'windows'),
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
    if name == '70_DOCUMENTATION/Service-Notes/README.txt': return True
    if name == '10_WINDOWS_TOOLBOX/06_Account-OOBE/Unattended/autounattend.xml': return True
    if name in ('index.html', 'README.txt', 'START-HERE.txt', 'LICENSE.txt', 'launcher.py', 'tool_downloads.py', 'Start-Toolkit.cmd', 'Start-Toolkit.command'):
        return True
    if name.startswith('assets/'):
        return name not in (MANIFEST, 'assets/js/local-inventory.js', 'assets/download-receipts.json') and Path(name).suffix in ('.js', '.css', '.json', '.png', '.svg')
    if name.startswith(('60_SCRIPTS/', '70_DOCUMENTATION/')):
        return '/Service-Notes/' not in name and Path(name).suffix in ('.ps1', '.py', '.html', '.txt')
    return name.endswith('/PLACE-FILES-HERE.txt') or name == '90_TEMP/README.txt'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def install_archive(blob, root=ROOT):
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
    if not changes: return 'Already up to date.'
    changes[MANIFEST] = ((root / MANIFEST).read_bytes(), manifest_bytes)
    backup = safe_path(root, '.toolkit-backups/' + time.strftime('%Y%m%d-%H%M%S') + '-' + secrets.token_hex(3))
    backup.mkdir(parents=True)
    for name, (before, after) in changes.items():
        if before is not None:
            p = backup / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(before)
    (backup / 'changes.json').write_text(json.dumps({n: b is not None for n, (b, a) in changes.items()}), encoding='utf-8')
    applied = []
    try:
        for name, (before, after) in changes.items():
            p = safe_path(root, name)
            applied.append(name)
            if after is None:
                if p.exists(): p.unlink()
            else:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(after)
    except Exception:
        for name in reversed(applied):
            p = safe_path(root, name)
            before = changes[name][0]
            if before is None:
                if p.exists(): p.unlink()
            else: p.write_bytes(before)
        raise
    return 'Updated toolkit files. Backup: ' + str(backup) + '. Close and restart the launcher to load the new version.'

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
    def __init__(self, root=ROOT, port=8765):
        self.root = root
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.Lock()
        self.state = {'busy': False, 'message': 'Ready.'}
        super().__init__(('127.0.0.1', port), Handler)
        self.origin = 'http://127.0.0.1:' + str(self.server_port)
    def job(self, action, body=None):
        context = {'tool': (body or {}).get('tool')}
        try:
            if action == 'download':
                message = tool_downloads.save_selected(self.root, body['tool'], body['assets'], safe_path,
                    lambda progress: setattr(self, 'state', dict(context, busy=True, **progress)))
                self.state = dict(context, busy=True, message='Scanning and organizing saved packages…', stage='scan')
                message += '\n' + run_script('inventory')
            else: message = update() if action == 'update' else run_script(action)
            self.state = dict(context, busy=False, message=message, stage='complete')
        except Exception as error:
            self.state = dict(context, busy=False, message='Stopped: ' + str(error), stage='error')
        finally: self.lock.release()

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
        if route is None: return self.reply(403, {'error': 'Open the URL printed by your launcher.'})
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
                return self.reply(200, tool_downloads.options(self.server.root, query.get('tool', [''])[0]))
            except Exception as error: return self.reply(400, {'error': str(error)})
        if route == 'api/status':
            return self.reply(200, dict(self.server.state, scripts=[{'id': key, 'name': label, 'enabled': platform == 'all' or os.name == 'nt', 'path': path} for key, (label, path, platform) in SCRIPTS.items()]))
        if route == 'api/inventory':
            try:
                text=(self.server.root/'assets/js/local-inventory.js').read_text('utf-8-sig')
                return self.reply(200,json.loads(text.split('window.LOCAL_INVENTORY =',1)[1].strip().rstrip(';')))
            except (OSError,ValueError,IndexError): return self.reply(200,{'tools':{}})
        try:
            route = route or 'index.html'
            if route not in ('index.html', 'README.txt', 'START-HERE.txt', 'LICENSE.txt') and not route.startswith(('assets/', '70_DOCUMENTATION/')): raise ValueError()
            if '/Service-Notes/' in route: raise ValueError()
            p = safe_path(self.server.root, route)
            if not p.is_file(): raise ValueError()
            data = p.read_bytes()
            if route == 'index.html':
                config = '<script>window.TOOLKIT_LAUNCHER=true;window.TOOLKIT_LOCAL_BASE=' + json.dumps((self.server.root / 'index.html').as_uri()) + ';</script>'
                data = data.replace(b'</head>', config.encode() + b'<script defer src="assets/js/launcher-client.js"></script></head>')
            return self.reply(200, data, mimetypes.guess_type(route)[0] or 'text/plain')
        except (ValueError, OSError): return self.reply(404, {'error': 'Unavailable'})
    def do_POST(self):
        if self.route() != 'api/action' or self.headers.get('Origin') != self.server.origin:
            return self.reply(403, {'error': 'Invalid local session'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 1024: raise ValueError()
            body = json.loads(self.rfile.read(size))
            action = body['action']
            if body.get('confirmed') is not True or action not in (*SCRIPTS, 'update', 'download'): raise ValueError()
            if action == 'download':
                if not isinstance(body.get('tool'), str) or not isinstance(body.get('assets'), list) or not 1 <= len(body['assets']) <= 50 or any(not isinstance(a, str) for a in body['assets']): raise ValueError()
        except (ValueError, KeyError, TypeError): return self.reply(400, {'error': 'Invalid action'})
        if not self.server.lock.acquire(False): return self.reply(409, {'error': 'Another action is still running. Close its script terminal first.'})
        self.server.state = {'busy': True, 'tool': body.get('tool'), 'message': 'Working: ' + action + '. Review any script terminal that opens.'}
        threading.Thread(target=self.server.job, args=(action, body), daemon=True).start()
        self.reply(202, self.server.state)

    def do_PUT(self):
        if self.route() != 'api/import' or self.headers.get('Origin') != self.server.origin:
            return self.reply(403, {'error': 'Invalid local session'})
        if not self.server.lock.acquire(False): return self.reply(409, {'error': 'Another action is running'})
        temporary = None
        handed_off = False
        try:
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            tool = query.get('tool', [''])[0]; name = query.get('name', [''])[0]
            folder = tool_folder(self.server.root, tool)
            if not name or Path(name).name != name or '/' in name or '\\' in name or ':' in name or name.startswith('.'):
                raise ValueError('Invalid package filename')
            if Path(name).suffix.lower() not in ('.exe', '.msi', '.msix', '.zip', '.7z', '.gz', '.xz', '.bz2', '.dmg', '.pkg', '.deb', '.rpm', '.appimage', '.iso'):
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
                    self.server.state = dict(busy=True, tool=tool, message='Importing ' + name, stage='import', received=received, total=size, file=name)
            with destination.open('xb') as output, temporary.open('rb') as source:
                try: shutil.copyfileobj(source, output)
                except Exception:
                    output.close(); destination.unlink(); raise
            self.server.state = dict(busy=True, tool=tool, message='Scanning imported package…', stage='scan')
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
    server = Server()
    url = server.origin + '/' + server.token + '/index.html'
    print('Master IT Toolkit launcher. Keep this terminal open; Ctrl+C stops it.\n' + url, flush=True)
    open_app(url)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
