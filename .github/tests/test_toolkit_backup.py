import importlib.util,json,sqlite3,tempfile,unittest,zipfile
from pathlib import Path
from contextlib import closing
spec=importlib.util.spec_from_file_location('backup',Path(__file__).resolve().parents[2]/'MASTER-IT-TOOLKIT/60_SCRIPTS/Backup/toolkit_backup.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
class BackupTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.root=self.base/'MASTER-IT-TOOLKIT';self.root.mkdir();self.dest=self.base/'backup';self.dest.mkdir()
  for name in ('assets/data.json','20_PORTABLE_APPS/tool.exe','90_TEMP/partial.bin','70_DOCUMENTATION/Service-Notes/BrowserProfile/cookies','70_DOCUMENTATION/Service-Notes/job.txt'):
   p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('fixture')
  db=self.root/b.DB;db.parent.mkdir(parents=True,exist_ok=True)
  with closing(sqlite3.connect(db)) as connection:connection.execute('CREATE TABLE workspace (name TEXT)');connection.execute("INSERT INTO workspace VALUES ('my custom build')");connection.commit()
 def tearDown(self):self.tmp.cleanup()
 def test_workspace_snapshot_verifies_and_restores_sqlite(self):
  b.backup(self.root,{'destination':str(self.dest),'scope':'workspace'},lambda _:None)
  p=next(self.dest.glob('*.zip'));self.assertIn('verified',b.verify(p))
  with zipfile.ZipFile(p) as z:
   self.assertNotIn('MASTER-IT-TOOLKIT/20_PORTABLE_APPS/tool.exe',z.namelist());self.assertFalse(any('BrowserProfile' in n or '90_TEMP' in n for n in z.namelist()))
   restored=self.base/'restored.sqlite';restored.write_bytes(z.read('MASTER-IT-TOOLKIT/'+b.DB))
  with closing(sqlite3.connect(restored)) as db:self.assertEqual(db.execute('SELECT name FROM workspace').fetchone()[0],'my custom build');self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
 def test_full_and_existing_versions_preserved(self):
  (self.base/'Master-IT-Toolkit.exe').write_bytes(b'launcher')
  for _ in range(2):b.backup(self.root,{'destination':str(self.dest),'scope':'full'},lambda _:None)
  archives=list(self.dest.glob('*.zip'));self.assertEqual(len(archives),2)
  with zipfile.ZipFile(archives[0]) as z:self.assertIn('MASTER-IT-TOOLKIT/20_PORTABLE_APPS/tool.exe',z.namelist());self.assertIn('Master-IT-Toolkit.exe',z.namelist())
 def test_recursive_destination_and_cancellation(self):
  with self.assertRaises(ValueError):b.backup(self.root,{'destination':str(self.root),'scope':'full'},lambda _:None)
  cancelled=[False]
  def progress(state):
   if state['stage']=='backup':cancelled[0]=True
  with self.assertRaises(InterruptedError):b.backup(self.root,{'destination':str(self.dest),'scope':'full'},progress,lambda:cancelled[0])
  self.assertEqual(list(self.dest.iterdir()),[])
 def test_modified_file_and_corrupted_archive_fail(self):
  changed=[False]
  def progress(state):
   if state['stage']=='backup' and 'data.json' in state['message'] and not changed[0]:(self.root/'assets/data.json').write_text('changed length');changed[0]=True
  with self.assertRaises(ValueError):b.backup(self.root,{'destination':str(self.dest),'scope':'workspace'},progress)
  self.assertEqual(list(self.dest.iterdir()),[])
  b.backup(self.root,{'destination':str(self.dest),'scope':'workspace'},lambda _:None)
  p=next(self.dest.glob('*.zip'))
  with zipfile.ZipFile(p,'a') as z:z.writestr('unexpected','tampered')
  with self.assertRaises(ValueError):b.verify(p)
if __name__=='__main__':unittest.main()
