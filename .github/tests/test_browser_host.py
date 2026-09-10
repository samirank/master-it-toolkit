import asyncio
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import AsyncMock, Mock

ROOT = Path(__file__).resolve().parents[2]/'MASTER-IT-TOOLKIT'
sys.path.insert(0,str(ROOT))
import launcher
import browser_host
import activity_store


class BrowserTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        (self.root/'assets').mkdir()
        (self.root/'assets/toolkit-manifest.json').write_text(json.dumps([{'id':'test','localFolder':'apps'}]))
        self.server=Mock(root=self.root, lock=threading.Lock(), state={'busy':False})
        self.server.history=activity_store.Store(self.root,launcher.safe_path,'SECRET-TOKEN')
        self.scan=Mock(return_value='Fixture scan complete')
        self.host=browser_host.Host(self.server,launcher.safe_path,self.scan)
    def tearDown(self): self.temp.cleanup()

    def test_destination_rejects_paths_and_preserves_existing(self):
        for name in ('../x.exe','x:evil.exe','CON.exe','thing.ps1','/x.exe','x\\y.exe'):
            with self.assertRaises(ValueError): browser_host.destination(self.root,'test',name,launcher.safe_path)
        p=browser_host.destination(self.root,'test','tool.exe',launcher.safe_path);p.write_bytes(b'original')
        with self.assertRaises(ValueError): browser_host.destination(self.root,'test','tool.exe',launcher.safe_path)
        self.assertEqual(p.read_bytes(),b'original')

    def test_busy_download_is_cancelled_without_overwriting_job(self):
        self.server.lock.acquire(); self.server.state={'busy':True,'message':'Existing job'}
        download=Mock(cancel=AsyncMock())
        asyncio.run(self.host.save(download,'test',self.root))
        download.cancel.assert_awaited_once(); self.scan.assert_not_called()
        self.assertEqual(self.server.state['message'],'Existing job');self.server.lock.release()

    def test_sqlite_history_persists_and_redacts_token(self):
        self.server.history.record('test',{'tool':'test','stage':'error','message':'Example SECRET-TOKEN log'})
        another=activity_store.Store(self.root,launcher.safe_path)
        row=another.recent()['jobs'][0]
        self.assertEqual(row['message'],'Example [session] log');self.assertEqual(row['stage'],'error')
        self.assertTrue(another.path.is_relative_to(self.root/'70_DOCUMENTATION/Service-Notes'))

    @unittest.skipUnless(importlib.util.find_spec('playwright'),'Requires bundled browser test environment')
    def test_real_chromium_download_routes_to_tool_and_calls_scan(self):
        class Fixture(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                if self.path=='/payload':
                    data=b'Harmless test file. Not an executable.'*1024
                    self.send_response(200);self.send_header('Content-Disposition','attachment; filename="fixture.zip"')
                    self.send_header('Content-Type','application/zip')
                else:
                    data=b'<script>setTimeout(()=>location.href="/payload",300)</script>'
                    self.send_response(200);self.send_header('Content-Type','text/html')
                self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        fixture=ThreadingHTTPServer(('127.0.0.1',0),Fixture)
        threading.Thread(target=fixture.serve_forever,daemon=True).start()
        previous=os.environ.get('TOOLKIT_BROWSER_TEST_HEADLESS')
        os.environ['TOOLKIT_BROWSER_TEST_HEADLESS']='1'
        os.environ['PLAYWRIGHT_BROWSERS_PATH']=str(ROOT/'runtime-browser')
        try:
            self.host.open('http://127.0.0.1:'+str(fixture.server_port),'test')
            deadline=time.monotonic()+40
            while time.monotonic()<deadline:
                if self.server.state.get('stage') in ('complete','error'): break
                time.sleep(.1)
            self.assertEqual(self.server.state.get('stage'),'complete',self.server.state)
            self.assertEqual((self.root/'apps/fixture.zip').read_bytes(),b'Harmless test file. Not an executable.'*1024)
            self.scan.assert_called_once()
            self.assertEqual(self.server.history.recent()['jobs'][0]['action'],'vendor-download')
        finally:
            self.host.stop.set()
            deadline=time.monotonic()+10
            while self.host.windows and time.monotonic()<deadline:time.sleep(.1)
            fixture.shutdown();fixture.server_close()
            if previous is None:os.environ.pop('TOOLKIT_BROWSER_TEST_HEADLESS',None)
            else:os.environ['TOOLKIT_BROWSER_TEST_HEADLESS']=previous


if __name__=='__main__':unittest.main()
