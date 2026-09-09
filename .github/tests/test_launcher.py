import importlib.util
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2] / 'MASTER-IT-TOOLKIT'
spec = importlib.util.spec_from_file_location('launcher', ROOT / 'launcher.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)

def archive(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as z:
        for name, body in files.items(): z.writestr('MASTER-IT-TOOLKIT/' + name, body)
        z.writestr('MASTER-IT-TOOLKIT/' + launcher.MANIFEST, json.dumps({n: launcher.digest(b) for n,b in files.items()}))
    return output.getvalue()

class UpdateTests(unittest.TestCase):
    def test_shipped_archive_is_complete_and_repeatable(self):
        blob = (ROOT.parent / 'MASTER-IT-TOOLKIT.zip').read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            with zipfile.ZipFile(io.BytesIO(blob)) as z: z.extractall(temporary)
            self.assertEqual(launcher.install_archive(blob, Path(temporary) / 'MASTER-IT-TOOLKIT'), 'Already up to date.')
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'assets').mkdir()
        (self.root / 'index.html').write_bytes(b'old')
        (self.root / launcher.MANIFEST).write_text(json.dumps({'index.html': launcher.digest(b'old')}))
    def tearDown(self): self.temp.cleanup()
    def test_update_backup_and_private_data(self):
        (self.root / 'customer.txt').write_bytes(b'private')
        result = launcher.install_archive(archive({'index.html': b'new'}), self.root)
        self.assertIn('Updated', result)
        self.assertEqual((self.root / 'index.html').read_bytes(), b'new')
        self.assertEqual((self.root / 'customer.txt').read_bytes(), b'private')
        self.assertEqual(next((self.root / '.toolkit-backups').glob('*/index.html')).read_bytes(), b'old')
    def test_local_edits_stop_update(self):
        (self.root / 'index.html').write_bytes(b'my edits')
        with self.assertRaisesRegex(ValueError, 'Local changes'): launcher.install_archive(archive({'index.html': b'new'}), self.root)
        self.assertEqual((self.root / 'index.html').read_bytes(), b'my edits')
    def test_traversal_and_inventory_rejected(self):
        for name in ('../outside', '/outside', 'C:/outside', 'assets/js/local-inventory.js'):
            with self.assertRaises(ValueError): launcher.install_archive(archive({name: b'bad'}), self.root)
    def test_checksum_rejected(self):
        data = io.BytesIO(archive({'index.html': b'new'}))
        with zipfile.ZipFile(data, 'a') as z: z.writestr('MASTER-IT-TOOLKIT/index.html', b'tampered')
        with self.assertRaises(ValueError): launcher.install_archive(data.getvalue(), self.root)
    def test_failed_write_rolls_back(self):
        original = Path.write_bytes
        fired = False
        def write(path, data):
            nonlocal fired
            if path == self.root / 'index.html' and data == b'new' and not fired:
                fired = True
                raise OSError('simulated disk error')
            return original(path, data)
        with patch.object(Path, 'write_bytes', write):
            with self.assertRaises(OSError): launcher.install_archive(archive({'index.html': b'new'}), self.root)
        self.assertEqual((self.root / 'index.html').read_bytes(), b'old')
    def test_symlink_rejected(self):
        target = self.root / 'real'; target.mkdir()
        try: (self.root / 'link').symlink_to(target, target_is_directory=True)
        except OSError: self.skipTest('No symlink permission')
        with self.assertRaises(ValueError): launcher.safe_path(self.root, 'link/file')

class ServerTests(unittest.TestCase):
    def setUp(self):
        self.server = launcher.Server(ROOT, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.base = self.server.origin + '/' + self.server.token + '/'
    def tearDown(self): self.server.shutdown(); self.server.server_close(); self.thread.join()
    def request(self, path, body=None, origin=None):
        headers = {'Origin': origin} if origin else {}
        r = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body else None, headers=headers)
        return urllib.request.urlopen(r)
    def test_session_and_private_files(self):
        with self.request('index.html') as r:
            self.assertIn(b'launcher-client.js', r.read())
            self.assertEqual(r.headers['Referrer-Policy'], 'no-referrer')
        for path in ('../launcher.py', '70_DOCUMENTATION/Service-Notes/README.txt', '60_SCRIPTS/Diagnostics/Get-PCDiagnostics.ps1'):
            with self.assertRaises(urllib.error.HTTPError): self.request(path)
        with self.assertRaises(urllib.error.HTTPError): urllib.request.urlopen(self.server.origin + '/api/status')
    def test_external_origin_and_unknown_action_rejected(self):
        for action, origin in [('inventory', 'https://example.com'), ('cmd /c anything', self.server.origin)]:
            with self.assertRaises(urllib.error.HTTPError): self.request('api/action', {'action': action, 'confirmed': True}, origin)
    def test_approved_action_and_busy_lock(self):
        gate = threading.Event()
        with patch.object(launcher, 'run_script', side_effect=lambda key: gate.wait(3) or 'done'):
            with self.request('api/action', {'action':'inventory','confirmed':True}, self.server.origin) as r: self.assertEqual(r.status, 202)
            with self.assertRaises(urllib.error.HTTPError) as error: self.request('api/action', {'action':'inventory','confirmed':True}, self.server.origin)
            self.assertEqual(error.exception.code, 409)
            gate.set()

if __name__ == '__main__': unittest.main()
