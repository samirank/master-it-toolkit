"""Cross-platform fixture test. No real software is loaded or executed."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

REPO=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('inventory', REPO/'MASTER-IT-TOOLKIT/60_SCRIPTS/Inventory/update_toolkit_inventory.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='neighbor-circuit-test-')
        self.root=Path(self.temp.name)
        module.ROOT=self.root
        self.write('assets/js/tools-data.js','window.TOOLKIT_DATA = '+json.dumps([
            {'id':'app','localFolder':'apps','localExecutable':'apps/Tool.exe','inventoryPatterns':['tool.exe']},
            {'id':'empty','localFolder':'empty','inventoryPatterns':['*.exe']},
            {'id':'suite','localFolder':'suite','inventoryPatterns':['a.exe','b.exe'],'inventoryMatch':'all'},
            {'id':'host','localFolder':'','inventoryPatterns':[]},
            {'id':'iso','localFolder':'boot','inventoryPatterns':['image*.iso']}
        ])+';')
        self.write('apps/Nested Folder/Tool.exe','MOCK DATA NOT EXECUTABLE')
        self.write('empty/placeholder.exe','')
        self.write('suite/a.exe','MOCK DATA')
        self.write('boot/image-test.iso','MOCK NOT BOOT MEDIA')
    def tearDown(self): self.temp.cleanup()
    def write(self,name,text):
        p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
    def test_recursive_path_and_unknown_version(self):
        r=module.scan()['tools']['app']
        self.assertTrue(r['installed']);self.assertEqual(r['localPath'],'apps/Nested Folder/Tool.exe');self.assertEqual(r['version'],'')
    def test_empty_files_not_installed(self): self.assertFalse(module.scan()['tools']['empty']['installed'])
    def test_all_pattern_requirement(self):
        self.assertFalse(module.scan()['tools']['suite']['installed'])
        self.write('suite/b.exe','MOCK DATA');self.assertTrue(module.scan()['tools']['suite']['installed'])
    def test_wildcard_iso(self): self.assertTrue(module.scan()['tools']['iso']['installed'])
    def test_host_not_installed(self): self.assertFalse(module.scan()['tools']['host']['installed'])
    def test_real_7zip_and_bcu_packages(self):
        catalog=json.loads((REPO/'MASTER-IT-TOOLKIT/assets/toolkit-manifest.json').read_text('utf-8'))
        tools=[t for t in catalog if t['id'] in ('7zip','bcu')]
        self.write('assets/js/tools-data.js','window.TOOLKIT_DATA = '+json.dumps(tools)+';')
        for t in tools:self.write(t['localFolder']+('/7z2603-x64.exe' if t['id']=='7zip' else '/BCUninstaller_5.10.0_portable.zip'),'MOCK PACKAGE')
        result=module.scan()['tools']
        for id in ('7zip','bcu'):
            self.assertTrue(result[id]['downloaded']);self.assertFalse(result[id]['ready'])
        self.assertEqual(result['7zip']['version'],'26.03')
    def test_download_receipt_version(self):
        self.write('apps/unusual-package.zip','PACKAGE')
        self.write('assets/download-receipts.json',json.dumps({'app':[{'path':'apps/unusual-package.zip','size':7,'version':'2.0','savedAt':'2026-09-09'}],'_latest':{'app':'2.1'}}))
        result=module.scan()['tools']['app'];self.assertTrue(result['downloaded']);self.assertEqual(result['version'],'2.0');self.assertEqual(result['latestVersion'],'2.1')
    def test_each_directory_walked_once(self):
        original=module.os.scandir;seen=[]
        def counted(path):seen.append(str(path));return original(path)
        with patch.object(module.os,'scandir',side_effect=counted):module.scan()
        self.assertEqual(len(seen),len(set(seen)))
    def test_missing_folder_size(self): self.assertEqual(module.scan()['storage']['folders']['90_TEMP'],0)
    def test_unsafe_paths(self):
        for value in ['../outside','/etc/passwd','C:\\Windows','apps/../outside','a.txt:stream']:
            with self.assertRaises(ValueError):module.safe_path(value)
    def test_symlink_skipped(self):
        try:(self.root/'apps'/'link.exe').symlink_to(self.root/'boot/image-test.iso')
        except OSError:self.skipTest('Host does not permit unprivileged symlinks')
        self.assertNotIn(self.root/'apps/link.exe',module.files('apps'))

if __name__=='__main__':unittest.main()
