"""Find shared source and the matching bundled runtime without fixed drive paths."""
import atexit
from contextlib import contextmanager
import json
import hashlib
import os
import platform
import secrets
import shutil
import sys
import tempfile
import threading
import zipfile
from pathlib import Path, PurePosixPath

SUPPORTED = ('windows-x64', 'linux-x64', 'macos-arm64')
LOCKS = {}


HOST_CACHE_LOCK = threading.RLock()
HOST_CACHE = None
HOST_USERS = 0


def remove_host_session(folder, base):
    """Delete only a directly owned session, never a link or unrelated folder."""
    if folder.is_symlink() or base.is_symlink(): return False
    resolved = folder.resolve()
    if resolved.parent != base.resolve() or not folder.name.startswith('session-'): return False
    owner = folder / '.owner.json'
    if owner.is_symlink() or not owner.is_file(): return False
    try:
        record = json.loads(owner.read_text('utf-8'))
        if record.get('application') != 'Master-IT-Toolkit-browser-session-v1': return False
        shutil.rmtree(resolved)
        return True
    except (OSError, ValueError): return False


def clean_abandoned_host_sessions(base):
    if not base.is_dir() or base.is_symlink(): return
    for folder in base.glob('session-*'):
        if folder.is_symlink() or not folder.is_dir(): continue
        try:
            owner = folder / '.owner.json'
            if owner.is_symlink(): continue
            record = json.loads(owner.read_text('utf-8'))
            pid = record.get('pid')
            if record.get('application') != 'Master-IT-Toolkit-browser-session-v1' or type(pid) is not int or pid <= 0: continue
            try: os.kill(pid, 0)
            except ProcessLookupError: remove_host_session(folder, base)
            except (PermissionError, OSError): pass  # Unknown ownership: preserve.
        except (OSError, ValueError): continue


def host_session():
    global HOST_CACHE
    with HOST_CACHE_LOCK:
        if HOST_CACHE is None:
            base = Path.home() / 'Library/Caches/Master-IT-Toolkit/browser-sessions'
            base.mkdir(parents=True, exist_ok=True)
            clean_abandoned_host_sessions(base)
            folder = base / ('session-' + secrets.token_hex(16))
            folder.mkdir(mode=0o700)
            (folder / '.owner.json').write_text(json.dumps({'application': 'Master-IT-Toolkit-browser-session-v1', 'pid': os.getpid()}), encoding='utf-8')
            HOST_CACHE = folder
        return HOST_CACHE


def cleanup_host_cache():
    global HOST_CACHE
    with HOST_CACHE_LOCK:
        if HOST_USERS or HOST_CACHE is None: return
        folder = HOST_CACHE
        if remove_host_session(folder, folder.parent):
            HOST_CACHE = None
            # Only remove empty application cache directories.
            for parent in (folder.parent, folder.parent.parent):
                try: parent.rmdir()
                except OSError: break


@contextmanager
def browser_session(root):
    """Keep shared runtime files alive until every browser window has closed."""
    global HOST_USERS
    with HOST_CACHE_LOCK: HOST_USERS += 1
    try: yield browser_path(root)
    finally:
        with HOST_CACHE_LOCK:
            HOST_USERS -= 1
            cleanup_host_cache()


atexit.register(cleanup_host_cache)


def prepare_browser(runtime, browser=None):
    """Only expand this OS's browser; foreign macOS paths stay zipped on Windows."""
    archive = runtime / 'browser.zip'
    browser = Path(browser) if browser is not None else runtime / 'browser'
    destination = browser.parent
    if not archive.is_file(): return
    destination.mkdir(parents=True, exist_ok=True)
    with LOCKS.setdefault(str(browser.resolve()), threading.Lock()):
        expected = json.loads((runtime / 'platform.json').read_text('utf-8')).get('browserArchiveSha256', '')
        if len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected):
            raise ValueError('Invalid bundled browser checksum')
        marker = browser / '.toolkit-runtime-ready'
        if marker.is_file() and marker.read_text('utf-8') == expected: return
        digest = hashlib.sha256()
        with archive.open('rb') as source:
            for block in iter(lambda: source.read(1024 * 1024), b''): digest.update(block)
        if digest.hexdigest() != expected: raise ValueError('Bundled browser checksum mismatch; reinstall this platform runtime.')
        print('Preparing the bundled browser from this SSD (no download needed)...', flush=True)
        with zipfile.ZipFile(archive) as package:
            members = package.infolist()
            if len(members) > 50000 or len({i.filename for i in members}) != len(members): raise ValueError('Invalid browser archive')
            total = sum(i.file_size for i in members)
            if total > 8 * 1024**3 or shutil.disk_usage(destination).free < total + 128 * 1024**2: raise ValueError('Not enough free space to prepare the bundled browser')
            with tempfile.TemporaryDirectory(prefix='.browser-', dir=destination) as temporary:
                stage = Path(temporary)
                for index, info in enumerate(members):
                    name = info.filename
                    if name.startswith('/') or '\\' in name or ':' in name or '..' in PurePosixPath(name).parts or info.external_attr >> 28 == 0xA:
                        raise ValueError('Unsafe browser archive path')
                    target = stage / name
                    target.resolve().relative_to(stage.resolve())
                    if info.is_dir(): target.mkdir(parents=True, exist_ok=True); continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with package.open(info) as source, target.open('xb') as output:
                        shutil.copyfileobj(source, output, 1024 * 1024); output.flush(); os.fsync(output.fileno())
                    if sys.platform != 'win32': target.chmod(0o644 | ((info.external_attr >> 16) & 0o111))
                    if index % 100 == 0: print('Preparing browser: ' + str(index * 100 // max(1, len(members))) + '%', flush=True)
                (stage / '.toolkit-runtime-ready').write_text(expected, encoding='utf-8')
                previous = destination / ('.previous-browser-' + secrets.token_hex(8))
                if browser.exists(): browser.rename(previous)
                try: stage.rename(browser)
                except Exception:
                    if previous.exists() and not browser.exists(): previous.rename(browser)
                    raise
                # Previous browser versions are retained rather than deleting files
                # that another still-running launcher could be using.
        print('Bundled browser ready.', flush=True)


def label():
    system = {'win32': 'windows', 'darwin': 'macos'}.get(sys.platform, 'linux' if sys.platform.startswith('linux') else sys.platform)
    arch = platform.machine().lower()
    arch = {'amd64': 'x64', 'x86_64': 'x64', 'aarch64': 'arm64'}.get(arch, arch)
    return system + '-' + arch


def toolkit_root(executable):
    folder = Path(executable).resolve().parent
    for candidate in (folder, folder / 'MASTER-IT-TOOLKIT', *list(folder.parents)[:3]):
        if (candidate / 'launcher.py').is_file() and (candidate / 'assets/toolkit-manifest.json').is_file():
            return candidate
    raise RuntimeError('Keep the launchers, runtime folders and MASTER-IT-TOOLKIT folder together.')


def browser_path(root):
    modern = root / 'runtimes' / label() / 'browser'
    runtime = modern.parent
    manifest = runtime / 'platform.json'
    if sys.platform == 'darwin' and (runtime / 'browser.zip').is_file():
        # Never expand macOS app bundles onto the shared SSD. Session files
        # are removed after browser use and rebuilt entirely offline.
        checksum = json.loads(manifest.read_text('utf-8')).get('browserArchiveSha256', '')
        if len(checksum) != 64 or any(c not in '0123456789abcdef' for c in checksum):
            raise ValueError('Invalid bundled browser checksum')
        modern = host_session() / checksum[:16] / 'browser'
    prepare_browser(runtime, modern)
    # Windows ZIP extraction can lose Unix executable bits. Restore only the
    # package's explicitly listed browser files when first opened on Unix.
    if modern.is_dir() and manifest.is_file() and sys.platform != 'win32':
        entries = json.loads(manifest.read_text('utf-8')).get('executables', [])
        if not isinstance(entries, list) or len(entries) > 10000:
            raise ValueError('Invalid runtime executable list')
        for name in entries:
            if not isinstance(name, str) or not name.startswith('browser/') or '\\' in name or ':' in name or '..' in Path(name).parts:
                raise ValueError('Invalid runtime executable path')
            path = modern / name[len('browser/'):]
            path.resolve().relative_to(modern.resolve())
            if path.is_file() and not os.access(path, os.X_OK):
                path.chmod(path.stat().st_mode | 0o100)
    return modern if modern.is_dir() else root / 'runtime-browser'


def available(root):
    return dict(current=label(), installed=[item for item in SUPPORTED if (root / 'runtimes' / item / 'browser').is_dir() or (root / 'runtimes' / item / 'browser.zip').is_file()], supported=list(SUPPORTED))
