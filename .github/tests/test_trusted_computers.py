import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'MASTER-IT-TOOLKIT'))
import activity_store
import launcher
import secure_vault as v
import trusted_computers as t

class MemoryKeyring:
    def __init__(self): self.values = {}
    def set_password(self, service, account, value): self.values[service, account] = value
    def get_password(self, service, account): return self.values.get((service, account))
    def delete_password(self, service, account): self.values.pop((service, account), None)


class TrustedComputerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = activity_store.Store(self.root, launcher.safe_path)
        self.store.workspace('notes', {'issue': 'private customer issue'})
        self.path = self.store.path
        self.password = 'test-only vault passphrase'
        self.recovery = v.setup(self.path, self.password)
        self.keyring = MemoryKeyring()
        self.backend = patch.object(t, 'backend', return_value=self.keyring).start()
        self.host = patch.object(t.host_inventory, 'host_id', return_value='machine-a').start()
        self.addCleanup(patch.stopall)

    def tearDown(self):
        v.lock(self.path)
        self.tmp.cleanup()

    def test_multiple_masters_moved_drive_and_foreign_account(self):
        t.enroll(self.path, self.password, name='Private master name')
        self.assertNotIn(b'Private master name', self.path.read_bytes())
        self.assertNotIn(b'private customer issue', self.path.read_bytes())
        self.assertNotIn(v.KEYS[str(self.path.resolve())], self.path.read_bytes())
        local_key = next(iter(self.keyring.values.values())).encode()
        self.assertNotIn(local_key, self.path.read_bytes())
        v.lock(self.path)
        self.host.return_value = 'machine-b'
        self.assertFalse(t.auto_unlock(self.path))
        with self.assertRaises(ValueError): self.store.workspace()
        v.unlock(self.path, self.recovery, True)
        self.assertEqual(self.store.workspace()['notes']['issue'], 'private customer issue')
        t.enroll(self.path, self.recovery, True, 'Second master')
        self.assertEqual(len(t.status(self.path)['masters']), 2)
        v.lock(self.path)
        self.assertTrue(t.auto_unlock(self.path))
        v.lock(self.path)
        self.host.return_value = 'machine-a'
        moved = self.root / 'other-drive' / 'vault.sqlite'
        moved.parent.mkdir(); shutil.copyfile(self.path, moved)
        self.assertTrue(t.auto_unlock(moved))
        self.assertEqual(t.status(moved)['masters'][0]['name'], 'Private master name')
        v.lock(moved)
        # A copied SSD alone does not include any OS credential.
        self.keyring.values.clear()
        self.assertFalse(t.auto_unlock(moved))
        v.unlock(moved, self.password)
        v.lock(moved)

    def test_revoke_remote_master_and_preserve_after_database_write(self):
        t.enroll(self.path, self.password)
        self.store.workspace('notes', {'issue': 'updated'})
        self.host.return_value = 'machine-b'
        t.revoke(self.path, 'machine-a')
        v.lock(self.path); self.host.return_value = 'machine-a'
        self.assertFalse(t.auto_unlock(self.path))
        self.assertTrue(self.keyring.values)  # Remote credential cannot restore revoked grant.
        v.unlock(self.path, self.password)
        self.assertEqual(self.store.workspace()['notes']['issue'], 'updated')

    def test_wrong_password_unavailable_keyring_and_tampering(self):
        with self.assertRaises(ValueError): t.enroll(self.path, 'wrong')
        self.assertFalse(self.keyring.values)
        self.backend.side_effect = ValueError('No native store')
        with self.assertRaises(ValueError): t.enroll(self.path, self.password)
        self.assertFalse(t.status(self.path)['master'])
        self.backend.side_effect = None
        t.enroll(self.path, self.password)
        doc = v.header(self.path)
        doc['masters']['machine-a']['wrapped'] = v.b64(b'corrupted')
        v.atomic(self.path, v.MAGIC + json.dumps(doc).encode())
        v.lock(self.path)
        self.assertFalse(t.auto_unlock(self.path))
        self.assertTrue(v.status(self.path)['locked'])
        v.unlock(self.path, self.password)

    def test_startup_unlock_manual_lock_and_no_private_labels_while_locked(self):
        t.enroll(self.path, self.password)
        v.lock(self.path)
        self.assertEqual(t.status(self.path)['masters'], [])
        server = launcher.Server(self.root, port=0)
        try:
            self.assertFalse(v.status(self.path)['locked'])
            self.assertEqual(server.history.workspace()['notes']['issue'], 'private customer issue')
            v.lock(self.path)
            server.service_actions()
            self.assertTrue(v.status(self.path)['locked'])
        finally: server.server_close()

    def test_failed_credential_write_does_not_enable_grant(self):
        with patch.object(self.keyring, 'set_password', side_effect=RuntimeError('unavailable')):
            with self.assertRaises(ValueError): t.enroll(self.path, self.password)
        self.assertFalse(t.status(self.path)['master'])

if __name__ == '__main__': unittest.main()
