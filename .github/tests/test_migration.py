import sys,tempfile,unittest,os,errno
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]/'MASTER-IT-TOOLKIT';sys.path.insert(0,str(ROOT))
import migration_tools as m

class MigrationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.source=self.base/'source';self.dest=self.base/'destination';self.source.mkdir();self.dest.mkdir()
  (self.source/'a.txt').write_bytes(b'one');(self.source/'b.txt').write_bytes(b'two');self.job='a'*24
 def tearDown(self):self.tmp.cleanup()
 def plan(self):return m.plan(str(self.source),str(self.dest),self.job)
 def test_verified_copy_repeat_and_existing_files_preserved(self):
  (self.dest/'existing.txt').write_text('untouched')
  result=m.copy(self.plan(),lambda _:None);output=Path(result['output'])
  self.assertEqual(result['copied'],2);self.assertEqual((output/'a.txt').read_bytes(),b'one')
  self.assertEqual((self.source/'b.txt').read_bytes(),b'two');self.assertEqual((self.dest/'existing.txt').read_text(),'untouched')
  repeat=m.copy(self.plan(),lambda _:None);self.assertEqual(repeat['reused'],2);self.assertEqual(repeat['copied'],0)
  (output/'a.txt').write_bytes(b'bad')
  with self.assertRaisesRegex(ValueError,'differs'):m.copy(self.plan(),lambda _:None)
  self.assertEqual((output/'a.txt').read_bytes(),b'bad')
 def test_source_changes_after_review_write_nothing(self):
  plan=self.plan();(self.source/'c.txt').write_bytes(b'new')
  with self.assertRaisesRegex(ValueError,'changed'):m.copy(plan,lambda _:None)
  self.assertEqual(list(self.dest.iterdir()),[])
 def test_interrupted_copy_resumes_verified_files(self):
  calls=[0]
  def cancel():calls[0]+=1;return calls[0]>=5
  with self.assertRaises(InterruptedError):m.copy(self.plan(),lambda _:None,cancel)
  output=self.dest/('Master-IT-Migration-'+self.job)
  self.assertFalse(list(output.glob('partial-*')));self.assertTrue((output/'data/a.txt').exists())
  result=m.copy(self.plan(),lambda _:None);self.assertEqual(result['reused'],1);self.assertEqual(result['copied'],1)
 def test_verification_failure_does_not_publish(self):
  original=m.digest
  def wrong(path):return 'bad' if path.name.startswith('partial-') else original(path)
  with patch.object(m,'digest',side_effect=wrong):
   with self.assertRaisesRegex(ValueError,'verification'):m.copy(self.plan(),lambda _:None)
  self.assertFalse(list(self.dest.rglob('a.txt')));self.assertFalse(list(self.dest.rglob('partial-*')))
 def test_overlaps_and_invalid_job_rejected(self):
  for src,dst,job in [(self.source,self.source,self.job),(self.base,self.dest,self.job),(self.source,self.dest,'../escape')]:
   with self.assertRaises(ValueError):m.plan(str(src),str(dst),job)
 def test_links_not_copied(self):
  try:(self.source/'link.txt').symlink_to(self.source/'a.txt')
  except OSError:self.skipTest('Symlink creation unavailable')
  p=self.plan();self.assertEqual(p['skipped'],['link.txt']);result=m.copy(p,lambda _:None)
  self.assertFalse((Path(result['output'])/'link.txt').exists());self.assertEqual(result['skipped'],1)
 @unittest.skipIf(os.name=='nt','POSIX fallback')
 def test_exclusive_rename_fallback_never_overwrites(self):
  a=self.base/'temporary';b=self.base/'published';a.write_bytes(b'new')
  with patch.object(m.os,'link',side_effect=OSError(errno.EPERM,'not supported')):m.publish_file(a,b)
  a.write_bytes(b'other')
  with patch.object(m.os,'link',side_effect=OSError(errno.EPERM,'not supported')):
   with self.assertRaises(OSError):m.publish_file(a,b)
  self.assertEqual(b.read_bytes(),b'new');self.assertEqual(a.read_bytes(),b'other')

if __name__=='__main__':unittest.main()
