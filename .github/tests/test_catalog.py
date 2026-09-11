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
    def test_probe_matches_download_and_pins_blender_selected_mirror(self):
        from unittest.mock import Mock
        item=asset(arch='arm64');item.update(url='https://mirror.blender.org/release/Blender5.2/blender-5.2.1-windows-arm64.msi',digest='sha256:'+'a'*64)
        response=io.BytesIO(b'package');response.headers={'Content-Type':'application/octet-stream'}
        response.url='https://mirror.fcix.net/blender/release/Blender5.2/blender-5.2.1-windows-arm64.msi'
        opener=Mock();opener.open.return_value=response
        with patch.object(monitor.urllib.request,'build_opener',return_value=opener):monitor.probe({'assets':[item]})
        self.assertFalse(opener.open.call_args.args[0].has_header('Range'))
        self.assertEqual(item['url'],response.url)
        self.assertEqual(item['digest'],'sha256:'+'a'*64)

    def test_blender_official_mirror_retains_release_and_checksum(self):
        from types import SimpleNamespace
        original='https://download.blender.org/release/Blender5.2/blender-5.2.1-windows-x64.msi'
        def resolve(package,url):
            manifest={'PackageVersion':'5.2.1','Installers':[{'InstallerUrl':url,'InstallerSha256':'A'*64,'Architecture':'x64'}]}
            with patch.dict(sys.modules,{'yaml':SimpleNamespace(safe_load=json.loads)}),patch.object(d,'fetch_json',return_value=[{'name':'5.2.1','type':'dir'}]),patch.object(d,'fetch_bytes',return_value=json.dumps(manifest).encode()):
                return monitor.winget({'package':package})['assets'][0]
        result=resolve('BlenderFoundation.Blender',original)
        self.assertEqual(result['url'],original.replace('download.blender.org','mirror.blender.org'))
        self.assertEqual(result['digest'],'sha256:'+'a'*64)
        for package,url in [('Other.Package',original),('BlenderFoundation.Blender',original.replace('download.blender.org','download.blender.org.example.com')),('BlenderFoundation.Blender',original+'?redirect=other')]:
            self.assertEqual(resolve(package,url)['url'],url)

    def notify_fixture(self,issues,tools):
        with tempfile.TemporaryDirectory() as tmp,patch.dict(monitor.os.environ,{'GITHUB_REPOSITORY':'owner/toolkit','RUNNER_TEMP':tmp}),patch.object(monitor.subprocess,'check_output',return_value=json.dumps(issues)),patch.object(monitor.subprocess,'run') as run:
            monitor.notify({'tools':tools})
            body=(Path(tmp)/'catalog-health.md').read_text(encoding='utf-8')
            return [call.args[0] for call in run.call_args_list],body

    def issue_fixture(self,number,tracker=False,state='OPEN'):
        return dict(number=number,title=monitor.ISSUE_TITLE if tracker else 'Download catalog '+'a'*20+': 1 changes',body=monitor.ISSUE_MARKER if tracker else 'The download catalog was refreshed. Downloads still come from the original publishers.',state=state,author={'is_bot':True,'login':'app/github-actions'})

    def test_notifications_consolidate_without_closing_human_issues(self):
        old=self.issue_fixture(1);new=self.issue_fixture(2);human=self.issue_fixture(3);human['author']={'is_bot':False,'login':'owner'}
        calls,body=self.notify_fixture([old,new,human],{'broken':{'name':'Tool','status':'error','error':'404'}})
        self.assertIn('404',body);self.assertEqual(calls[0][2:4],['edit','2'])
        self.assertEqual([c[3] for c in calls if c[2]=='close'],['1']);self.assertFalse(any(c[2]=='create' for c in calls))

    def test_notifications_close_recovered_tracker_even_without_changes(self):
        calls,body=self.notify_fixture([self.issue_fixture(1,True)],{'healthy':{'status':'ready'}})
        self.assertIn('No action is needed',body);self.assertTrue(any(c[2:4]==['close','1'] for c in calls))
        calls,_=self.notify_fixture([],{'healthy':{'status':'ready'}});self.assertEqual(calls,[])

    def test_notifications_reopen_and_ignore_unchanged_failure(self):
        problem={'tool':{'status':'error','name':'Tool','error':'offline'}}
        issue=self.issue_fixture(1,True,'CLOSED');calls,body=self.notify_fixture([issue],problem)
        self.assertTrue(any(c[2:4]==['reopen','1'] for c in calls))
        issue.update(state='OPEN',body=body);calls,_=self.notify_fixture([issue],problem);self.assertEqual(calls,[])

    def test_notifications_failed_replacement_keeps_originals(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict(monitor.os.environ,{'GITHUB_REPOSITORY':'owner/toolkit','RUNNER_TEMP':tmp}),patch.object(monitor.subprocess,'check_output',return_value=json.dumps([self.issue_fixture(1),self.issue_fixture(2)])),patch.object(monitor.subprocess,'run',side_effect=RuntimeError('GitHub unavailable')) as run:
            with self.assertRaises(RuntimeError):monitor.notify({'tools':{'broken':{'status':'error'}}})
            self.assertEqual(run.call_count,1);self.assertEqual(run.call_args.args[0][2],'edit')

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

    def test_sourceforge_rotating_mirrors_remain_scoped(self):
        for origin in ('sourceforge.net/projects/crystaldiskinfo/files/file.exe','downloads.sourceforge.net/project/crystaldiskinfo/file.zip'):
            a=dict(asset(),url='https://'+origin)
            self.assertTrue(d.allowed_download(a,'https://new-mirror.dl.sourceforge.net/project/crystaldiskinfo/file.zip'))
            for url in ('http://new-mirror.dl.sourceforge.net/a','https://new-mirror.dl.sourceforge.net.evil.example/a','https://evilsourceforge.net/a','https://sourceforge.net@evil.example/a','https://mirror.dl.sourceforge.net:444/a'):
                self.assertFalse(d.allowed_download(a,url))
        self.assertFalse(d.allowed_download(asset(),'https://new-mirror.dl.sourceforge.net/a'))

    def test_crystaldiskinfo_feed_selects_standard_portable_zip(self):
        names=['9.9.3/CrystalDiskInfo9_9_3Ads.exe','9.9.3/CrystalDiskInfo9_9_3Shizuku.zip','9.9.3/CrystalDiskInfo9_9_3.zip','9.9.2/CrystalDiskInfo9_9_2.zip','10.0rc1/CrystalDiskInfo10_0.zip']
        xml=('<rss><channel>'+''.join('<item><link>https://sourceforge.net/projects/crystaldiskinfo/files/'+n+'/download</link></item>' for n in names)+'</channel></rss>').encode()
        with patch.object(d,'fetch_bytes',return_value=xml):info=d.sourceforge(d.sources(ROOT/'MASTER-IT-TOOLKIT')['cdi'])
        self.assertEqual(info['version'],'9.9.3');self.assertEqual([a['name'] for a in info['assets']],['CrystalDiskInfo9_9_3.zip']);self.assertEqual(info['assets'][0]['platform'],'Windows')

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

    def test_bulk_selection_is_scoped_and_empty_selection_cannot_download_all(self):
        tools=[{'id':id,'name':id,'officialDownload':'https://example.com','kind':'Installer','license':'Free','localFolder':'tools/'+id} for id in ('a','b')]
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'assets/js').mkdir(parents=True)
            (root/'assets/toolkit-manifest.json').write_text(json.dumps(tools))
            (root/'assets/js/local-inventory.js').write_text('window.LOCAL_INVENTORY = {"tools":{}};')
            with patch.object(d,'options',return_value={'assets':[asset()]}),patch.object(d,'save_selected',return_value='Saved') as saved:
                d.bulk_download(root,{'mode':'missing','tools':['b']},launcher.safe_path,lambda _:None,lambda:None,lambda:None)
                self.assertEqual([call.args[1] for call in saved.call_args_list],['b'])
                for selected in ([],['unknown'],'a'):
                    with self.assertRaises(ValueError):
                        d.bulk_download(root,{'tools':selected},launcher.safe_path,lambda _:None,lambda:None,lambda:None)
                self.assertEqual(saved.call_count,1)

    def test_queue_filters_intersect_before_downloading(self):
        tools=[{'id':id,'name':id,'officialDownload':'https://example.com','kind':'Installer','license':'Free','priority':priority,'categories':[category]} for id,priority,category in [('a','P1','Network'),('b','P2','Network'),('c','P1','Disk')]]
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'assets/js').mkdir(parents=True)
            (root/'assets/toolkit-manifest.json').write_text(json.dumps(tools))
            (root/'assets/js/local-inventory.js').write_text('window.LOCAL_INVENTORY = {"tools":{}};')
            with patch.object(d,'options',return_value={'assets':[asset()]}),patch.object(d,'save_selected',return_value='Saved') as saved:
                selection={'filters':{'priority':'P1','category':'Network','kind':'Installer','license':'Free'}}
                d.bulk_download(root,selection,launcher.safe_path,lambda _:None,lambda:None,lambda:None)
                self.assertEqual([call.args[1] for call in saved.call_args_list],['a'])
                saved.reset_mock()
                d.bulk_download(root,{**selection,'tools':['b']},launcher.safe_path,lambda _:None,lambda:None,lambda:None)
                saved.assert_not_called()
                with self.assertRaises(ValueError):
                    d.bulk_download(root,{'filters':{'priority':'invalid'}},launcher.safe_path,lambda _:None,lambda:None,lambda:None)

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
