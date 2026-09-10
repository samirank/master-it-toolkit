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
import zipfile
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
        self.server.lock.acquire(); self.server.state={'busy':True,'message':'Existing job'};self.host.stop.set()
        download=Mock(cancel=AsyncMock())
        asyncio.run(self.host.save(download,'test',self.root))
        download.cancel.assert_awaited_once(); self.scan.assert_not_called()
        self.assertEqual(self.server.state['message'],'Existing job');self.server.lock.release()

    def test_queued_download_waits_then_saves_and_cleans_only_its_file(self):
        stage=self.root/'stage';stage.mkdir();source=stage/'transfer';source.write_bytes(b'fixture')
        unrelated=stage/'unrelated';unrelated.write_bytes(b'preserve')
        async def remove():
            if source.exists():source.unlink()
        download=Mock(suggested_filename='package.zip',path=AsyncMock(return_value=source),delete=AsyncMock(side_effect=remove),cancel=AsyncMock())
        download.page.context.pages=[object()]
        self.server.lock.acquire()
        async def run():
            async def release():await asyncio.sleep(.05);self.server.lock.release()
            await asyncio.gather(release(),self.host.save(download,'test',stage))
        asyncio.run(run())
        self.assertEqual((self.root/'apps/package.zip').read_bytes(),b'fixture')
        self.assertFalse(source.exists());self.assertEqual(unrelated.read_bytes(),b'preserve')
        download.cancel.assert_not_awaited();self.scan.assert_called_once();self.server.publish_completion.assert_called_once()

    def test_sqlite_history_persists_and_redacts_token(self):
        self.server.history.record('test',{'tool':'test','stage':'error','message':'Example SECRET-TOKEN log'})
        another=activity_store.Store(self.root,launcher.safe_path)
        row=another.recent()['jobs'][0]
        self.assertEqual(row['message'],'Example [session] log');self.assertEqual(row['stage'],'error')
        self.assertTrue(another.path.is_relative_to(self.root/'70_DOCUMENTATION/Service-Notes'))

    def test_ps1_only_for_catalogued_scripts_and_identical_detection(self):
        self.assertTrue(browser_host.allowed_package({'inventoryPatterns':['winutil*.ps1']},'WinUtil (1).ps1'))
        self.assertFalse(browser_host.allowed_package({'inventoryPatterns':['tool.exe']},'arbitrary.ps1'))
        a=self.root/'a';b=self.root/'b';a.write_bytes(b'known');b.write_bytes(b'known')
        self.assertTrue(self.host.same_file(a,b));b.write_bytes(b'other');self.assertFalse(self.host.same_file(a,b))

    @unittest.skipUnless(importlib.util.find_spec('playwright'),'Requires bundled browser test environment')
    def test_real_adblocking_and_site_exception(self):
        with zipfile.ZipFile(ROOT.parent/'.github/vendor/ubol-2026.907.2003.zip') as archive:archive.extractall(self.root/'extension')
        os.environ['PLAYWRIGHT_BROWSERS_PATH']=str(ROOT/'runtime-browser')
        async def check():
            from playwright.async_api import async_playwright
            async with async_playwright() as runtime:
                extension=str(self.root/'extension')
                context=await runtime.chromium.launch_persistent_context(str(self.root/'profile'),headless=True,channel='chromium',ignore_default_args=['--disable-extensions'],args=['--disable-extensions-except='+extension,'--load-extension='+extension])
                try:
                    worker=context.service_workers[0] if context.service_workers else await context.wait_for_event('serviceworker')
                    base=worker.url.split('/js/')[0]
                    await self.host.set_filter(context,base,'fixture.test',True)
                    await context.route('https://fixture.test/**',lambda route:route.fulfill(body='<title>Fixture</title>',content_type='text/html'))
                    await context.route('https://googleads.g.doubleclick.net/**',lambda route:route.fulfill(body='fixture',headers={'Access-Control-Allow-Origin':'*'}))
                    page=await context.new_page();await page.goto('https://fixture.test/')
                    blocked=[];page.on('requestfailed',lambda request:blocked.append(request.failure))
                    result=await page.evaluate("()=>fetch('https://googleads.g.doubleclick.net/pagead/ads').then(async r=>({body:await r.text(),url:r.url})).catch(()=>({body:'blocked',url:''}))")
                    self.assertNotEqual(result['body'],'fixture');self.assertTrue(result['url'].startswith('chrome-extension://') or any('BLOCKED_BY_CLIENT' in failure for failure in blocked),result)
                    await self.host.set_filter(context,base,'fixture.test',False)
                    await page.reload()
                    result=await page.evaluate("()=>fetch('https://googleads.g.doubleclick.net/pagead/ads').then(async r=>({body:await r.text(),url:r.url})).catch(()=>({body:'blocked',url:''}))")
                    self.assertEqual(result['body'],'fixture')
                finally:await context.close()
        asyncio.run(check())

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
        with zipfile.ZipFile(ROOT.parent/'.github/vendor/ubol-2026.907.2003.zip') as archive: archive.extractall(self.root/'extension')
        self.host.extension=self.root/'extension'
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
