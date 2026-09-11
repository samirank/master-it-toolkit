import sys,json,tempfile,threading,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]/'MASTER-IT-TOOLKIT';sys.path.insert(0,str(ROOT))
import launcher,portable_tools,activity_store
class JobTests(unittest.TestCase):
 def test_resume_keeps_checkpoints_and_rejects_changed_machine_or_definition(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'assets').mkdir();definition={'test':{'name':'Test','steps':[{'text':'First','action':'manual'},{'text':'Second','action':'manual'}]}}
   path=root/'assets/workflows.json';path.write_text(json.dumps(definition))
   with patch('host_inventory.machine_identity',return_value={'id':'machine-a'}):
    prior=portable_tools.Workflow(root,'test','manual',launcher.safe_path,lambda _:None)
    prior.record.update(status='interrupted',steps=[{'step':0,'text':'First','result':'verified by technician'}],stepNotes={'0':'Already checked'})
    prior.store.workflow_job(prior.record)
    resumed=portable_tools.Workflow(root,'test','manual',launcher.safe_path,lambda _:None,setup={'resumeId':prior.id})
    self.assertEqual(resumed.start_step,1);self.assertNotEqual(resumed.id,prior.id)
    self.assertEqual(resumed.record['resumedFrom'],prior.id);self.assertEqual(resumed.record['stepNotes']['0'],'Already checked')
    definition['test']['steps'][0]['text']='Changed';path.write_text(json.dumps(definition))
    with self.assertRaisesRegex(ValueError,'Cannot resume'):portable_tools.Workflow(root,'test','manual',launcher.safe_path,lambda _:None,setup={'resumeId':prior.id})
   with patch('host_inventory.machine_identity',return_value={'id':'machine-b'}):
    with self.assertRaisesRegex(ValueError,'Cannot resume'):portable_tools.Workflow(root,'test','manual',launcher.safe_path,lambda _:None,setup={'resumeId':prior.id})
 def test_checkpoint_inputs_notes_and_machine_history(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'assets').mkdir();(root/'assets/workflows.json').write_text(json.dumps({'test':{'name':'Test','steps':[{'text':'Review','tool':'test','action':'manual'}]}}))
   states=[];prepared=[]
   with patch('host_inventory.machine_identity',return_value={'id':'machine-a','name':'PC','serial':'123','mac':'aa','matchBasis':'serial'}):
    flow=portable_tools.Workflow(root,'test','automatic',launcher.safe_path,states.append,setup={'inputs':{'ticket':'ABC','issue':'Test'},'prepare':True},prepare=lambda f,s:prepared.append(s['tool']) or 'Prepared')
   thread=threading.Thread(target=flow.run);thread.start()
   for _ in range(100):
    if flow.waiting:break
    time.sleep(.01)
   self.assertTrue(flow.waiting);self.assertEqual(prepared,['test'])
   flow.control({'run':flow.id,'step':0,'command':'note','notes':'Checked cable'})
   saved=activity_store.Store(root,launcher.safe_path).workflow_job(machine='machine-a')[0]
   self.assertEqual(saved['stepNotes']['0'],'Checked cable');self.assertEqual(saved['inputs']['ticket'],'ABC')
   flow.control({'run':flow.id,'step':0,'command':'next','notes':'Working'})
   thread.join(3);self.assertFalse(thread.is_alive())
   store=activity_store.Store(root,launcher.safe_path);self.assertEqual(store.workflow_job(machine='machine-a')[0]['status'],'completed');self.assertEqual(store.workflow_job(machine='machine-b'),[])
 def test_copy_requires_review_and_records_verified_output(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);root=base/'toolkit';root.mkdir();source=base/'source';source.mkdir();dest=base/'destination';dest.mkdir();(source/'sample.txt').write_bytes(b'migration fixture')
   (root/'assets').mkdir();(root/'assets/workflows.json').write_text(json.dumps({'test':{'name':'Copy test','steps':[{'text':'Copy reviewed files','action':'copy'}]}}))
   with patch('host_inventory.machine_identity',return_value={'id':'machine-a'}):
    flow=portable_tools.Workflow(root,'test','manual',launcher.safe_path,lambda _:None,setup={'inputs':{'source':str(source),'destination':str(dest)}})
   thread=threading.Thread(target=flow.run);thread.start()
   try:
    for _ in range(200):
     if flow.waiting:break
     time.sleep(.01)
    with self.assertRaisesRegex(ValueError,'Review a current'):flow.control({'run':flow.id,'step':0,'command':'copy'})
    plan=flow.preview_copy(flow.id,0);self.assertEqual(plan['fileCount'],1);self.assertEqual(list(dest.iterdir()),[])
    flow.control({'run':flow.id,'step':0,'command':'copy','planToken':plan['token']})
    for _ in range(300):
     if flow.waiting and flow.record.get('migrationResult'):break
     time.sleep(.01)
    result=flow.record['migrationResult'];self.assertTrue(result['verified']);self.assertEqual((Path(result['output'])/'sample.txt').read_bytes(),b'migration fixture')
    self.assertTrue(thread.is_alive(),'Copy must still wait for technician verification')
    flow.control({'run':flow.id,'step':0,'command':'next'});thread.join(3)
    saved=flow.store.workflow_job(machine='machine-a')[0];self.assertEqual(saved['status'],'completed');self.assertTrue(saved['migrationResult']['verified'])
   finally:
    if thread.is_alive():flow.control({'run':flow.id,'command':'stop'});thread.join(3)
 def test_preparation_only_installs_single_signed_candidate(self):
  with tempfile.TemporaryDirectory() as tmp:
   server=launcher.Server(Path(tmp),port=0)
   flow=SimpleNamespace(stop=False,setup={'install':True,'updates':False},state=lambda _:None)
   info={'installedOnHost':False,'reason':'','name':'Test','files':[{'path':'setup.exe','sha256':'a'*64,'signature':{'status':'Valid'}}]}
   try:
    with patch('tool_downloads.refresh_catalog'),patch('tool_downloads.bulk_download',return_value='Downloaded') as download,patch('launcher.run_script',return_value='Scanned'),patch('install_tools.options',return_value=info),patch('install_tools.install',return_value='Installed') as install:
     server.prepare_workflow_step(flow,{'tool':'test','action':'install'});self.assertEqual(install.call_count,1);self.assertEqual(download.call_args.args[1]['tools'],['test'])
     info['files'][0]['signature']['status']='UnknownError';install.reset_mock();server.prepare_workflow_step(flow,{'tool':'test','action':'install'});install.assert_not_called()
     flow.setup['install']=False;server.prepare_workflow_step(flow,{'tool':'test','action':'install'});install.assert_not_called()
   finally:server.server_close()
if __name__=='__main__':unittest.main()
