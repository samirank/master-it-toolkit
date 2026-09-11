"""Find shared source and the matching bundled runtime without fixed drive paths."""
import json
import os
import platform
import sys
from pathlib import Path

SUPPORTED = ('windows-x64', 'linux-x64', 'macos-arm64')


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
    return dict(current=label(), installed=[item for item in SUPPORTED if (root / 'runtimes' / item / 'browser').is_dir()], supported=list(SUPPORTED))
