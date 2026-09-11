import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[2] / 'MASTER-IT-TOOLKIT'
sys.path.insert(0, str(ROOT))
import launcher
import portable_tools as portable


class PortableTests(unittest.TestCase):
    def test_shutup_versioned_download_scans_and_offers_run_without_extraction(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('shutup_scanner',ROOT/'60_SCRIPTS/Inventory/update_toolkit_inventory.py')
        scanner=importlib.util.module_from_spec(spec);spec.loader.exec_module(scanner);scanner.ROOT=self.root
        tool=next(t for t in json.loads((ROOT/'assets/toolkit-manifest.json').read_text('utf-8')) if t['id']=='shutup')
        tool['localFolder']='apps'
        (self.root/'assets/toolkit-manifest.json').write_text(json.dumps([tool]))
        (self.root/'assets/js/tools-data.js').write_text('window.TOOLKIT_DATA = '+json.dumps([tool])+';')
        names=['OOSU10.exe','ooshutup10_3.5.1130_x64.exe','ooshutup10_4.0.100_x86.exe','ooshutup10_4.0.100_arm64.exe']
        for name in names:(self.root/'apps'/name).write_bytes(b'Harmless fixture; never executed')
        inventory=scanner.scan();record=inventory['tools']['shutup']
        self.assertTrue(record['downloaded']);self.assertTrue(record['ready']);self.assertFalse(record['needsExtraction'])
        (self.root/'assets/js/local-inventory.js').write_text('window.LOCAL_INVENTORY = '+json.dumps(inventory)+';')
        with patch.object(portable,'os',SimpleNamespace(name='nt')):
            choices=portable.options(self.root,'shutup',launcher.safe_path)
        self.assertEqual({f['name'] for f in choices['files']},set(names));self.assertFalse(choices['reason'])

    def test_winutil_script_launch_is_explicit_and_has_fixed_arguments(self):
        self.tool.update(id='winutil',inventoryPatterns=['winutil*.ps1'])
        (self.root/'assets/toolkit-manifest.json').write_text(json.dumps([self.tool]))
        (self.root/'apps/winutil.ps1').write_text('# Test fixture, never executed')
        (self.root/'assets/js/local-inventory.js').write_text('window.LOCAL_INVENTORY = '+json.dumps({'tools':{'winutil':{'files':[{'path':'apps/winutil.ps1'},{'path':'apps/Sample.exe'}]}}})+';')
        process=Mock();process.wait.return_value=0
        with patch.object(portable,'os',SimpleNamespace(name='nt')),patch.object(portable.shutil,'which',return_value='powershell.exe'),patch.object(portable.subprocess,'Popen',return_value=process) as popen:
            data=portable.options(self.root,'winutil',launcher.safe_path)
            self.assertTrue(data['confirmationRequired']);self.assertEqual(len(data['files']),1)
            portable.launch(self.root,'winutil','apps/winutil.ps1',launcher.safe_path,lambda _:None)
            self.assertEqual(popen.call_args.args[0],['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(self.root/'apps/winutil.ps1')])
            self.assertFalse(popen.call_args.kwargs['shell'])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root/'assets/js').mkdir(parents=True)
        (self.root/'apps').mkdir()
        self.tool = dict(id='sample', name='Sample', kind='Portable', os=['Windows'], localFolder='apps', inventoryPatterns=['Sample*.exe'])
        (self.root/'assets/toolkit-manifest.json').write_text(json.dumps([self.tool]))
        for name in ['Sample.exe','Sample-setup.exe','Other.exe']:
            (self.root/'apps'/name).write_bytes(b'Non-executable test fixture')
        (self.root/'outside.exe').write_bytes(b'Non-executable test fixture')
        self.inventory(['apps/Sample.exe','apps/Sample-setup.exe','apps/Other.exe','outside.exe','../outside.exe'])

    def inventory(self, files):
        (self.root/'assets/js/local-inventory.js').write_text('window.LOCAL_INVENTORY = '+json.dumps({'tools':{'sample':{'files':[{'path':p} for p in files]}}})+';')

    def tearDown(self): self.temp.cleanup()

    def test_catalog_and_folder_confinement(self):
        # Patch just the module OS facade, never pathlib's host platform.
        with patch.object(portable, 'os', SimpleNamespace(name='nt')):
            data = portable.options(self.root, 'sample', launcher.safe_path)
            self.assertEqual([f['path'] for f in data['files']], ['apps/Sample.exe'])
            with self.assertRaises(ValueError): portable.launch(self.root,'sample','outside.exe',launcher.safe_path,lambda _:None)
            (self.root/'apps/Sample.exe').unlink()
            self.assertFalse(portable.options(self.root,'sample',launcher.safe_path)['files'])

    def test_launch_has_no_shell_or_injected_arguments(self):
        process=Mock();process.wait.return_value=0
        with patch.object(portable,'options',return_value={'files':[{'path':'apps/Sample.exe'}]}), patch.object(portable.subprocess,'Popen',return_value=process) as popen:
            result=portable.launch(self.root,'sample','apps/Sample.exe',launcher.safe_path,lambda _:None)
            self.assertIn('does not certify',result)
            self.assertEqual(popen.call_args.args,([str(self.root/'apps/Sample.exe')],))
            self.assertIs(popen.call_args.kwargs['shell'],False)

    def test_nonzero_exit_is_not_success(self):
        process=Mock();process.wait.return_value=5
        with patch.object(portable,'options',return_value={'files':[{'path':'apps/Sample.exe'}]}), patch.object(portable.subprocess,'Popen',return_value=process):
            with self.assertRaisesRegex(RuntimeError,'code 5'): portable.launch(self.root,'sample','apps/Sample.exe',launcher.safe_path,lambda _:None)

    def test_stop_detaches_without_killing_application(self):
        process=Mock();process.wait.side_effect=portable.subprocess.TimeoutExpired('fixture',0.5)
        with patch.object(portable,'options',return_value={'files':[{'path':'apps/Sample.exe'}]}), patch.object(portable.subprocess,'Popen',return_value=process):
            result=portable.launch(self.root,'sample','apps/Sample.exe',launcher.safe_path,lambda _:None,Mock(side_effect=[False,True]))
            self.assertIn('remains running',result)
            process.kill.assert_not_called();process.terminate.assert_not_called()

    def test_workflow_definitions_match_browser_and_catalog(self):
        definitions=json.loads((ROOT/'assets/workflows.json').read_text('utf-8'))
        browser=(ROOT/'assets/js/workflows-data.js').read_text('utf-8').split('window.TOOLKIT_WORKFLOWS = ',1)[1]
        self.assertEqual(definitions,json.JSONDecoder().raw_decode(browser)[0])
        catalog={t['id']:t for t in json.loads((ROOT/'assets/toolkit-manifest.json').read_text('utf-8'))}
        for workflow in definitions.values():
            for step in workflow['steps']:
                if step.get('tool'): self.assertEqual(catalog[step['tool']]['kind'],'Portable')

    def workflow(self,mode='automatic'):
        (self.root/'assets/workflows.json').write_text(json.dumps({'test':{'name':'Test','steps':[{'text':'Authorize'},{'text':'Inspect','tool':'sample'},{'text':'Verify'}]}}))
        self.ready=threading.Event()
        def publish(state):
            if state['workflow']['waiting']: self.ready.set()
        return portable.Workflow(self.root,'test',mode,launcher.safe_path,publish)

    def advance(self,w,command):
        self.assertTrue(self.ready.wait(3));self.ready.clear()
        w.control({'run':w.id,'step':w.step,'command':command})

    def test_automatic_launch_waits_for_authorization_and_review(self):
        w=self.workflow()
        with patch.object(w,'run_tool',return_value='Process exited; review') as launch:
            thread=threading.Thread(target=w.run,daemon=True);thread.start()
            self.assertTrue(self.ready.wait(3));launch.assert_not_called()
            self.advance(w,'next');self.assertTrue(self.ready.wait(3));launch.assert_called_once()
            self.assertEqual(len(w.history),1)
            with self.assertRaises(ValueError): w.control({'run':'stale','step':1,'command':'next'})
            with self.assertRaises(ValueError): w.control({'run':w.id,'step':0,'command':'next'})
            self.advance(w,'skip');self.advance(w,'next');thread.join(3)
            self.assertFalse(thread.is_alive());self.assertIn('not verified',w.history[1]['result'])

    def test_stop_prevents_next_launch(self):
        w=self.workflow()
        with patch.object(w,'run_tool') as launch:
            thread=threading.Thread(target=w.run,daemon=True);thread.start()
            self.advance(w,'stop');thread.join(3)
            self.assertFalse(thread.is_alive());launch.assert_not_called()

    def test_manual_mode_does_not_launch_on_advance(self):
        w=self.workflow('manual')
        with patch.object(w,'run_tool',return_value='Review') as launch:
            thread=threading.Thread(target=w.run,daemon=True);thread.start()
            self.advance(w,'next');self.assertTrue(self.ready.wait(3));launch.assert_not_called()
            self.advance(w,'run');self.assertTrue(self.ready.wait(3));launch.assert_called_once()
            self.advance(w,'stop');thread.join(3)


if __name__=='__main__': unittest.main()
