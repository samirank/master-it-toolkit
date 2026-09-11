import sys,tempfile,unittest,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]/'MASTER-IT-TOOLKIT';sys.path.insert(0,str(ROOT))
import launcher,activity_store,secure_vault as v
class VaultTests(unittest.TestCase):
 def test_migrate_lock_recovery_and_save(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);store=activity_store.Store(root,launcher.safe_path);store.workspace('notes',{'text':'private customer note'})
   recovery=v.setup(store.path,'fourteen plus secure characters')
   self.assertNotIn(b'private customer note',store.path.read_bytes())
   store.workspace('notes',{'text':'updated secret'});self.assertEqual(store.workspace()['notes']['text'],'updated secret')
   v.lock(store.path)
   with self.assertRaises(ValueError):store.workspace()
   with self.assertRaises(ValueError):v.unlock(store.path,'wrong')
   v.unlock(store.path,recovery,recovery=True);self.assertEqual(store.workspace()['notes']['text'],'updated secret')
   self.assertNotIn(b'updated secret',store.path.read_bytes())
   v.lock(store.path)
 def test_six_digit_pin_and_minimum_length(self):
  with tempfile.TemporaryDirectory() as tmp:
   store=activity_store.Store(Path(tmp),launcher.safe_path)
   with self.assertRaisesRegex(ValueError,'6 characters'):v.setup(store.path,'12345')
   v.setup(store.path,'123456');v.lock(store.path)
   with self.assertRaises(ValueError):v.unlock(store.path,'654321')
   v.unlock(store.path,'123456');self.assertFalse(v.status(store.path)['locked']);v.lock(store.path)
 def test_tampering_fails_closed(self):
  with tempfile.TemporaryDirectory() as tmp:
   store=activity_store.Store(Path(tmp),launcher.safe_path);v.setup(store.path,'another long passphrase');v.lock(store.path)
   data=bytearray(store.path.read_bytes());data[-30]^=1;store.path.write_bytes(data)
   with self.assertRaises((ValueError,KeyError)):v.unlock(store.path,'another long passphrase')
if __name__=='__main__':unittest.main()
