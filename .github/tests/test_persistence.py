import sys,tempfile,unittest,json,time,sqlite3,subprocess
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]/'MASTER-IT-TOOLKIT';sys.path.insert(0,str(ROOT))
import launcher,activity_store
class PersistenceTests(unittest.TestCase):
 def test_auto_backup_reconnect_and_restart(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/'kit';root.mkdir();target=Path(tmp)/'nas'
   script=root/'60_SCRIPTS/Backup/toolkit_backup.py';script.parent.mkdir(parents=True);script.write_bytes((ROOT/'60_SCRIPTS/Backup/toolkit_backup.py').read_bytes())
   (root/'portable-tool.exe').write_bytes(b'tool payload')
   server=launcher.Server(root,port=0)
   try:
    server.history.workspace('backupSettings',dict(destination=str(target),scope='full',automatic=True,intervalHours=24))
    server.auto_backup_tick();self.assertFalse(target.exists())
    target.mkdir()
    with patch('launcher.time.time',return_value=time.time()+301):server.auto_backup_tick()
    self.assertEqual(server.state['stage'],'complete');self.assertEqual(len(list(target.glob('*.zip'))),1)
    self.assertFalse(server.lock.locked())
   finally:server.server_close()
   server=launcher.Server(root,port=0)
   try:server.auto_backup_tick();self.assertEqual(len(list(target.glob('*.zip'))),1)
   finally:server.server_close()
 def test_sqlite_uncommitted_crash(self):
  with tempfile.TemporaryDirectory() as tmp:
   store=activity_store.Store(Path(tmp),launcher.safe_path);store.workspace('notes',{'text':'committed'})
   code="import sqlite3,sys,os; db=sqlite3.connect(sys.argv[1]);db.execute(\"UPDATE workspace SET value='{}' WHERE key='notes'\");os._exit(9)"
   result=subprocess.run([sys.executable,'-c',code,str(store.path)]);self.assertEqual(result.returncode,9)
   self.assertEqual(store.workspace()['notes'],{'text':'committed'})
   db=store.connect()
   try:self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok');self.assertEqual(db.execute('PRAGMA synchronous').fetchone()[0],2)
   finally:db.close()
if __name__=='__main__':unittest.main()
