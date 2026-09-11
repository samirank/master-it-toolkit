"""Explicit, revocable vault unlock grants backed by the current OS account's keyring.

Only native credential stores are accepted; never fall back to a plaintext file.
The SSD contains wrapped keys, not the local credential used to unwrap them.
"""
import hashlib
import json
import os
import socket
import sys
import time

import secure_vault as vault
import host_inventory

SERVICE = 'Master IT Toolkit private vault'


def backend():
    try:
        if sys.platform == 'win32':
            from keyring.backends.Windows import WinVaultKeyring
            store = WinVaultKeyring()
            store.persist = 'local machine'  # Do not roam the credential to another PC.
        elif sys.platform == 'darwin':
            from keyring.backends.macOS import Keyring
            store = Keyring()
        elif sys.platform.startswith('linux'):
            from keyring.backends.SecretService import Keyring
            store = Keyring()
        else:
            raise RuntimeError('Unsupported platform')
        if store.priority <= 0:
            raise RuntimeError('Native credential store unavailable')
        return store
    except Exception:
        raise ValueError('Master computer unlock needs the updated standalone launcher and an available OS credential store. Use your vault passphrase here instead.') from None


def identity(doc):
    # Salt identifies the vault across drive letters, mount points and SSD copies.
    return hashlib.sha256(vault.un64(doc['salt'])).hexdigest(), host_inventory.host_id()


def account(doc):
    vault_id, host = identity(doc)
    return vault_id + ':' + host


def aad(doc, host):
    return ('mit-master-v1:' + identity(doc)[0] + ':' + host).encode()


def status(path):
    result = vault.status(path)
    result.update(master=False, masters=[])
    if not result['configured']:
        return result
    with vault.mutex(path):
        doc = vault.header(path)
        host = identity(doc)[1]
        result['master'] = host in doc.get('masters', {})
        key = vault.KEYS.get(str(path.resolve()))
        if key is not None:
            for identifier, record in doc.get('masters', {}).items():
                details = json.loads(vault.open_seal(key, record['details'], aad(doc, identifier)))
                result['masters'].append(dict(id=identifier, current=identifier == host, **details))
    return result


def enroll(path, secret, recovery=False, name=''):
    # Fresh proof is required even in an automatically unlocked session.
    if vault.status(path)['locked']:
        raise ValueError('Unlock the vault before registering a master computer.')
    vault.unlock(path, secret, recovery)
    with vault.mutex(path):
        doc = vault.header(path)
        host = identity(doc)[1]
        masters = doc.setdefault('masters', {})
        if host not in masters and len(masters) >= 20:
            raise ValueError('Remove a master computer before adding another (maximum 20).')
        key = vault.KEYS[str(path.resolve())]
        local_key = os.urandom(32)
        credential = vault.b64(local_key)
        store = backend()
        # A failed enrollment can never leave a new grant enabled on the SSD.
        previous = store.get_password(SERVICE, account(doc))
        try:
            store.set_password(SERVICE, account(doc), credential)
            if store.get_password(SERVICE, account(doc)) != credential:
                raise ValueError('OS credential store did not retain the unlock key')
            label = str(name or socket.gethostname()).strip()[:80]
            masters[host] = {
                'wrapped': vault.seal(local_key, key, aad(doc, host)),
                'details': vault.seal(key, json.dumps(dict(name=label, platform=sys.platform, added=time.time())).encode(), aad(doc, host)),
            }
            vault.atomic(path, vault.MAGIC + json.dumps(doc).encode())
        except Exception:
            try:
                if previous is not None: store.set_password(SERVICE, account(doc), previous)
                else: store.delete_password(SERVICE, account(doc))
            except Exception: pass
            raise ValueError('Could not register this master computer; use the vault passphrase.') from None


def auto_unlock(path):
    """Only called at startup or by an explicit Unlock on this master button."""
    if not vault.status(path)['locked']:
        return False
    with vault.mutex(path):
        try:
            doc = vault.header(path)
            host = identity(doc)[1]
            record = doc.get('masters', {}).get(host)
            if record is None: return False
            credential = backend().get_password(SERVICE, account(doc))
            if not credential: return False
            key = vault.open_seal(vault.un64(credential), record['wrapped'], aad(doc, host))
            vault.open_seal(key, doc['data'], b'mit-sqlite-v1')
            vault.KEYS[str(path.resolve())] = key
            return True
        except Exception:
            # Locked keychains, missing packages and invalid keys fail closed.
            return False


def revoke(path, identifier):
    with vault.mutex(path):
        if vault.status(path)['locked']:
            raise ValueError('Unlock the vault before managing master computers.')
        doc = vault.header(path)
        if not isinstance(identifier, str) or identifier not in doc.get('masters', {}):
            raise ValueError('Unknown master computer')
        del doc['masters'][identifier]
        vault.atomic(path, vault.MAGIC + json.dumps(doc).encode())
        if identifier == identity(doc)[1]:
            try: backend().delete_password(SERVICE, account(doc))
            except Exception: pass  # Removing the SSD grant already revokes access.
