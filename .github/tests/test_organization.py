import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('inventory', Path(__file__).resolve().parents[2] / 'MASTER-IT-TOOLKIT/60_SCRIPTS/Inventory/update_toolkit_inventory.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class OrganizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        m.ROOT = Path(self.temp.name)
        (m.ROOT/'apps').mkdir()
        (m.ROOT/'assets/js').mkdir(parents=True)
        (m.ROOT/'assets/js/tools-data.js').write_text('window.TOOLKIT_DATA = '+json.dumps([dict(id='app',localFolder='apps',inventoryPatterns=['tool.exe'],packagePatterns=['tool*.zip'])])+';')
    def tearDown(self): self.temp.cleanup()
    def archive(self, members):
        with zipfile.ZipFile(m.ROOT/'apps/tool.zip','w') as z:
            for name, content in members: z.writestr(name,content)
    def test_extract_refresh_repeat_and_preserve(self):
        self.archive([('portable/tool.exe',b'fixture')])
        self.assertFalse(m.scan()['tools']['app']['ready'])
        self.assertEqual(len(m.organize(m.scan())['extracted']),1)
        self.assertTrue(m.scan()['tools']['app']['ready'])
        self.assertTrue((m.ROOT/'apps/tool.zip').exists())
        self.assertEqual(len(m.organize(m.scan())['skipped']),1)
        self.assertFalse(list(m.ROOT.rglob('.extract-*')))
    def test_reject_unsafe_members(self):
        for name in ['../escape.exe','/absolute.exe','C:/evil.exe','CON.txt','x:stream','folder/../bad','TOOL.exe']:
            self.archive([('tool.exe',b'fixture'),(name,b'bad')])
            self.assertTrue(m.organize(m.scan())['errors'],name)
            self.assertFalse(list(m.ROOT.rglob('.extract-*')))
            self.assertFalse(m.scan()['tools']['app']['ready'])
    def test_nested_archive_not_recursively_extracted(self):
        self.archive([('tool-inner.zip',b'not an archive'),('tool.exe',b'fixture')])
        m.organize(m.scan())
        self.assertFalse(m.organize(m.scan())['errors'])
    def test_partial_staging_not_ready(self):
        p=m.ROOT/'apps/Ready/.extract-interrupted';p.mkdir(parents=True)
        (p/'tool.exe').write_bytes(b'partial')
        self.assertFalse(m.scan()['tools']['app']['ready'])

if __name__ == '__main__': unittest.main()
