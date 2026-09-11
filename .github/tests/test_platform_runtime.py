import importlib.util
import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'MASTER-IT-TOOLKIT'))
sys.path.insert(0, str(ROOT / 'MASTER-IT-TOOLKIT/60_SCRIPTS/Runtime'))
import platform_runtime as p
spec = importlib.util.spec_from_file_location('assemble_universal', ROOT / '.github/scripts/assemble_universal.py')
assemble = importlib.util.module_from_spec(spec); spec.loader.exec_module(assemble)


class PlatformTests(unittest.TestCase):
    def test_browser_preparation_is_offline_cached_and_platform_specific(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(p,'label',return_value='windows-x64'):
            root=Path(tmp);runtime=root/'runtimes/windows-x64';runtime.mkdir(parents=True)
            archive=runtime/'browser.zip'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('chromium-fixture/chrome',b'browser')
            checksum=hashlib.sha256(archive.read_bytes()).hexdigest()
            (runtime/'platform.json').write_text(json.dumps({'browserArchiveSha256':checksum}))
            foreign=root/'runtimes/macos-arm64';foreign.mkdir();(foreign/'browser.zip').write_bytes(b'foreign compressed runtime')
            self.assertEqual(set(p.available(root)['installed']),{'windows-x64','macos-arm64'})
            browser=p.browser_path(root);self.assertEqual((browser/'chromium-fixture/chrome').read_bytes(),b'browser')
            self.assertFalse((foreign/'browser').exists())
            with patch.object(p.zipfile,'ZipFile',side_effect=AssertionError('Cache should be reused')):self.assertEqual(p.browser_path(root),browser)
            self.assertFalse(list(runtime.glob('.browser-*')))

    def test_damaged_or_unsafe_browser_archive_preserves_previous_browser(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime=Path(tmp);browser=runtime/'browser';browser.mkdir();(browser/'old').write_bytes(b'preserve')
            archive=runtime/'browser.zip'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('../escape',b'bad')
            manifest=runtime/'platform.json';manifest.write_text(json.dumps({'browserArchiveSha256':'0'*64}))
            with self.assertRaisesRegex(ValueError,'checksum mismatch'):p.prepare_browser(runtime)
            manifest.write_text(json.dumps({'browserArchiveSha256':hashlib.sha256(archive.read_bytes()).hexdigest()}))
            with self.assertRaisesRegex(ValueError,'Unsafe'):p.prepare_browser(runtime)
            self.assertEqual((browser/'old').read_bytes(),b'preserve');self.assertFalse((runtime.parent/'escape').exists())
            self.assertFalse(list(runtime.glob('.browser-*')))

    def test_unix_permissions_and_escaping_runtime_paths(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(p, 'label', return_value='linux-x64'), patch.object(p.sys, 'platform', 'linux'):
            root = Path(tmp); runtime = root / 'runtimes/linux-x64'
            browser = runtime / 'browser'; browser.mkdir(parents=True)
            binary = browser / 'chrome'; binary.write_bytes(b'fixture'); binary.chmod(0o600)
            manifest = runtime / 'platform.json'
            manifest.write_text(json.dumps({'executables': ['browser/chrome']}))
            p.browser_path(root)
            if __import__('os').name != 'nt': self.assertTrue(binary.stat().st_mode & 0o100)
            manifest.write_text(json.dumps({'executables': ['browser/../../outside']}))
            with self.assertRaises(ValueError): p.browser_path(root)

    def test_paths_follow_shared_root_and_platform(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'MASTER-IT-TOOLKIT'
            (root / 'assets').mkdir(parents=True)
            (root / 'assets/toolkit-manifest.json').write_text('[]')
            (root / 'launcher.py').touch()
            nested = root / 'runtimes/linux-x64/Master-IT-Toolkit'
            nested.parent.mkdir(parents=True)
            (nested.parent / 'browser').mkdir()
            self.assertEqual(p.toolkit_root(nested), root.resolve())
            self.assertEqual(p.toolkit_root(Path(tmp) / 'Start-Windows.exe'), root.resolve())
            with patch.object(p, 'label', return_value='linux-x64'):
                self.assertEqual(p.browser_path(root), nested.parent / 'browser')
                self.assertEqual(p.available(root)['installed'], ['linux-x64'])
            with patch.object(p, 'label', return_value='macos-arm64'):
                self.assertEqual(p.browser_path(root), root / 'runtime-browser')

    def packages(self, root, different=False):
        for index, label in enumerate(assemble.LABELS):
            with zipfile.ZipFile(root / ('standalone-' + label + '.zip'), 'w') as z:
                z.writestr('MASTER-IT-TOOLKIT/launcher.py', 'shared' + (str(index) if different else ''))
                z.writestr(['Start-Windows.exe', 'Start-Linux.sh', 'Start-macOS.command'][index], 'launcher')
                info = zipfile.ZipInfo('MASTER-IT-TOOLKIT/runtimes/' + label + '/platform.json')
                info.external_attr = 0o100755 << 16
                z.writestr(info, json.dumps({'platform': label}))

    def test_universal_merge_keeps_all_runtimes_and_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.packages(root)
            with zipfile.ZipFile(assemble.assemble(root)) as z:
                self.assertEqual(z.namelist().count('MASTER-IT-TOOLKIT/launcher.py'), 1)
                self.assertEqual(len(z.namelist()), 7)
                self.assertTrue(z.getinfo('MASTER-IT-TOOLKIT/runtimes/linux-x64/platform.json').external_attr >> 16 & 0o111)
            self.assertIn('standalone-all-platforms.zip', (root / 'SHA256SUMS.txt').read_text())

    def test_conflicting_sources_do_not_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.packages(root, True)
            with self.assertRaises(ValueError): assemble.assemble(root)
            self.assertFalse((root / 'standalone-all-platforms.zip').exists())
            self.assertFalse(list(root.glob('*.partial')))

if __name__ == '__main__': unittest.main()
