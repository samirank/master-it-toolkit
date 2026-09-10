"""Isolated bundled Chromium windows; downloads never use the user's browser profile."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import threading
import time

EXTENSIONS = {'.exe','.msi','.msix','.zip','.7z','.gz','.xz','.bz2','.dmg','.pkg','.deb','.rpm','.appimage','.iso'}


def destination(root, tool_id, filename, safe_path):
    if not filename or Path(filename).name != filename or '/' in filename or '\\' in filename or ':' in filename or filename.endswith(('.', ' ')):
        raise ValueError('Invalid download filename')
    if re.match(r'^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)', filename, re.I): raise ValueError('Reserved filename')
    if tool_id:
        catalog = json.loads((root/'assets/toolkit-manifest.json').read_text('utf-8'))
        tool = next((t for t in catalog if t['id'] == tool_id), None)
        if not tool or not tool.get('localFolder'): raise ValueError('Unknown tool destination')
        folder = safe_path(root, tool['localFolder'])
        if Path(filename).suffix.lower() not in EXTENSIONS: raise ValueError('Unsupported package type; no file was imported')
    else:
        folder = safe_path(root, '70_DOCUMENTATION/Service-Notes/Exports')
        if Path(filename).suffix.lower() not in ('.json','.txt','.csv'): raise ValueError('Use the tool download manager for software packages')
    folder.mkdir(parents=True, exist_ok=True)
    path = safe_path(root, (folder/filename).relative_to(root).as_posix())
    if path.exists(): raise ValueError('A file with this name already exists; it was preserved. Review it in Manage files.')
    return path


class Host:
    def __init__(self, server, safe_path, scan):
        self.server, self.root, self.safe_path, self.scan = server, server.root, safe_path, scan
        self.stop = threading.Event()
        self.windows = set()
        self.lock = threading.Lock()
        self.notice = None

    def available(self):
        try: return importlib.util.find_spec('playwright.async_api') is not None
        except (ImportError, ValueError): return False

    def open(self, url, tool_id=None):
        if not self.available(): raise ValueError('Managed browser requires the new standalone package. Existing browser downloads are not redirected; use direct downloads or Import file until then.')
        key = tool_id or '_dashboard'
        with self.lock:
            if key in self.windows: raise ValueError('This browser window is already open. Close it before reopening.')
            if len(self.windows) >= 5: raise ValueError('Close a publisher window before opening another')
            self.windows.add(key)
        threading.Thread(target=self.worker, args=(url, tool_id, key), daemon=True).start()

    def worker(self, url, tool_id, key):
        try: asyncio.run(self.window(url, tool_id))
        except Exception as error:
            state = dict(busy=False, tool=tool_id, stage='error', message='Browser stopped: ' + str(error))
            self.server.history.record('browser', state)
            self.notice = state
            if not self.server.state.get('busy'): self.server.state = state
        finally:
            with self.lock: self.windows.discard(key)

    async def window(self, url, tool_id):
        bundled = self.root/'runtime-browser'
        if bundled.is_dir(): os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(bundled)
        from playwright.async_api import async_playwright
        temp_root = self.safe_path(self.root, '90_TEMP/browser-sessions')
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='session-', dir=temp_root) as temporary:
            stage = Path(temporary)/'transfers'; stage.mkdir()
            profile = Path(temporary)/'profile'
            if tool_id is None:
                import host_inventory
                profile = self.safe_path(self.root, '70_DOCUMENTATION/Service-Notes/BrowserProfile/'+host_inventory.host_id())
                profile.mkdir(parents=True, exist_ok=True)
            async with async_playwright() as engine:
                context = await engine.chromium.launch_persistent_context(str(profile), channel='chromium',
                    headless=os.environ.get('TOOLKIT_BROWSER_TEST_HEADLESS') == '1', accept_downloads=True,
                    downloads_path=str(stage), no_viewport=True, args=['--app=about:blank','--window-size=1280,860'])
                tasks = set()
                def downloaded(download):
                    task = asyncio.create_task(self.save(download, tool_id, stage)); tasks.add(task); task.add_done_callback(tasks.discard)
                def attach(page): page.on('download', downloaded)
                context.on('page', attach)
                for page in context.pages: attach(page)
                page = context.pages[0] if context.pages else await context.new_page()
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                except Exception:
                    if not tasks: raise
                try:
                    while context.pages and not self.stop.is_set(): await asyncio.sleep(.25)
                finally:
                    await context.close()
                    if tasks: await asyncio.gather(*tasks, return_exceptions=True)

    async def save(self, download, tool_id, stage):
        server = self.server
        if not server.lock.acquire(False):
            await download.cancel()
            self.notice = {'tool':tool_id, 'stage':'error','message':'Download cancelled because another toolkit job is active. Retry after that job finishes.'}
            server.history.record('vendor-download', self.notice)
            return
        started = time.time()
        temporary = None
        state = dict(busy=True, tool=tool_id, stage='download', startedAt=started, message='Downloading '+download.suggested_filename+' to the toolkit…')
        server.state = state
        try:
            target = destination(self.root, tool_id, download.suggested_filename, self.safe_path)
            task = asyncio.create_task(download.path())
            while not task.done():
                await asyncio.sleep(.25)
                received = sum(p.stat().st_size for p in stage.iterdir() if p.is_file())
                server.state = dict(state, received=received)
                if received > 8_000_000_000 or shutil.disk_usage(stage).free < 100_000_000 or self.stop.is_set():
                    await download.cancel()
                    await asyncio.gather(task, return_exceptions=True)
                    raise ValueError('Download cancelled: size, free space or shutdown limit reached')
            temporary = await task
            if not temporary: raise ValueError('Download did not complete')
            source = Path(temporary)
            if source.stat().st_size > 8_000_000_000: raise ValueError('Download exceeds 8 GB')
            # Exclusive create protects an existing file even if it appeared during transfer.
            target = destination(self.root, tool_id, download.suggested_filename, self.safe_path)
            created = False
            try:
                with target.open('xb') as output, source.open('rb') as incoming:
                    created = True
                    shutil.copyfileobj(incoming, output, 1024*1024)
            except Exception:
                if created: target.unlink(missing_ok=True)
                raise
            message = 'Saved '+str(target)+'.'
            if tool_id:
                server.state = dict(state, stage='scan', message='Saved download. Scanning and organizing…')
                message += '\n'+await asyncio.to_thread(self.scan)
            server.state = dict(state, busy=False, stage='complete', message=message)
        except Exception as error:
            server.state = dict(state, busy=False, stage='error', message='Download stopped: '+str(error))
            try: await download.cancel()
            except Exception: pass
        finally:
            server.history.record('vendor-download' if tool_id else 'export', server.state)
            server.lock.release()
            try: await download.delete()
            except Exception: pass
