import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'MASTER-IT-TOOLKIT'))
import tool_downloads as d
import launcher
spec=importlib.util.spec_from_file_location('catalog_refresh',ROOT/'.github/scripts/refresh_download_catalog.py')
monitor=importlib.util.module_from_spec(spec);spec.loader.exec_module(monitor)

def asset(name='tool-x64.exe',id='a',platform='Windows',arch='x64'):
    return {'id':id,'name':name,'url':'https://github.com/org/tool/releases/download/v1/'+name,'platform':platform,'architecture':arch,'size':3,'digest':None}

class CatalogTests(unittest.TestCase):
    def test_repository_is_runtime_authority(self):
        with patch.object(d,'fetch_json',side_effect=AssertionError('Publisher queried directly')):
            info=d.options(ROOT/'MASTER-IT-TOOLKIT','clonezilla')
        self.assertTrue(info['assets']);self.assertEqual(info['assets'][0]['platform'],'Boot ISO')

    def test_architecture_and_platform_selection(self):
        info={'assets':[asset(),asset('tool-arm64.exe','arm',arch='arm64'),asset('linux-x64.AppImage','linux','Linux'),asset('rescue-amd64.iso','iso','Boot ISO')]}
        self.assertEqual({a['id'] for a in d.recommended(info,'Windows','x64')},{'a','iso'})
        self.assertEqual({a['id'] for a in d.recommended(info,'All','All')},{'a','arm','linux','iso'})

    def test_repo_transfer_follows_canonical_release(self):
        release={'html_url':'https://github.com/new-owner/tool/releases/tag/v2','tag_name':'v2','assets':[{'id':1,'name':'tool.exe','browser_download_url':'https://github.com/new-owner/tool/releases/download/v2/tool.exe'}]}
        with patch.object(d,'fetch_json',return_value=release):
            self.assertEqual(len(d.options(ROOT/'MASTER-IT-TOOLKIT','7zip',live=True)['assets']),1)

    def test_sourceforge_version_filename_changes(self):
        xml=b'<rss><channel><item><link>https://sourceforge.net/projects/clonezilla/files/stable/9.0/new-amd64.iso/download</link></item><item><link>https://sourceforge.net/projects/clonezilla/files/stable/8.0/old-amd64.iso/download</link></item></channel></rss>'
        with patch.object(d,'fetch_bytes',return_value=xml):info=d.sourceforge({'project':'clonezilla','folder':'stable'})
        self.assertEqual(info['version'],'9.0');self.assertEqual([a['name'] for a in info['assets']],['new-amd64.iso'])

    def test_unsafe_catalog_paths_and_redirects(self):
        for name in ('../bad.exe','bad\\tool.exe','x:stream','bad.exe.'):
            with self.assertRaises(ValueError):d.validate_asset(dict(asset(),name=name))
        for url in ('http://example.com/a.exe','https://localhost/a.exe','https://127.0.0.1/a.exe','https://u:p@example.com/a.exe'):
            with self.assertRaises(ValueError):d.validate_asset(dict(asset(),url=url))
        self.assertFalse(d.allowed_download(asset(),'https://attacker.invalid/a.exe'))
        self.assertTrue(d.allowed_download(dict(asset(),url='https://downloads.sourceforge.net/project/a/b.iso'),'https://netix.dl.sourceforge.net/project/a/b.iso'))

    def test_bulk_continues_after_failure_and_skips_present(self):
        tools=[{'id':id,'name':id,'officialDownload':'https://example.com','kind':'Installer','license':'Free','localFolder':'tools/'+id} for id in ('a','b','c')]
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'assets/js').mkdir(parents=True)
            (root/'assets/toolkit-manifest.json').write_text(json.dumps(tools));(root/'assets/js/local-inventory.js').write_text('window.LOCAL_INVENTORY = '+json.dumps({'tools':{'a':{'downloaded':True}}})+';')
            def save(root,id,*args,**kwargs):
                if id=='b':raise ValueError('Checksum mismatch')
                return 'Saved: tool'
            with patch.object(d,'options',return_value={'assets':[asset()]}),patch.object(d,'save_selected',side_effect=save) as saved:
                result=d.bulk_download(root,{'mode':'missing'},launcher.safe_path,lambda _:None,lambda:None,lambda:None)
            self.assertIn('1 failed',result);self.assertIn('1 already present',result)
            self.assertEqual([c.args[1] for c in saved.call_args_list],['b','c'])

    def test_monitor_preserves_last_good_and_no_duplicate_change(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'assets').mkdir();(root/'assets/toolkit-manifest.json').write_text(json.dumps([{'id':'test','name':'Test','officialDownload':'https://example.com','kind':'Installer','license':'Free'}]));(root/'assets/download-sources.json').write_text('{"test":{"provider":"github","repo":"org/test"}}')
            with patch.object(monitor,'ROOT',root),patch.object(monitor,'probe'),patch.object(d,'options',return_value={'version':'1','assets':[asset()]}):
                first,changes=monitor.generate({});second,unchanged=monitor.generate(first)
            self.assertTrue(changes);self.assertEqual(unchanged,[]);self.assertEqual(first['revision'],second['revision'])
            with patch.object(monitor,'ROOT',root),patch.object(d,'options',side_effect=ValueError('Publisher down')):
                failed,changes=monitor.generate(second)
            self.assertEqual(failed['tools']['test']['assets'],first['tools']['test']['assets']);self.assertEqual(changes[0]['kind'],'source-error')

    def test_changed_same_filename_keeps_previous(self):
        old=b'old';new=b'new';sha=launcher.digest(new);a=dict(asset(),digest='sha256:'+sha)
        class Response(io.BytesIO):url=a['url']
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'tools').mkdir();(root/'tools'/a['name']).write_bytes(old)
            info={'folder':'tools','version':'2','assets':[a]}
            with patch.object(d,'options',return_value=info),patch.object(d,'open_package',return_value=Response(new)):
                d.save_selected(root,'test',['a'],launcher.safe_path,lambda _:None)
            self.assertEqual((root/'tools'/a['name']).read_bytes(),old)
            receipts=json.loads((root/'assets/download-receipts.json').read_text())['test']
            self.assertEqual(receipts[0]['sha256'],sha);self.assertEqual((root/receipts[0]['path']).read_bytes(),new)

if __name__=='__main__':unittest.main()
