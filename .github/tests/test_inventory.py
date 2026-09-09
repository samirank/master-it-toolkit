"""Cross-platform fixture test. No real software is loaded or executed."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

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
    def test_missing_folder_size(self): self.assertEqual(module.scan()['storage']['folders']['90_TEMP'],0)
    def test_unsafe_paths(self):
        for value in ['../outside','/etc/passwd','C:\\Windows','apps/../outside','a.txt:stream']:
            with self.assertRaises(ValueError):module.safe_path(value)
    def test_symlink_skipped(self):
        try:(self.root/'apps'/'link.exe').symlink_to(self.root/'boot/image-test.iso')
        except OSError:self.skipTest('Host does not permit unprivileged symlinks')
        self.assertNotIn(self.root/'apps/link.exe',module.files('apps'))

if __name__=='__main__':unittest.main()
