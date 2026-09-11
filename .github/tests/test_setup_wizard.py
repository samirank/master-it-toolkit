import sys,tempfile,unittest,threading,time
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]/'MASTER-IT-TOOLKIT';sys.path.insert(0,str(ROOT))
import launcher,activity_store,setup_wizard as wizard,secure_vault

class SetupTests(unittest.TestCase):
 def test_first_run_resume_completion_and_changed_volume(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);store=activity_store.Store(root,launcher.safe_path)
   store.workspace('notes',{'issue':'preserve me'})
   self.assertTrue(wizard.status(root,store,'volume-a')['required'])
   wizard.save(root,store,{'step':2,'completed':False},'volume-a')
   reopened=activity_store.Store(root,launcher.safe_path)
   self.assertEqual(wizard.status(root,reopened,'volume-a')['step'],2)
   wizard.save(root,reopened,{'step':3,'completed':True},'volume-a')
   self.assertFalse(wizard.status(root,reopened,'volume-a')['required'])
   self.assertFalse(wizard.status(root,reopened,'')['required'],'Unknown identity must not repeatedly reset setup')
   state=wizard.status(root,reopened,'volume-b');self.assertTrue(state['changedDrive']);self.assertEqual(state['step'],0)
   self.assertEqual(reopened.workspace()['notes'],{'issue':'preserve me'})
 def test_validation_and_vault_persistence(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);store=activity_store.Store(root,launcher.safe_path)
   for body in ({'step':8,'completed':True},{'step':True,'completed':False},{'step':0,'completed':'yes'},{'step':0,'completed':False,'volumes':{}}):
    with self.assertRaises(ValueError):wizard.save(root,store,body,'volume-a')
   secure_vault.setup(store.path,'fixture passphrase for wizard')
   wizard.save(root,store,{'step':3,'completed':True},'volume-a');secure_vault.lock(store.path)
   self.assertNotIn(b'setupState',store.path.read_bytes())
   secure_vault.unlock(store.path,'fixture passphrase for wizard')
   self.assertFalse(wizard.status(root,store,'volume-a')['required'])
   secure_vault.lock(store.path)
 def test_status_waits_until_setup_key_is_available(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);store=activity_store.Store(root,launcher.safe_path);written=threading.Event();release=threading.Event();observed=[]
   original=secure_vault.atomic
   def pause(path,data):original(path,data);written.set();release.wait(3)
   with patch.object(secure_vault,'atomic',side_effect=pause):
    creator=threading.Thread(target=secure_vault.setup,args=(store.path,'fixture passphrase for status'));creator.start()
    try:
     self.assertTrue(written.wait(3));reader=threading.Thread(target=lambda:observed.append(secure_vault.status(store.path)));reader.start()
     time.sleep(.05);self.assertEqual(observed,[])
    finally:release.set();creator.join(3)
    reader.join(3);self.assertEqual(observed,[{'configured':True,'locked':False}]);secure_vault.lock(store.path)
 def test_identity_failure_is_optional(self):
  with patch('setup_wizard.subprocess.check_output',side_effect=OSError('Unavailable')):
   if sys.platform.startswith('linux'):self.assertEqual(wizard.volume_id(ROOT),'')
  self.assertIsInstance(wizard.volume_id(ROOT),str)

if __name__=='__main__':unittest.main()
