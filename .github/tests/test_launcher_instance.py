import sys, tempfile, subprocess, unittest, threading
from pathlib import Path
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[2]/'MASTER-IT-TOOLKIT'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'60_SCRIPTS/Runtime'))
import launcher
from launcher_instance import Instance

class InstanceTests(unittest.TestCase):
 def test_process_lock_release_and_authenticated_focus(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);one=Instance(root);self.assertTrue(one.acquire())
   code="import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from launcher_instance import Instance;i=Instance(Path(sys.argv[2]));print(i.acquire());i.close()"
   def second():return subprocess.check_output([sys.executable,'-c',code,str(ROOT/'60_SCRIPTS/Runtime'),tmp],text=True).strip()
   self.assertEqual(second(),'False')
   server=launcher.Server(root,port=0);server.browser=Mock();server.browser.available.return_value=True
   thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    one.publish(server.origin,server.token)
    self.assertTrue(Instance(root).focus(timeout=2));server.browser.focus_dashboard.assert_called_once()
   finally:server.shutdown();server.server_close();thread.join();one.close()
   self.assertEqual(second(),'True');self.assertFalse(one.record.exists())

if __name__=='__main__':unittest.main()
