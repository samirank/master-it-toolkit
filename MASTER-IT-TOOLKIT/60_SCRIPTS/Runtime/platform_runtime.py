"""Find shared source and the matching bundled runtime without fixed drive paths."""
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


def prepare_browser(runtime):
    """Only expand this OS's browser; foreign macOS paths stay zipped on Windows."""
    archive = runtime / 'browser.zip'
    browser = runtime / 'browser'
    if not archive.is_file(): return
    with LOCKS.setdefault(str(runtime.resolve()), threading.Lock()):
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
            if total > 8 * 1024**3 or shutil.disk_usage(runtime).free < total + 128 * 1024**2: raise ValueError('Not enough free space to prepare the bundled browser')
            with tempfile.TemporaryDirectory(prefix='.browser-', dir=runtime) as temporary:
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
                previous = runtime / ('.previous-browser-' + secrets.token_hex(8))
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
    prepare_browser(modern.parent)
    manifest = modern.parent / 'platform.json'
    # Windows ZIP extraction can lose Unix executable bits. Restore only the
    # package's explicitly listed browser files when first opened on Unix.
    if modern.is_dir() and manifest.is_file() and sys.platform != 'win32':
        entries = json.loads(manifest.read_text('utf-8')).get('executables', [])
        if not isinstance(entries, list) or len(entries) > 10000:
            raise ValueError('Invalid runtime executable list')
        for name in entries:
            if not isinstance(name, str) or not name.startswith('browser/') or '\\' in name or ':' in name or '..' in Path(name).parts:
                raise ValueError('Invalid runtime executable path')
            path = modern.parent / name
            path.resolve().relative_to(modern.resolve())
            if path.is_file() and not os.access(path, os.X_OK):
                path.chmod(path.stat().st_mode | 0o100)
    return modern if modern.is_dir() else root / 'runtime-browser'


def available(root):
    return dict(current=label(), installed=[item for item in SUPPORTED if (root / 'runtimes' / item / 'browser').is_dir() or (root / 'runtimes' / item / 'browser.zip').is_file()], supported=list(SUPPORTED))
