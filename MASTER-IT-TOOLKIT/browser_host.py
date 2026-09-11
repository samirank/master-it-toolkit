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
import fnmatch
import hashlib
from urllib.parse import urlsplit

EXTENSIONS = {'.exe','.msi','.msix','.zip','.7z','.gz','.xz','.bz2','.dmg','.pkg','.deb','.rpm','.appimage','.iso'}

def allowed_package(tool, filename):
    return Path(filename).suffix.lower() in EXTENSIONS or (Path(filename).suffix.lower()=='.ps1' and
        any(fnmatch.fnmatchcase(filename.casefold(), pattern.casefold()) for pattern in tool.get('inventoryPatterns',[]) if pattern.lower().endswith('.ps1')))


def destination(root, tool_id, filename, safe_path, existing=False):
    if not filename or Path(filename).name != filename or '/' in filename or '\\' in filename or ':' in filename or filename.endswith(('.', ' ')):
        raise ValueError('Invalid download filename')
    if re.match(r'^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)', filename, re.I): raise ValueError('Reserved filename')
    if tool_id:
        catalog = json.loads((root/'assets/toolkit-manifest.json').read_text('utf-8'))
        tool = next((t for t in catalog if t['id'] == tool_id), None)
        if not tool or not tool.get('localFolder'): raise ValueError('Unknown tool destination')
        folder = safe_path(root, tool['localFolder'])
        if not allowed_package(tool,filename): raise ValueError('Unsupported package type for this tool; no file was imported')
    else:
        folder = safe_path(root, '70_DOCUMENTATION/Service-Notes/Exports')
        if Path(filename).suffix.lower() not in ('.json','.txt','.csv'): raise ValueError('Use the tool download manager for software packages')
    folder.mkdir(parents=True, exist_ok=True)
    path = safe_path(root, (folder/filename).relative_to(root).as_posix())
    if path.exists() and not existing: raise ValueError('A file with this name already exists; it was preserved. Review it in Manage files.')
    return path


class Host:
    def __init__(self, server, safe_path, scan):
        self.server, self.root, self.safe_path, self.scan = server, server.root, safe_path, scan
        self.stop = threading.Event()
        self.focus_requested = threading.Event()
        self.windows = set()
        self.lock = threading.Lock()
        self.notice = None
        self.pending = 0
        self.filtering = {}
        self.extension = self.root/'runtime-extensions/ubol'

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

    def focus_dashboard(self, url):
        with self.lock:
            if '_dashboard' in self.windows:
                self.focus_requested.set()
                return
        self.open(url)

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
        from platform_runtime import browser_session
        with browser_session(self.root) as bundled:
            await self._window(url, tool_id, bundled)

    async def _window(self, url, tool_id, bundled):
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
                arguments=['--app=about:blank','--window-size=1280,860']
                if tool_id:
                    if not (self.extension/'manifest.json').is_file(): raise ValueError('uBlock Origin Lite is missing. Update the toolkit package before opening publisher windows.')
                    arguments += ['--disable-extensions-except='+str(self.extension),'--load-extension='+str(self.extension)]
                context = await engine.chromium.launch_persistent_context(str(profile), channel='chromium',
                    headless=os.environ.get('TOOLKIT_BROWSER_TEST_HEADLESS') == '1', accept_downloads=True,
                    downloads_path=str(stage), no_viewport=True, ignore_default_args=['--disable-extensions'] if tool_id else None, args=arguments)
                tasks = set()
                def downloaded(download):
                    task = asyncio.create_task(self.save(download, tool_id, stage)); tasks.add(task); task.add_done_callback(tasks.discard)
                def attach(page): page.on('download', downloaded)
                context.on('page', attach)
                for page in context.pages: attach(page)
                page = context.pages[0] if context.pages else await context.new_page()
                extension_url = None
                last_filter = None
                if tool_id:
                    worker=next((w for w in context.service_workers if w.url.startswith('chrome-extension://')),None)
                    if worker is None: worker=await context.wait_for_event('serviceworker',timeout=15000)
                    extension_url=worker.url.split('/js/')[0]
                    await self.set_filter(context,extension_url,urlsplit(url).hostname,self.filtering.get(tool_id,True))
                    last_filter=(urlsplit(url).hostname,self.filtering.get(tool_id,True))
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                except Exception:
                    if not tasks: raise
                try:
                    while context.pages and not self.stop.is_set():
                        if tool_id is None and self.focus_requested.is_set():
                            self.focus_requested.clear()
                            target = next((p for p in context.pages if not p.is_closed()), None)
                            if target:
                                await target.bring_to_front()
                                # Restore minimized Chromium windows as well as selecting the tab.
                                session = await context.new_cdp_session(target)
                                try:
                                    window = await session.send('Browser.getWindowForTarget')
                                    await session.send('Browser.setWindowBounds', {'windowId': window['windowId'], 'bounds': {'windowState': 'normal'}})
                                finally: await session.detach()

                        if extension_url and not page.is_closed():
                            host=urlsplit(page.url).hostname
                            desired=(host,self.filtering.get(tool_id,True))
                            if host and urlsplit(page.url).scheme in ('http','https') and desired!=last_filter:
                                await self.set_filter(context,extension_url,*desired)
                                last_filter=desired
                                await page.bring_to_front()
                        await asyncio.sleep(.25)
                finally:
                    await context.close()
                    if tasks: await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    async def set_filter(context, extension_url, hostname, enabled):
        settings=await context.new_page()
        try:
            await settings.goto(extension_url+'/dashboard.html')
            result=await settings.evaluate('(s)=>chrome.runtime.sendMessage({what:"setFilteringMode",hostname:s.hostname,level:s.level})',
                {'hostname':hostname,'level':1 if enabled else 0})
            if result != (1 if enabled else 0): raise ValueError('Ad blocking setting was not applied')
        finally: await settings.close()

    async def save(self, download, tool_id, stage):
        server = self.server
        with self.lock: self.pending += 1
        try:
            if self.pending > 8: raise ValueError('Download queue is full; finish the queued files before adding more')
            while not server.lock.acquire(False):
                self.notice = {'tool':tool_id,'stage':'queued','message':'Download queued. Waiting for the current toolkit job…'}
                if self.stop.is_set() or not download.page.context.pages: raise ValueError('Publisher window closed while download was queued')
                if sum(p.stat().st_size for p in stage.iterdir() if p.is_file())>8_000_000_000 or shutil.disk_usage(stage).free<100_000_000:
                    raise ValueError('Download queue exceeded its storage limit')
                await asyncio.sleep(.25)
        except Exception as error:
            self.notice = {'tool':tool_id,'stage':'error','message':str(error)}
            server.history.record('vendor-download',self.notice)
            try: await download.cancel(); await download.delete()
            except Exception: pass
            return
        finally:
            with self.lock: self.pending -= 1
        self.notice = None
        started = time.time()
        temporary = None
        state = dict(busy=True, tool=tool_id, stage='download', startedAt=started, message='Downloading '+download.suggested_filename+' to the toolkit…')
        server.state = state
        try:
            target = destination(self.root, tool_id, download.suggested_filename, self.safe_path, existing=True)
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
            target = destination(self.root, tool_id, download.suggested_filename, self.safe_path, existing=True)
            duplicate = target.exists() and self.same_file(target,source)
            if target.exists() and not duplicate: raise ValueError('A different file with this name already exists; it was preserved. Review the destination before replacing it.')
            created = False
            try:
                if not duplicate:
                    with target.open('xb') as output, source.open('rb') as incoming:
                        created = True
                        shutil.copyfileobj(incoming, output, 1024*1024)
            except Exception:
                if created: target.unlink(missing_ok=True)
                raise
            message = ('✓ Already saved (identical file)' if duplicate else '✓ Download saved')+'\nDestination: '+str(target)
            if tool_id:
                server.state = dict(state, stage='scan', message='Saved download. Scanning and organizing…')
                report = await asyncio.to_thread(self.scan)
                message += '\n✓ Inventory refreshed and organization checked\n'+report
            await download.delete()
            message += '\n✓ Temporary transfer file removed'
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
            server.publish_completion()

    @staticmethod
    def same_file(a,b):
        if not a.is_file() or a.stat().st_size != b.stat().st_size: return False
        def digest(path):
            value=hashlib.sha256()
            with path.open('rb') as source:
                for chunk in iter(lambda:source.read(1024*1024),b''):value.update(chunk)
            return value.digest()
        return digest(a)==digest(b)
