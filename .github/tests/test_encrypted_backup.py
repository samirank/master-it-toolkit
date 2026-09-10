import importlib.util,json,sys,tempfile,unittest,os
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]/'MASTER-IT-TOOLKIT';sys.path.insert(0,str(ROOT))
import secure_vault as vault
spec=importlib.util.spec_from_file_location('encrypted_backup',ROOT/'60_SCRIPTS/Backup/encrypted_backup.py')
backup=importlib.util.module_from_spec(spec);spec.loader.exec_module(backup)

class EncryptedBackupTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.root=self.base/'kit';self.root.mkdir()
  self.db=self.root/'70_DOCUMENTATION/Service-Notes/Activity/activity.sqlite'
  self.secret='a sufficiently long test passphrase';self.recovery=vault.setup(self.db,self.secret)
  self.target=self.base/'backups';self.target.mkdir()
 def tearDown(self):vault.lock(self.db);self.tmp.cleanup()
 def test_recovery_without_original_database(self):
  expected=vault.KEYS[str(self.db.resolve())];doc=vault.header(self.db)
  metadata=self.target/'toolkit-backup-key.json';metadata.write_text(json.dumps({k:doc[k] for k in ('salt','password','recovery')}))
  vault.lock(self.db);self.db.unlink()
  self.assertEqual(backup.recover_key(metadata,self.secret),expected)
  self.assertEqual(backup.recover_key(metadata,self.recovery,True),expected)
  with self.assertRaises(ValueError):backup.recover_key(metadata,'wrong password')
 def test_invalid_settings_start_no_process(self):
  with patch.object(backup.subprocess,'Popen') as proc:
   for extra in ({'keepLast':-1},{'scope':'bad'},{'destination':str(self.root)}):
    with self.assertRaises(ValueError):backup.run(self.root,{'destination':str(self.target),**extra},lambda _:None)
   proc.assert_not_called()
 def test_locked_vault_never_starts_plaintext_backup(self):
  vault.lock(self.db)
  with patch.object(backup.subprocess,'Popen') as proc:
   with self.assertRaisesRegex(ValueError,'unlock'):backup.run(self.root,{'destination':str(self.target)},lambda _:None)
   proc.assert_not_called()
 @unittest.skipUnless(os.environ.get('RESTIC_TEST_BINARY'),'Set RESTIC_TEST_BINARY for real backup/restore verification')
 def test_actual_backup_restore_after_ssd_loss(self):
  (self.root/'private-note.txt').write_text('Private fixture note')
  (self.base/'Master-IT-Toolkit.exe').write_text('Launcher fixture')
  restored=self.base/'restored';restored.mkdir();settings={'destination':str(self.target),'scope':'full'}
  with patch.object(backup,'executable',return_value=os.environ['RESTIC_TEST_BINARY']):
   backup.run(self.root,settings,lambda _:None)
   snapshots=json.loads(backup.run(self.root,dict(settings,operation='snapshots'),lambda _:None))
   vault.lock(self.db)
   key=backup.recover_key(self.target/'toolkit-backup-key.json',self.recovery,True)
   backup.run(self.root,dict(settings,operation='restore',snapshot=snapshots[-1]['id'],restoreDestination=str(restored)),lambda _:None,repository_key=key)
   self.assertEqual(next(restored.rglob('private-note.txt')).read_text(),'Private fixture note')
   self.assertEqual(next(restored.rglob('Master-IT-Toolkit.exe')).read_text(),'Launcher fixture')
   recovered=next(restored.rglob('activity.sqlite'));vault.unlock(recovered,self.recovery,True);vault.lock(recovered)

if __name__=='__main__':unittest.main()
