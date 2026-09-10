"""Password/recovery-key wrapped AES-256-GCM vault; SQLite plaintext stays in memory."""
import base64,json,os,secrets,sqlite3,threading,time
from pathlib import Path
MAGIC=b'MITVAULT1\n'
LOCKS={};KEYS={}

def b64(data):return base64.b64encode(data).decode('ascii')
def un64(data):return base64.b64decode(data,validate=True)
def crypto():
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    return AESGCM

def derive(password,salt):
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    return Scrypt(salt=salt,length=32,n=32768,r=8,p=1).derive(password.encode('utf-8'))

def seal(key,data,aad):
    nonce=os.urandom(12)
    return b64(nonce+crypto()(key).encrypt(nonce,data,aad))
def open_seal(key,data,aad):
    value=un64(data)
    return crypto()(key).decrypt(value[:12],value[12:],aad)
def atomic(path,data):
    temporary=path.with_name('.'+path.name+'.'+secrets.token_hex(8)+'.tmp')
    try:
        with temporary.open('xb') as output:output.write(data);output.flush();os.fsync(output.fileno())
        os.replace(temporary,path)
        if os.name!='nt':
            fd=os.open(str(path.parent),os.O_RDONLY)
            try:os.fsync(fd)
            finally:os.close(fd)
    finally:
        if temporary.exists():temporary.unlink()
def encrypted(path):
    if not path.exists():return False
    with path.open('rb') as source:return source.read(len(MAGIC))==MAGIC

def mutex(path):return LOCKS.setdefault(str(path.resolve()),threading.RLock())
def status(path):return dict(configured=encrypted(path),locked=encrypted(path) and str(path.resolve()) not in KEYS)
def lock(path):
    with mutex(path):KEYS.pop(str(path.resolve()),None)
def header(path):
    raw=path.read_bytes()
    if not raw.startswith(MAGIC):raise ValueError('Vault is not configured')
    return json.loads(raw[len(MAGIC):])
def setup(path,password):
    if not isinstance(password,str) or not 14<=len(password)<=1024:raise ValueError('Use a passphrase of at least 14 characters')
    with mutex(path):
        if encrypted(path):raise ValueError('Vault already configured')
        path.parent.mkdir(parents=True,exist_ok=True)
        db=sqlite3.connect(str(path))
        try:
            db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Existing database needs recovery first')
            # Ensure a serializable database even on a new installation.
            db.execute('CREATE TABLE IF NOT EXISTS vault_marker (version INTEGER)');db.commit()
            payload=db.serialize()
        finally:db.close()
        recovery=secrets.token_urlsafe(32);key=os.urandom(32);salt=os.urandom(16)
        doc={'salt':b64(salt),'password':seal(derive(password,salt),key,b'mit-password-v1'),'recovery':seal(derive(recovery,salt),key,b'mit-recovery-v1'),'data':seal(key,payload,b'mit-sqlite-v1')}
        atomic(path,MAGIC+json.dumps(doc).encode())
        KEYS[str(path.resolve())]=key
        return recovery

def unlock(path,secret,recovery=False):
    if not isinstance(secret,str) or len(secret)>1024:raise ValueError('Invalid unlock value')
    with mutex(path):
        doc=header(path)
        try:
            field='recovery' if recovery else 'password'
            key=open_seal(derive(secret,un64(doc['salt'])),doc[field],('mit-'+field+'-v1').encode())
            open_seal(key,doc['data'],b'mit-sqlite-v1')
        except Exception:raise ValueError('Incorrect secret or damaged vault') from None
        KEYS[str(path.resolve())]=key

class Connection:
    def __init__(self,path):
        self.path=path;self.lock=mutex(path);self.lock.acquire();self.closed=False
        try:
            self.key=KEYS.get(str(path.resolve()))
            if self.key is None:raise ValueError('Workspace locked. Unlock the encrypted vault first.')
            self.doc=header(path);self.before=open_seal(self.key,self.doc['data'],b'mit-sqlite-v1')
            self.db=sqlite3.connect(':memory:');self.db.deserialize(self.before)
            self.db.execute('PRAGMA temp_store=MEMORY')
        except Exception:self.lock.release();raise
    def __getattr__(self,name):return getattr(self.db,name)
    def __enter__(self):self.db.__enter__();return self
    def __exit__(self,*args):return self.db.__exit__(*args)
    def close(self):
        if self.closed:return
        self.closed=True
        try:
            if self.db.in_transaction:self.db.rollback()
            after=self.db.serialize()
            if after!=self.before:
                self.doc['data']=seal(self.key,after,b'mit-sqlite-v1')
                atomic(self.path,MAGIC+json.dumps(self.doc).encode())
        finally:self.db.close();self.key=None;self.lock.release()
