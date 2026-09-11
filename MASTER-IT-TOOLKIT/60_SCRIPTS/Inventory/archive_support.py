"""Bounded, cross-platform archive readers. No archive paths are extracted by a library."""
import bz2,gzip,lzma,posixpath,re,stat,tarfile,zipfile
from types import SimpleNamespace

SUPPORTED=('.zip','.tar','.tar.gz','.tgz','.tar.bz2','.tbz2','.tar.xz','.txz','.gz','.bz2','.xz')
ARCHIVES=SUPPORTED+('.7z','.rar','.zst')
MAX_BYTES=8*1024**3
MAX_FILES=50000

def member_name(value):
    name=value.replace('\\','/')
    # TAR producers commonly include an otherwise harmless leading ./.
    while name.startswith('./'):name=name[2:]
    parts=name.rstrip('/').split('/')
    if (not name or name.startswith('/') or any(p in ('','.','..') or ':' in p or p.endswith((' ','.')) or
        re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)',p,re.I) for p in parts)
        or any(c in name for c in '<>"|?*') or any(ord(c)<32 for c in name)
        or name.casefold().rstrip('/')=='.toolkit-extracted.json'):
        raise ValueError('Unsafe archive member: '+name)
    return '/'.join(parts)

class Archive:
    def __init__(self,path):self.path=path;self.source=None;self.entries=[]
    def __enter__(self):
        try:
            lower=self.path.name.lower()
            if lower.endswith('.zip'):
                self.source=zipfile.ZipFile(self.path)
                for m in self.source.infolist():
                    mode=m.external_attr>>16
                    if m.flag_bits&1 or stat.S_IFMT(mode) and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):raise ValueError('Encrypted or special ZIP entry')
                    self.entries.append(SimpleNamespace(name=member_name(m.filename),size=m.file_size,directory=m.is_dir(),mode=mode,original=m))
                self.kind='zip'
            elif lower.endswith(('.tar','.tar.gz','.tgz','.tar.bz2','.tbz2','.tar.xz','.txz')):
                self.source=tarfile.open(self.path,'r:*');members=[]
                for m in self.source:
                    if len(members)>=MAX_FILES:raise ValueError('Too many archive members')
                    if m.name in ('.','./') and m.isdir():continue
                    members.append(m)
                index={member_name(m.name):m for m in members}
                if len(index)!=len(members):raise ValueError('Duplicate TAR members')
                for m in members:
                    target=m
                    for _ in range(16):
                        if not (target.issym() or target.islnk()):break
                        link=target.linkname.replace('\\','/')
                        if link.startswith('/') or ':' in link:raise ValueError('Absolute TAR link')
                        relative=posixpath.normpath(posixpath.join(posixpath.dirname(member_name(target.name)),link) if target.issym() else link)
                        target=index.get(member_name(relative))
                        if target is None:raise ValueError('Missing TAR link target')
                    if not (target.isfile() or target.isdir() and m.isdir()):raise ValueError('Unsupported TAR link or special file')
                    self.entries.append(SimpleNamespace(name=member_name(m.name),size=target.size,directory=m.isdir(),mode=target.mode,original=target))
                self.kind='tar'
            else:
                self.kind=lower.rsplit('.',1)[-1]
                if self.kind not in ('gz','bz2','xz'):raise ValueError('Archive format requires manual extraction')
                self.entries=[SimpleNamespace(name=member_name(self.path.stem),size=None,directory=False,mode=0,original=None)]
            names=set();total=0
            for e in self.entries:
                key=e.name.casefold()
                if key in names:raise ValueError('Duplicate archive member: '+e.name)
                names.add(key);total+=e.size or 0
            if len(names)>MAX_FILES or total>MAX_BYTES:raise ValueError('Archive exceeds automatic extraction limits')
            self.total=total
            return self
        except Exception:
            if self.source:self.source.close()
            raise
    def open(self,entry):
        if self.kind=='zip':return self.source.open(entry.original)
        if self.kind=='tar':return self.source.extractfile(entry.original)
        return {'gz':gzip.open,'bz2':bz2.open,'xz':lzma.open}[self.kind](self.path,'rb')
    def __exit__(self,*args):
        if self.source:self.source.close()
