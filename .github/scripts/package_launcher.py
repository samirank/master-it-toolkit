import subprocess
import sys
import tempfile
import zipfile
import urllib.request
import importlib.metadata
from pathlib import Path

root = Path(__file__).resolve().parents[2]
binary, label = sys.argv[1:]
executable = root / 'dist' / binary
subprocess.run([str(executable), '--self-test'], check=True)
output = root / ('standalone-' + label + '.zip')
with zipfile.ZipFile(root / 'MASTER-IT-TOOLKIT.zip') as source, zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as target:
    for info in source.infolist():
        if info.filename.startswith('MASTER-IT-TOOLKIT/'): target.writestr(info, source.read(info.filename))
    info = zipfile.ZipInfo(binary)
    info.external_attr = 0o100755 << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    target.writestr(info, executable.read_bytes())
    version = '.'.join(map(str, sys.version_info[:3]))
    with urllib.request.urlopen('https://raw.githubusercontent.com/python/cpython/v' + version + '/LICENSE', timeout=30) as response:
        target.writestr('MASTER-IT-TOOLKIT/runtime-licenses/PYTHON-LICENSE.txt', response.read())
    distribution = importlib.metadata.distribution('pyinstaller')
    for file in distribution.files:
        if str(file).endswith('/COPYING.txt') or str(file).endswith('/COPYING'):
            target.writestr('MASTER-IT-TOOLKIT/runtime-licenses/PYINSTALLER-COPYING.txt', distribution.locate_file(file).read_bytes())
with tempfile.TemporaryDirectory() as temporary:
    with zipfile.ZipFile(output) as z: z.extractall(temporary)
    exe = Path(temporary) / binary
    exe.chmod(0o755)
    subprocess.run([str(exe), '--inventory'], check=True, timeout=120)
print(output)
