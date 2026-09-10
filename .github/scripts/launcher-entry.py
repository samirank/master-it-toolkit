"""Frozen bootstrap: updated source is loaded on restart, without replacing the EXE."""
import launcher  # Included so PyInstaller collects its standard-library dependencies.
import runpy
import argparse
import datetime
import fnmatch
import tempfile
import sys
import sqlite3
import playwright.async_api  # Collect browser driver dependencies in the frozen runtime.
from pathlib import Path

root = Path(sys.executable).resolve().parent
if (root / 'MASTER-IT-TOOLKIT' / 'launcher.py').is_file(): root = root / 'MASTER-IT-TOOLKIT'
sys.path.insert(0, str(root))
if '--browser-self-test' in sys.argv:
    import asyncio
    import os
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(root / 'runtime-browser')
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
    print('Master IT Toolkit standalone runtime ready.')
elif '--inventory' in sys.argv:
    script = root / '60_SCRIPTS/Inventory/update_toolkit_inventory.py'
    sys.argv = [str(script), *sys.argv[sys.argv.index('--inventory')+1:]]
    runpy.run_path(str(script), run_name='__main__')
else:
    runpy.run_path(str(root / 'launcher.py'), run_name='__main__')
