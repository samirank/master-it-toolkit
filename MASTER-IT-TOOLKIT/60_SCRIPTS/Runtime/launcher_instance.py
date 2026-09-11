"""One launcher per toolkit folder; second launches focus the authenticated session."""
import json
import os
import time
import urllib.request
from pathlib import Path
if os.name == 'nt':
    import msvcrt
else:
    import fcntl


class Instance:
    def __init__(self, root):
        self.folder = Path(root) / '90_TEMP/launcher'
        self.folder.mkdir(parents=True, exist_ok=True)
        self.record = self.folder / 'session.json'
        self.handle = None

    def acquire(self):
        handle = (self.folder / 'instance.lock').open('a+b')
        handle.seek(0, 2)
        if handle.tell() == 0: handle.write(b'0'); handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt': msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else: fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close(); return False
        self.handle = handle
        self.record.unlink(missing_ok=True)
        return True

    def publish(self, origin, token):
        temporary = self.record.with_suffix('.tmp')
        with temporary.open('w', encoding='utf-8') as output:
            if os.name != 'nt': os.fchmod(output.fileno(), 0o600)
            json.dump({'origin': origin, 'token': token}, output)
            output.flush(); os.fsync(output.fileno())
        os.replace(temporary, self.record)

    def focus(self, timeout=20):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                import re
                info = json.loads(self.record.read_text('utf-8'))
                origin, token = info['origin'], info['token']
                if not re.fullmatch(r'http://127\.0\.0\.1:\d+', origin) or not re.fullmatch(r'[A-Za-z0-9_-]{20,100}', token):
                    raise ValueError('Invalid session record')
                request = urllib.request.Request(origin+'/'+token+'/api/focus', data=b'{}', headers={'Origin': origin, 'Content-Type': 'application/json'})
                with urllib.request.urlopen(request, timeout=2) as response:
                    if response.status == 200: return True
            except (OSError, ValueError, KeyError): pass
            time.sleep(.25)
        return False

    def close(self):
        if self.handle is not None:
            self.record.unlink(missing_ok=True)
            self.handle.close(); self.handle = None
