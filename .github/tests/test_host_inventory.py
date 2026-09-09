import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
import zipfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]/'MASTER-IT-TOOLKIT'
sys.path.insert(0,str(ROOT))
import host_inventory as host
spec=importlib.util.spec_from_file_location('scanner',ROOT/'60_SCRIPTS/Inventory/update_toolkit_inventory.py')
scanner=importlib.util.module_from_spec(spec);spec.loader.exec_module(scanner)

class SmartScanTests(unittest.TestCase):
    def test_version_architecture_and_no_substring_false_positive(self):
        tools=[dict(id='7zip',name='7-Zip',os=['Windows']),dict(id='notepad',name='Notepad++',os=['Windows'])]
        records=[dict(name='7-Zip 26.01 (x64)',version='26.01'),dict(name='Notepad',version='1'),dict(name='Notepad++ (64-bit x64)',version='8')]
        self.assertEqual(len(host.matches(tools[0],records,'win32')),1)
        self.assertFalse(host.matches(tools[1],records[1:2],'win32'))
        self.assertTrue(host.matches(tools[1],records[2:],'win32'))
        self.assertFalse(host.matches(tools[0],[dict(name='7-Zip helper',version='1')],'win32'))
    def test_host_and_ssd_are_independent_and_errors_are_unknown(self):
        catalog=[dict(id='app',name='Example',os=['Windows'])]
        inventory={'tools':{'app':{'downloaded':False,'ready':False}}}
        data=dict(id='pc-a',platform='win32',programs=[dict(name='Example 2.4 (x64)',version='2.4')],errors=[])
        host.apply(catalog,inventory,data)
        self.assertTrue(inventory['tools']['app']['hostInstalled']);self.assertFalse(inventory['tools']['app']['downloaded'])
        data.update(programs=[],errors=['Unavailable'])
        host.apply(catalog,inventory,data);self.assertIsNone(inventory['tools']['app']['hostInstalled'])
    def test_linux_explicit_package_mapping(self):
        tool=dict(id='obs',name='OBS Studio',os=['Linux'])
        self.assertTrue(host.matches(tool,[dict(name='obs-studio',package='obs-studio',version='1')],'linux'))
        self.assertFalse(host.matches(tool,[dict(name='obs-studio-plugin',package='obs-studio-plugin',version='1')],'linux'))
    def test_smart_archive_and_interrupted_download_classification(self):
        with tempfile.TemporaryDirectory() as temp:
            scanner.ROOT=Path(temp);folder=Path(temp)/'apps';folder.mkdir();(Path(temp)/'assets/js').mkdir(parents=True)
            tool=dict(id='app',name='Example',localFolder='apps',inventoryPatterns=['Tool.exe'],packagePatterns=['tool*.zip','setup*.exe'])
            (Path(temp)/'assets/js/tools-data.js').write_text('window.TOOLKIT_DATA = '+json.dumps([tool])+';')
            with zipfile.ZipFile(folder/'tool.zip','w') as z:z.writestr('Tool.exe',b'fixture')
            partial=folder/'old.partial';partial.write_bytes(b'');os.utime(partial,(time.time()-90000,time.time()-90000))
            record=scanner.scan()['tools']['app']
            self.assertEqual(record['packageState'],'needs-extraction');self.assertEqual(len(record['cleanupReview']),1)
            scanner.organize(scanner.scan());record=scanner.scan()['tools']['app']
            self.assertEqual(record['packageState'],'ready');self.assertFalse(record['needsExtraction'])
            self.assertTrue(partial.exists());self.assertTrue((folder/'tool.zip').exists())
            next((folder/'Ready').rglob('Tool.exe')).unlink()
            incomplete=scanner.scan();self.assertTrue(incomplete['tools']['app']['needsExtraction'])
            self.assertTrue(scanner.organize(incomplete)['errors'])
    def test_uninstaller_program_is_not_a_setup_program(self):
        self.assertFalse(scanner.installer_file(Path('BCUninstaller.exe'),{'id':'bcu'}))
        self.assertTrue(scanner.installer_file(Path('BCUninstaller_6.3_setup.exe'),{'id':'bcu'}))

if __name__=='__main__':unittest.main()
