import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]/'MASTER-IT-TOOLKIT'
sys.path.insert(0,str(ROOT))
import launcher
import tool_downloads as downloads

class DownloadsTests(unittest.TestCase):
    def test_hwinfo_discovers_only_stable_official_portable_packages(self):
        page=b'<a href="https://www.hwinfo.com/files/hwi_852.zip">Stable</a><a href="https://www.hwinfo.com/files/hwi_853-6070.zip">Beta</a><a href="https://evil.invalid/files/hwi_999.zip">Bad</a>'
        with patch.object(downloads,'fetch_bytes',return_value=page):
            entry=downloads.hwinfo_portable()
        self.assertEqual(entry['version'],'8.52')
        self.assertEqual(entry['assets'][0]['url'],'https://www.hwinfo.com/files/hwi_852.zip')
        self.assertEqual(entry['assets'][0]['architecture'],'universal')
        with patch.object(downloads,'fetch_bytes',return_value=b'No matching download'):
            with self.assertRaises(ValueError):downloads.hwinfo_portable()

    def test_truncated_http_response_is_removed_and_retry_can_complete(self):
        import threading,urllib.request
        from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
        payload=b'complete package payload'; truncated=[True]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                self.send_response(200);self.send_header('Content-Length',str(len(payload)));self.end_headers()
                self.wfile.write(payload[:4] if truncated[0] else payload)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        asset={'id':'fixture','name':'tool.zip','url':'https://example.com/tool.zip','size':0,'digest':None}
        def transport(_):
            response=urllib.request.urlopen('http://127.0.0.1:'+str(server.server_port),timeout=5)
            response.url=asset['url'];return response
        try:
            with tempfile.TemporaryDirectory() as tmp,patch.object(downloads,'open_package',side_effect=transport):
                root=Path(tmp);info={'folder':'tools','assets':[asset]}
                with self.assertRaisesRegex(ValueError,'Incomplete'):
                    downloads.save_selected(root,'fixture',['fixture'],launcher.safe_path,lambda _:None,resolved=info)
                self.assertEqual(list((root/'tools').iterdir()),[])
                self.assertFalse((root/'assets/download-receipts.json').exists())
                truncated[0]=False
                downloads.save_selected(root,'fixture',['fixture'],launcher.safe_path,lambda _:None,resolved=info)
                self.assertEqual((root/'tools/tool.zip').read_bytes(),payload)
                self.assertTrue((root/'assets/download-receipts.json').is_file())
        finally:server.shutdown();server.server_close();thread.join()

    def test_stop_after_current_file_still_refreshes_inventory(self):
        stopped=[False];scans=[];callbacks=[]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'assets/js').mkdir(parents=True)
            (root/'assets/toolkit-manifest.json').write_text(json.dumps([{'id':'fixture','name':'Fixture','officialDownload':'https://example.com','kind':'Portable','license':'Free'}]))
            def scan():
                scans.append(True)
                (root/'assets/js/local-inventory.js').write_text('window.LOCAL_INVENTORY = '+json.dumps({'tools':{'fixture':{'downloaded':stopped[0]}}})+';')
            def save(*args,**kwargs):stopped[0]=True;return 'Saved: tool.zip'
            with patch.object(downloads,'options',return_value={'assets':[{'id':'a'}]}),patch.object(downloads,'recommended',return_value=[{'id':'a'}]),patch.object(downloads,'save_selected',side_effect=save):
                report=downloads.bulk_download(root,{},launcher.safe_path,lambda _:None,scan,lambda:callbacks.append(True),lambda:stopped[0])
            self.assertEqual(len(scans),2);self.assertEqual(len(callbacks),2)
            self.assertIn('1 processed',report)
            self.assertIn('Queue cancelled',report)
            self.assertIn('true',(root/'assets/js/local-inventory.js').read_text())

    def test_platforms(self):
        for name,expected in [('7z2603-x64.exe','Windows'),('7z2603-linux-arm64.tar.xz','Linux'),('7z2603-mac.tar.xz','macOS')]:
            self.assertEqual(downloads.platform_for(name,['Windows']),expected)
    def test_release_source_and_asset_filter(self):
        release={'assets':[{'id':1,'name':'tool.exe','browser_download_url':'https://github.com/ip7z/7zip/releases/download/v/tool.exe'}, {'id':2,'name':'bad.exe','browser_download_url':'https://untrusted.invalid/bad.exe'}]}
        with patch.object(downloads,'fetch_json',return_value=release) as fetch:
            self.assertEqual(len(downloads.options(ROOT,'7zip',live=True)['assets']),1)
            self.assertEqual(fetch.call_args.args[0],'https://api.github.com/repos/ip7z/7zip/releases/latest')
    def test_winutil_release_script_is_offered(self):
        release={'assets':[{'id':1,'name':'winutil.ps1','browser_download_url':'https://github.com/ChrisTitusTech/winutil/releases/download/test/winutil.ps1'},
            {'id':2,'name':'unrelated.ps1','browser_download_url':'https://github.com/ChrisTitusTech/winutil/releases/download/test/unrelated.ps1'}]}
        with patch.object(downloads,'fetch_json',return_value=release):
            self.assertEqual([a['name'] for a in downloads.options(ROOT,'winutil',live=True)['assets']],['winutil.ps1'])
    def test_download_checksum_existing_and_invalid_selection(self):
        payload=b'test package'; checksum=launcher.digest(payload)
        asset={'id':'1','name':'tool.zip','url':'https://github.com/ip7z/7zip/releases/download/v/tool.zip','size':len(payload),'digest':'sha256:'+checksum}
        info={'folder':'20_PORTABLE_APPS/Test','assets':[asset]}
        class Response(io.BytesIO): url=asset['url']
        with tempfile.TemporaryDirectory() as temp, patch.object(downloads,'options',return_value=info):
            root=Path(temp)
            with patch.object(downloads,'open_package',return_value=Response(payload)):
                result=downloads.save_selected(root,'7zip',['1'],launcher.safe_path,lambda _:None)
            self.assertIn('SHA256 verified',result)
            self.assertEqual((root/info['folder']/'tool.zip').read_bytes(),payload)
            self.assertIn('Kept existing',downloads.save_selected(root,'7zip',['1'],launcher.safe_path,lambda _:None))
            with self.assertRaises(ValueError): downloads.save_selected(root,'7zip',['spoofed'],launcher.safe_path,lambda _:None)
    def test_mismatch_cleans_partial(self):
        asset={'id':'1','name':'tool.zip','url':'https://github.com/ip7z/7zip/releases/download/v/tool.zip','size':3,'digest':'sha256:'+'0'*64}
        class Response(io.BytesIO): url=asset['url']
        with tempfile.TemporaryDirectory() as temp, patch.object(downloads,'options',return_value={'folder':'tools','assets':[asset]}),patch.object(downloads,'open_package',return_value=Response(b'bad')):
            with self.assertRaises(ValueError): downloads.save_selected(Path(temp),'7zip',['1'],launcher.safe_path,lambda _:None)
            self.assertEqual(list((Path(temp)/'tools').iterdir()),[])
    @unittest.skipUnless(os.name=='nt','Windows policy verification')
    def test_script_runs_under_process_restriction(self):
        shell=shutil.which('powershell.exe')
        with tempfile.TemporaryDirectory() as temp:
            script=Path(temp)/'test.ps1';script.write_text("Write-Output 'POLICY-FIX-PASS'")
            command=launcher.powershell_command(shell,script,'pc');command.remove('-NoExit')
            result=subprocess.run(command,env=dict(os.environ,PSExecutionPolicyPreference='Restricted'),capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('POLICY-FIX-PASS',result.stdout)

if __name__=='__main__':unittest.main()
