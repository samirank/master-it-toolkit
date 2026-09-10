import json
from pathlib import Path
import sys,tempfile,unittest,threading
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]/'MASTER-IT-TOOLKIT'
sys.path.insert(0,str(ROOT))
import launcher,portable_tools as p,activity_store
class BuildTests(unittest.TestCase):
 def test_profiles_match_browser_and_have_valid_tools(self):
  profiles=json.loads((ROOT/'assets/build-profiles.json').read_text('utf-8'))
  browser=(ROOT/'assets/js/build-profiles.js').read_text('utf-8').split(' = ',1)[1].rstrip(';\n')
  self.assertEqual(profiles,json.loads(browser));self.assertGreaterEqual(len(profiles),18)
  p.validate_custom_workflows(ROOT,{'custom-'+id:value for id,value in profiles.items()})
 def test_sqlite_roundtrip_and_reject_arbitrary_commands(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'assets').mkdir();(root/'assets/toolkit-manifest.json').write_text((ROOT/'assets/toolkit-manifest.json').read_text('utf-8'),encoding='utf-8');(root/'assets/workflows.json').write_text('{}')
   value={'custom-test':{'name':'My lab','platform':'Windows','steps':[{'text':'Check backup'},{'text':'Install browser','tool':'firefox','action':'install'}]}}
   store=activity_store.Store(root,launcher.safe_path);store.workspace('customWorkflows',value)
   self.assertEqual(activity_store.Store(root,launcher.safe_path).workspace()['customWorkflows'],value)
   store.record('workflow',{'message':'Finished','workflowName':'My lab','workflowProfile':'custom-test','workflowRecord':[{'step':0,'result':'verified'}]})
   runs=activity_store.Store(root,launcher.safe_path).recent()['workflows']
   self.assertEqual(runs[0]['profile'],'custom-test');self.assertEqual(runs[0]['steps'][0]['result'],'verified')
   with patch('platform.system',return_value='Windows'):
    flow=p.Workflow(root,'custom-test','automatic',launcher.safe_path,lambda _:None)
   self.assertEqual(flow.definition,value['custom-test'])
   bad=json.loads(json.dumps(value));bad['custom-test']['steps'][0]['command']='arbitrary.exe'
   with self.assertRaises(ValueError):store.workspace('customWorkflows',bad)
   self.assertEqual(store.workspace()['customWorkflows'],value)
 def test_install_step_never_runs_without_review(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'assets').mkdir();(root/'assets/workflows.json').write_text(json.dumps({'test':{'name':'Install test','steps':[{'text':'Install','tool':'firefox','action':'install'}]}}))
   ready=threading.Event()
   flow=p.Workflow(root,'test','automatic',launcher.safe_path,lambda state:ready.set() if state['workflow']['waiting'] else None)
   with patch('install_tools.install',return_value='Installed with checkpoint') as install,patch.object(flow,'run_tool') as run:
    thread=threading.Thread(target=flow.run,daemon=True);thread.start();self.assertTrue(ready.wait(3));ready.clear();install.assert_not_called();run.assert_not_called()
    flow.control({'run':flow.id,'step':0,'command':'install','package':'test.exe','sha256':'a'*64})
    self.assertTrue(ready.wait(3));install.assert_called_once();self.assertEqual(install.call_args.args[1]['tool'],'firefox')
    flow.control({'run':flow.id,'step':0,'command':'next'});thread.join(3);self.assertFalse(thread.is_alive())
if __name__=='__main__':unittest.main()
