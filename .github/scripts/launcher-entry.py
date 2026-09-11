"""Frozen bootstrap: updated source is loaded on restart, without replacing the EXE."""
import launcher  # Included so PyInstaller collects its standard-library dependencies.
import runpy
import argparse
import datetime
import fnmatch
import tempfile
import sys
import cryptography.hazmat.primitives.ciphers.aead
import cryptography.hazmat.primitives.kdf.scrypt
import sqlite3
import platform_runtime
import trusted_computers
if sys.platform == 'win32':
    import keyring.backends.Windows
elif sys.platform == 'darwin':
    import keyring.backends.macOS
else:
    import keyring.backends.SecretService
import playwright.async_api  # Collect browser driver dependencies in the frozen runtime.
from pathlib import Path

root = platform_runtime.toolkit_root(sys.executable) if not any(arg in sys.argv for arg in ('--self-test','--credential-self-test')) else Path(sys.executable).resolve().parent
sys.path.insert(0, str(root))
if '--credential-self-test' in sys.argv:
    import secrets
    store = trusted_computers.backend()
    account = 'build-test-' + secrets.token_hex(16)
    secret = secrets.token_urlsafe(32)
    try:
        store.set_password(trusted_computers.SERVICE, account, secret)
        assert store.get_password(trusted_computers.SERVICE, account) == secret
    finally:
        store.delete_password(trusted_computers.SERVICE, account)
    print('Native credential store ready; temporary test credential removed.')
elif '--browser-self-test' in sys.argv:
    import asyncio
    import os
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(platform_runtime.browser_path(root))
    async def test_browser():
        async with playwright.async_api.async_playwright() as p:
            browser = await p.chromium.launch(headless=True, channel='chromium')
            page = await browser.new_page()
            await page.set_content('<title>Toolkit browser ready</title>')
            assert await page.title() == 'Toolkit browser ready'
            await browser.close()
    asyncio.run(test_browser())
    print('Bundled browser runtime ready.')
elif '--self-test' in sys.argv:
    import os
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    cipher=AESGCM(os.urandom(32));nonce=os.urandom(12)
    assert cipher.decrypt(nonce,cipher.encrypt(nonce,b'vault runtime check',b'test'),b'test')==b'vault runtime check'
    print('Master IT Toolkit standalone runtime ready.')
elif '--inventory' in sys.argv:
    script = root / '60_SCRIPTS/Inventory/update_toolkit_inventory.py'
    sys.argv = [str(script), *sys.argv[sys.argv.index('--inventory')+1:]]
    runpy.run_path(str(script), run_name='__main__')
else:
    runpy.run_path(str(root / 'launcher.py'), run_name='__main__')
