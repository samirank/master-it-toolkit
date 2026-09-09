import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'MASTER-IT-TOOLKIT'))
import launcher

class TransferTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'assets').mkdir()
        (self.root/'assets/toolkit-manifest.json').write_text(json.dumps([{'id':'app','localFolder':'tools/app'}]))
        self.server=launcher.Server(self.root,port=0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base=self.server.origin+'/'+self.server.token+'/api/'
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
    def put(self,name='tool.zip',origin=None):
        return urllib.request.urlopen(urllib.request.Request(self.base+'import?tool=app&name='+name,data=b'fixture',method='PUT',headers={'Origin':origin or self.server.origin}),timeout=5)
    def test_import_preserve_and_callback(self):
        event=threading.Event()
        def scan(key): self.assertEqual(key,'inventory');event.set();return 'Inventory refreshed'
        with patch.object(launcher,'run_script',side_effect=scan):
            with self.put() as r: self.assertEqual(r.status,202)
            self.assertTrue(event.wait(3))
            # Wait for job lock handoff before trying the second import.
            self.assertTrue(self.server.lock.acquire(timeout=3));self.server.lock.release()
            self.assertEqual((self.root/'tools/app/tool.zip').read_bytes(),b'fixture')
            with self.assertRaises(urllib.error.HTTPError) as error: self.put()
            self.assertEqual(error.exception.code,400)
        with urllib.request.urlopen(self.base+'tool-files?tool=app') as r:
            data=json.load(r);self.assertEqual(data['files'][0]['name'],'tool.zip')
            self.assertEqual(data['folder'],str(self.root/'tools/app'))
        self.assertFalse(list(self.root.rglob('*.partial')))
    def test_reject_origin_traversal_and_unknown_tool(self):
        for name,origin in [('tool.zip','https://evil.invalid'),('..%2Fescape.zip',None),('note.txt',None)]:
            with self.assertRaises(urllib.error.HTTPError): self.put(name,origin)
        with self.assertRaises(urllib.error.HTTPError): urllib.request.urlopen(self.base+'tool-files?tool=unknown')
        self.assertFalse((self.root/'escape.zip').exists())
    def test_app_mode_argument(self):
        with patch.object(launcher.shutil,'which',return_value=sys.executable),patch.object(launcher.subprocess,'Popen') as popen,patch.object(launcher.webbrowser,'open') as browser:
            launcher.open_app('http://127.0.0.1:8765/test/index.html')
            self.assertIn('--app=http://127.0.0.1:8765/test/index.html',popen.call_args.args[0]);browser.assert_not_called()

if __name__=='__main__': unittest.main()
