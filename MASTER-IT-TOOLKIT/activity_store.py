"""Bounded local job history. No network, account passwords or session tokens."""
import threading
import time
import json


class Store:
    def __init__(self, root, safe_path, token=''):
        self.lock = threading.Lock()
        self.token = token
        self.error = ''
        self.path = safe_path(root, '70_DOCUMENTATION/Service-Notes/Activity/activity.sqlite')
        self.safe_path, self.root = safe_path, root
        try:
            import sqlite3  # Older frozen runtimes may not include this module.
            self.sqlite = sqlite3
            self.path.parent.mkdir(parents=True, exist_ok=True)
            db = self.connect()
            try:
                with db:
                    db.execute('CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY, finished REAL, action TEXT, tool TEXT, stage TEXT, message TEXT)')
                    db.execute('CREATE TABLE IF NOT EXISTS workspace (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
                    db.execute('CREATE TABLE IF NOT EXISTS workflow_runs (id INTEGER PRIMARY KEY, finished REAL, record TEXT NOT NULL)')
            finally: db.close()
        except Exception as error:
            self.error = 'Local history unavailable: ' + str(error)

    def connect(self):
        # Check SQLite sidecars too; never follow a substituted symlink on the SSD.
        for suffix in ('', '-journal', '-wal', '-shm'):
            self.safe_path(self.root, self.path.relative_to(self.root).as_posix() + suffix)
        db = self.sqlite.connect(str(self.path), timeout=5)
        db.execute('PRAGMA synchronous=FULL')
        db.execute('PRAGMA fullfsync=ON')
        return db

    def workspace(self, key=None, value=None):
        if self.error: raise RuntimeError(self.error)
        if key is not None and key not in ('preferences', 'favorites', 'notes', 'checklists', 'capacity', 'customWorkflows', 'backupSettings'):
            raise ValueError('Unknown workspace setting')
        if key=='backupSettings' and (not isinstance(value,dict) or set(value)-{'destination','scope','automatic','intervalHours'} or not isinstance(value.get('destination'),str) or len(value['destination'])>2048 or value.get('scope') not in ('workspace','full')):
            raise ValueError('Invalid backup settings')
        if key=='backupSettings' and (type(value.get('automatic',False)) is not bool or type(value.get('intervalHours',24)) is not int or not 1<=value.get('intervalHours',24)<=168):
            raise ValueError('Invalid automatic backup schedule')
        if key == 'customWorkflows':
            import portable_tools
            portable_tools.validate_custom_workflows(self.root, value)
        encoded = json.dumps(value, allow_nan=False)
        if len(encoded.encode('utf-8')) > 2_000_000: raise ValueError('Workspace setting is too large')
        with self.lock:
            db = self.connect()
            try:
                if key is not None:
                    with db:
                        db.execute('INSERT OR REPLACE INTO workspace(key,value) VALUES (?,?)', (key, encoded))
                return {k: json.loads(v) for k, v in db.execute('SELECT key,value FROM workspace')}
            finally: db.close()

    def record(self, action, state):
        if self.error: return
        message = str(state.get('message', ''))
        if self.token: message = message.replace(self.token, '[session]')
        try:
            with self.lock:
                db = self.connect()
                try:
                    with db:
                        db.execute('INSERT INTO jobs(finished,action,tool,stage,message) VALUES (?,?,?,?,?)',
                            (time.time(), str(action)[:80], str(state.get('tool') or '')[:120], state.get('stage', 'complete'), message[:64000]))
                        db.execute('DELETE FROM jobs WHERE id NOT IN (SELECT id FROM jobs ORDER BY id DESC LIMIT 500)')
                        if 'workflowRecord' in state:
                            record=json.dumps({'name':state.get('workflowName','Workflow'),'profile':state.get('workflowProfile',''),'message':message,'steps':state['workflowRecord']},ensure_ascii=False)
                            if self.token: record=record.replace(self.token,'[session]')
                            db.execute('INSERT INTO workflow_runs(finished,record) VALUES (?,?)',(time.time(),record))
                            db.execute('DELETE FROM workflow_runs WHERE id NOT IN (SELECT id FROM workflow_runs ORDER BY id DESC LIMIT 100)')
                finally: db.close()
        except Exception as error: self.error = 'Local history unavailable: ' + str(error)

    def recent(self):
        if self.error: return {'jobs': [], 'error': self.error}
        with self.lock:
            db = self.connect()
            try:
                rows = db.execute('SELECT id,finished,action,tool,stage,message FROM jobs ORDER BY id DESC LIMIT 100').fetchall()
                runs=[dict(id=id,finished=finished,**json.loads(record)) for id,finished,record in db.execute('SELECT id,finished,record FROM workflow_runs ORDER BY id DESC LIMIT 100')]
                return {'jobs': [dict(zip(('id','finished','action','tool','stage','message'), row)) for row in rows], 'workflows':runs}
            finally: db.close()


    def workflow_job(self, record=None, machine=None):
        with self.lock:
            db=self.connect()
            try:
                with db:
                    db.execute('CREATE TABLE IF NOT EXISTS workflow_jobs (id TEXT PRIMARY KEY, machine TEXT, updated REAL, record TEXT)')
                    if record is not None:
                        db.execute('INSERT OR REPLACE INTO workflow_jobs VALUES (?,?,?,?)',(record['id'],record['machine']['id'],time.time(),json.dumps(record)))
                rows=db.execute('SELECT record FROM workflow_jobs WHERE machine=? ORDER BY updated DESC LIMIT 200',(machine,)) if machine else db.execute('SELECT record FROM workflow_jobs ORDER BY updated DESC LIMIT 200')
                return [json.loads(row[0]) for row in rows]
            finally:db.close()
