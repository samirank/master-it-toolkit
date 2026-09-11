"""Merge tested native packages; shared files must be identical across builds."""
import hashlib
import shutil
import sys
import zipfile
from pathlib import Path, PurePosixPath

LABELS = ('windows-x64', 'linux-x64', 'macos-arm64')


def digest(source):
    h = hashlib.sha256()
    for block in iter(lambda: source.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()


def assemble(folder):
    output = folder / 'standalone-all-platforms.zip'
    temporary = output.with_suffix('.partial')
    seen = {}
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as target:
            for label in LABELS:
                with zipfile.ZipFile(folder / ('standalone-' + label + '.zip')) as source:
                    for info in source.infolist():
                        name = info.filename
                        if len(name) > 220: raise ValueError('Outer package path too long for SSD preparation on Windows: ' + name)
                        if name.startswith('/') or '\\' in name or ':' in name or '..' in PurePosixPath(name).parts:
                            raise ValueError('Unsafe package path')
                        if info.is_dir(): continue
                        with source.open(info) as src: checksum = digest(src)
                        if name in seen:
                            if seen[name] != checksum: raise ValueError('Platform packages disagree on shared file: ' + name)
                            continue
                        seen[name] = checksum
                        with source.open(info) as src, target.open(info, 'w', force_zip64=True) as dst:
                            shutil.copyfileobj(src, dst, 1024 * 1024)
            required = {'Start-Windows.exe', 'Start-Linux.sh', 'Start-macOS.command', 'MASTER-IT-TOOLKIT/launcher.py'}
            required.update('MASTER-IT-TOOLKIT/runtimes/' + label + '/platform.json' for label in LABELS)
            if not required.issubset(seen): raise ValueError('Incomplete universal bundle')
        temporary.replace(output)
        lines = []
        for path in sorted(folder.glob('*.zip')):
            with path.open('rb') as source: lines.append(digest(source) + '  ' + path.name)
        (folder / 'SHA256SUMS.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    finally:
        temporary.unlink(missing_ok=True)
    return output


if __name__ == '__main__': print(assemble(Path(sys.argv[1])))
