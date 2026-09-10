import hashlib,io,json,os,sys,tarfile,tempfile,unittest,zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]/'MASTER-IT-TOOLKIT';sys.path.insert(0,str(ROOT))
import portable_ai as ai

class PortableAITests(unittest.TestCase):
 def test_download_bad_checksum_preserves_old_file_and_cleans_partial(self):
  with tempfile.TemporaryDirectory() as tmp:
   target=Path(tmp)/'model';target.write_bytes(b'old')
   artifact={'name':'test','url':'https://publisher.example/model','size':3,'sha256':hashlib.sha256(b'new').hexdigest()}
   with patch.object(ai.urllib.request,'build_opener',return_value=SimpleNamespace(open=lambda *a,**k:io.BytesIO(b'bad'))):
    with self.assertRaisesRegex(ValueError,'checksum'):ai.download(artifact,target,lambda _:None,lambda:False)
   self.assertEqual(target.read_bytes(),b'old');self.assertEqual([p.name for p in Path(tmp).iterdir()],['model'])
 def test_download_cancel_does_not_publish_partial(self):
  with tempfile.TemporaryDirectory() as tmp:
   target=Path(tmp)/'model';artifact={'name':'test','url':'https://publisher.example/model','size':3,'sha256':hashlib.sha256(b'new').hexdigest()}
   with patch.object(ai.urllib.request,'build_opener',return_value=SimpleNamespace(open=lambda *a,**k:io.BytesIO(b'new'))):
    with self.assertRaises(InterruptedError):ai.download(artifact,target,lambda _:None,lambda:True)
   self.assertEqual(list(Path(tmp).iterdir()),[])
 def test_archive_traversal_and_case_collisions_rejected(self):
  for names in [['../outside'],['server','SERVER']]:
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);output=root/'ready';output.mkdir();archive=root/'runtime.zip'
    with zipfile.ZipFile(archive,'w') as z:
     for name in names:z.writestr(name,b'fixture')
    with self.assertRaises(ValueError):ai.extract(archive,output)
    self.assertFalse((root/'outside').exists())
 def test_tar_internal_library_links_are_regular_copies(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);output=root/'ready';output.mkdir();archive=root/'runtime.tar.gz'
   with tarfile.open(archive,'w:gz') as t:
    info=tarfile.TarInfo('lib/runtime.so.1');info.size=3;t.addfile(info,io.BytesIO(b'lib'))
    link=tarfile.TarInfo('lib/runtime.so');link.type=tarfile.SYMTYPE;link.linkname='runtime.so.1';t.addfile(link)
   ai.extract(archive,output);self.assertEqual((output/'lib/runtime.so').read_bytes(),b'lib');self.assertFalse((output/'lib/runtime.so').is_symlink())
 def test_no_insecure_redirects(self):
  with self.assertRaises(ValueError):ai.HTTPSOnly().redirect_request(None,None,302,'',{},'http://example.com')
  with self.assertRaises(ValueError):ai.NoRedirect().redirect_request(None,None,302,'',{},'https://example.com')
 @unittest.skipUnless(os.environ.get('PORTABLE_AI_TEST_ROOT'),'Requires prepared runtime/model')
 def test_real_model_loopback_answer(self):
  answer=ai.chat(Path(os.environ['PORTABLE_AI_TEST_ROOT']),[{'role':'user','content':'Reply with just the word READY.'}])
  self.assertIn('READY',answer.upper());self.assertFalse(ai.PROCESSES)

if __name__=='__main__':unittest.main()
