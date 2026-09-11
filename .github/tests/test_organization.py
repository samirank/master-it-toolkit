import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import tarfile,io,gzip,bz2,lzma
from unittest.mock import patch

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
    def use_packages(self,patterns):
        (m.ROOT/'assets/js/tools-data.js').write_text('window.TOOLKIT_DATA = '+json.dumps([dict(id='app',localFolder='apps',inventoryPatterns=['tool.exe'],packagePatterns=patterns)])+';')
    def test_tar_variants_and_internal_links(self):
        self.use_packages(['tool*.tar*','tool*.tgz'])
        for suffix,mode in [('.tar','w'),('.tar.gz','w:gz'),('.tar.bz2','w:bz2'),('.tar.xz','w:xz')]:
            archive=m.ROOT/('apps/tool'+suffix)
            with tarfile.open(archive,mode) as t:
                member=tarfile.TarInfo('./bin/tool.exe');member.size=7;member.mode=0o755;t.addfile(member,io.BytesIO(b'fixture'))
                link=tarfile.TarInfo('bin/alias.exe');link.type=tarfile.SYMTYPE;link.linkname='tool.exe';t.addfile(link)
            result=m.organize(m.scan());self.assertFalse(result['errors']);self.assertIn(archive.relative_to(m.ROOT).as_posix(),result['extracted'])
            target,_=m.archive_target(archive);self.assertEqual((target/'bin/alias.exe').read_bytes(),b'fixture');self.assertFalse((target/'bin/alias.exe').is_symlink())
            self.assertTrue(m.extracted(archive));self.assertTrue(archive.exists())
        self.assertTrue(m.scan()['tools']['app']['ready'])
    def test_single_file_compression_and_expansion_limit(self):
        self.use_packages(['tool.exe.*'])
        for suffix,compress in [('.gz',gzip.compress),('.bz2',bz2.compress),('.xz',lzma.compress)]:
            archive=m.ROOT/('apps/tool.exe'+suffix);archive.write_bytes(compress(b'fixture'))
            result=m.organize(m.scan());self.assertFalse(result['errors']);target,_=m.archive_target(archive)
            self.assertEqual((target/'tool.exe').read_bytes(),b'fixture');self.assertTrue(m.extracted(archive))
        archive=m.ROOT/'apps/tool.exe.oversize.gz';archive.write_bytes(gzip.compress(b'x'*100))
        with patch.object(m,'MAX_BYTES',10):self.assertTrue(m.organize(m.scan())['errors'])
        self.assertFalse(list(m.ROOT.rglob('.extract-*')))
    def test_tar_escaping_links_rejected(self):
        self.use_packages(['tool*.tar'])
        for target in ['../../outside','/etc/passwd','C:/outside','missing']:
            with tarfile.open(m.ROOT/'apps/tool.tar','w') as t:
                member=tarfile.TarInfo('tool.exe');member.type=tarfile.SYMTYPE;member.linkname=target;t.addfile(member)
            self.assertTrue(m.organize(m.scan())['errors']);self.assertFalse(list(m.ROOT.rglob('.extract-*')))

if __name__ == '__main__': unittest.main()
