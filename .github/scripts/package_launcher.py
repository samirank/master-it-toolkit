import subprocess
import sys
import tempfile
import zipfile
import urllib.request
import importlib.metadata
import os
from pathlib import Path

root = Path(__file__).resolve().parents[2]
binary, label = sys.argv[1:]
runtime_prefix = 'MASTER-IT-TOOLKIT/runtimes/' + label + '/'
archive_binary = 'Start-Windows.exe' if label == 'windows-x64' else runtime_prefix + binary
executable = root / 'dist' / binary
subprocess.run([str(executable), '--self-test'], check=True)
if label in ('windows-x64','macos-arm64'):
    subprocess.run([str(executable), '--credential-self-test'], check=True, timeout=30)
output = root / ('standalone-' + label + '.zip')
with zipfile.ZipFile(root / 'MASTER-IT-TOOLKIT.zip') as source, zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as target:
    for info in source.infolist():
        if info.filename.startswith('MASTER-IT-TOOLKIT/'): target.writestr(info, source.read(info.filename))
    info = zipfile.ZipInfo(archive_binary)
    info.external_attr = 0o100755 << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    target.writestr(info, executable.read_bytes())
    browser_root = root / 'MASTER-IT-TOOLKIT/runtime-browser'
    if not browser_root.is_dir(): raise RuntimeError('Bundled Chromium is missing')
    executables = []
    browser_archive = root / 'dist' / ('browser-' + label + '.zip')
    with zipfile.ZipFile(browser_archive, 'w', zipfile.ZIP_DEFLATED) as browser_zip:
        for folder, directories, files in os.walk(browser_root, followlinks=True):
            directories[:] = [d for d in directories if not d.startswith('.')]
            for name in files:
                file = Path(folder) / name
                browser_zip.write(file, file.relative_to(browser_root).as_posix())
                if file.stat().st_mode & 0o111: executables.append('browser/' + file.relative_to(browser_root).as_posix())
    browser_digest = __import__('hashlib').sha256()
    with browser_archive.open('rb') as src:
        for block in iter(lambda: src.read(1024 * 1024), b''): browser_digest.update(block)
    target.write(browser_archive, runtime_prefix + 'browser.zip', compress_type=zipfile.ZIP_STORED)
    for package in ('playwright','pyee','greenlet','cryptography','keyring','jaraco.classes','jaraco.context','jaraco.functools','more-itertools','importlib_metadata','zipp','SecretStorage','jeepney','pywin32-ctypes','cffi','pycparser'):
        try: distribution = importlib.metadata.distribution(package)
        except importlib.metadata.PackageNotFoundError: continue
        for file in distribution.files:
            if 'license' in str(file).lower() or str(file).endswith('NOTICE'):
                target.writestr(runtime_prefix + 'licenses/'+package+'/'+str(file).replace('../',''), distribution.locate_file(file).read_bytes())
    from playwright.sync_api import sync_playwright
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True, channel='chromium')
        page = browser.new_page()
        page.goto('chrome://credits')
        target.writestr(runtime_prefix + 'licenses/BROWSER-CREDITS.html', page.content())
        browser.close()
    version = '.'.join(map(str, sys.version_info[:3]))
    with urllib.request.urlopen('https://raw.githubusercontent.com/python/cpython/v' + version + '/LICENSE', timeout=30) as response:
        target.writestr(runtime_prefix + 'licenses/PYTHON-LICENSE.txt', response.read())
    distribution = importlib.metadata.distribution('pyinstaller')
    for file in distribution.files:
        if str(file).endswith('/COPYING.txt') or str(file).endswith('/COPYING'):
            target.writestr(runtime_prefix + 'licenses/PYINSTALLER-COPYING.txt', distribution.locate_file(file).read_bytes())
    if label != 'windows-x64':
        starter = 'Start-Linux.sh' if label == 'linux-x64' else 'Start-macOS.command'
        expected = 'Linux:x86_64' if label == 'linux-x64' else 'Darwin:arm64'
        script = '#!/bin/sh\nset -eu\ncd -- "$(dirname -- "$0")"\n'
        script += 'if [ "$(uname -s):$(uname -m)" != "' + expected + '" ]; then echo "This launcher requires ' + expected + '."; exit 1; fi\n'
        script += '[ -x "./' + archive_binary + '" ] || chmod u+x "./' + archive_binary + '"\n'
        script += 'exec "./' + archive_binary + '" "$@"\n'
        info = zipfile.ZipInfo(starter); info.external_attr = 0o100755 << 16
        target.writestr(info, script)
    target.writestr(runtime_prefix + 'platform.json', __import__('json').dumps({'platform': label, 'executable': archive_binary, 'executables': executables, 'browserArchiveSha256': browser_digest.hexdigest()}))
# Runtime-only additions never contain the shared database, inventory or source.
with zipfile.ZipFile(output) as source, zipfile.ZipFile(root / ('runtime-' + label + '.zip'), 'w', zipfile.ZIP_DEFLATED) as target:
    for info in source.infolist():
        if info.filename.startswith(runtime_prefix) or '/' not in info.filename:
            with source.open(info) as src, target.open(info, 'w') as dst:
                __import__('shutil').copyfileobj(src, dst)
with tempfile.TemporaryDirectory() as temporary:
    with zipfile.ZipFile(output) as z:
        z.extractall(temporary)
        for info in z.infolist():
            path = Path(temporary)/info.filename
            if path.is_file() and info.external_attr >> 16 & 0o111: path.chmod(0o755)
    exe = Path(temporary) / archive_binary
    exe.chmod(0o755)
    subprocess.run([str(exe), '--inventory'], check=True, timeout=120)
    subprocess.run([str(exe), '--browser-self-test'], check=True, timeout=300)
    subprocess.run([str(exe), '--browser-self-test'], check=True, timeout=120)
print(output)
