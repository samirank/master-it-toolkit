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
archive_binary = binary if binary.endswith('.exe') else 'Start-' + binary
executable = root / 'dist' / binary
subprocess.run([str(executable), '--self-test'], check=True)
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
    for folder, directories, files in os.walk(browser_root, followlinks=True):
        directories[:] = [d for d in directories if not d.startswith('.')]
        for name in files:
            file = Path(folder) / name
            target.write(file, 'MASTER-IT-TOOLKIT/runtime-browser/' + file.relative_to(browser_root).as_posix())
    for package in ('playwright','pyee','greenlet','cryptography'):
        distribution = importlib.metadata.distribution(package)
        for file in distribution.files:
            if 'license' in str(file).lower() or str(file).endswith('NOTICE'):
                target.writestr('MASTER-IT-TOOLKIT/runtime-licenses/'+package+'/'+str(file).replace('../',''), distribution.locate_file(file).read_bytes())
    from playwright.sync_api import sync_playwright
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True, channel='chromium')
        page = browser.new_page()
        page.goto('chrome://credits')
        target.writestr('MASTER-IT-TOOLKIT/runtime-licenses/BROWSER-CREDITS.html', page.content())
        browser.close()
    version = '.'.join(map(str, sys.version_info[:3]))
    with urllib.request.urlopen('https://raw.githubusercontent.com/python/cpython/v' + version + '/LICENSE', timeout=30) as response:
        target.writestr('MASTER-IT-TOOLKIT/runtime-licenses/PYTHON-LICENSE.txt', response.read())
    distribution = importlib.metadata.distribution('pyinstaller')
    for file in distribution.files:
        if str(file).endswith('/COPYING.txt') or str(file).endswith('/COPYING'):
            target.writestr('MASTER-IT-TOOLKIT/runtime-licenses/PYINSTALLER-COPYING.txt', distribution.locate_file(file).read_bytes())
with tempfile.TemporaryDirectory() as temporary:
    with zipfile.ZipFile(output) as z:
        z.extractall(temporary)
        for info in z.infolist():
            path = Path(temporary)/info.filename
            if path.is_file() and info.external_attr >> 16 & 0o111: path.chmod(0o755)
    exe = Path(temporary) / archive_binary
    exe.chmod(0o755)
    subprocess.run([str(exe), '--inventory'], check=True, timeout=120)
    subprocess.run([str(exe), '--browser-self-test'], check=True, timeout=120)
print(output)
