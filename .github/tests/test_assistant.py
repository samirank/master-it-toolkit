import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]/'MASTER-IT-TOOLKIT'
sys.path.insert(0,str(ROOT))
import offline_assistant as ai
import activity_store
import launcher

class AssistantTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  self.store=activity_store.Store(self.root,launcher.safe_path)
 def tearDown(self): self.temp.cleanup()
 def test_catalog_and_persistence(self):
  with patch.object(ai,'local_api',side_effect=AssertionError('Catalog mode must not use network')):
   result=ai.handle(ROOT,self.store,dict(message='LocalWP WordPress',mode='catalog'))
  self.assertIn('localwp',[m['id'] for m in result['matches']])
  again=activity_store.Store(self.root,launcher.safe_path)
  self.assertEqual(len(ai.history(again)),2)
  ai.handle(ROOT,again,dict(operation='clear'));self.assertEqual(ai.history(again),[])
 def test_ai_grounded_and_no_execution(self):
  calls=[]
  def local(path,body=None,**kw):
   calls.append((path,body))
   if path=='tags':return {'models':[{'name':ai.MODEL}]}
   return {'message':{'content':'<script>bad()</script> Use LocalWP.'},'tool_calls':[{'command':'erase everything'}]}
  with patch.object(ai,'local_api',side_effect=local):
   result=ai.handle(ROOT,self.store,dict(message='WordPress',mode='ai'))
  self.assertEqual(result['mode'],'ai');self.assertNotIn('tool_calls',result)
  self.assertIn('localwp',calls[-1][1]['messages'][0]['content'])
  self.assertNotIn('tools',calls[-1][1])
 def test_offline_failure_and_validation(self):
  with patch.object(ai,'local_api',side_effect=OSError('offline')):
   result=ai.handle(ROOT,self.store,dict(message='wifi internet',mode='ai'))
  self.assertEqual(result['mode'],'catalog');self.assertTrue(result['warning'])
  for body in [[],{'message':'x'*4001,'mode':'ai'},{'operation':'exec','command':'anything'}]:
   with self.assertRaises(ValueError):ai.handle(ROOT,self.store,body)
 def test_cloud_models_and_busy(self):
  with patch.object(ai,'local_api',return_value={'models':[{'name':ai.MODEL,'remote_host':'cloud'}]}):self.assertFalse(ai.ready())
  ai.LOCK.acquire()
  try:
   with self.assertRaises(ValueError):ai.handle(ROOT,self.store,{'operation':'clear'})
  finally:ai.LOCK.release()
 def test_http_session_and_origin(self):
  import threading
  import urllib.request
  import urllib.error
  server=launcher.Server(root=self.root,port=0)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   for prefix,origin,code in [(server.token,'https://example.com',403),('wrong',server.origin,403),(server.token,server.origin,200)]:
    request=urllib.request.Request(server.origin+'/'+prefix+'/api/assistant',data=b'{"operation":"clear"}',headers={'Origin':origin,'Content-Type':'application/json'})
    try:
     with urllib.request.urlopen(request) as response:self.assertEqual(response.status,code)
    except urllib.error.HTTPError as error:self.assertEqual(error.code,code)
  finally:server.shutdown();server.server_close();thread.join()
 def test_redirect_rejected(self):
  with self.assertRaises(ValueError):ai.NoRedirect().redirect_request(None,None,302,'',{},'https://example.com')

if __name__=='__main__':unittest.main()
