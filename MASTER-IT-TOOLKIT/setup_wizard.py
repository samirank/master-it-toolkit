"""First-run state belongs to the toolkit database, not the host browser."""
import hashlib,os,shutil,subprocess,sys,time
from pathlib import Path

def volume_id(root):
    # Best effort only: unavailable identifiers must not cause repeated onboarding.
    try:
        if os.name=='nt':
            import ctypes
            from ctypes import wintypes
            kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            mount=ctypes.create_unicode_buffer(32768);serial=wintypes.DWORD()
            if not kernel.GetVolumePathNameW(str(root),mount,len(mount)):return ''
            if not kernel.GetVolumeInformationW(mount.value,None,0,ctypes.byref(serial),None,None,None,0):return ''
            value='windows:'+str(serial.value)
        elif sys.platform.startswith('linux'):
            value=subprocess.check_output(['findmnt','-n','-o','UUID','--target',str(root)],timeout=3,text=True).strip()
            if not value:return ''
            value='linux:'+value
        else:return ''
        return hashlib.sha256(value.encode()).hexdigest()
    except (OSError,subprocess.SubprocessError):return ''

def status(root,store,identity=None):
    workspace=store.workspace();saved=workspace.get('setupState',{})
    identity=volume_id(root) if identity is None else identity
    previous=saved.get('volumes',{}).get(sys.platform)
    changed=bool(identity and previous and identity!=previous)
    disk=shutil.disk_usage(root)
    return dict(required=not saved.get('completed',False) or changed,changedDrive=changed,
        root=str(root.resolve()),free=disk.free,total=disk.total,driveDetection=bool(identity),
        step=0 if changed else saved.get('step',0),backup=workspace.get('backupSettings',{}))

def save(root,store,body,identity=None):
    if not isinstance(body,dict) or set(body)-{'step','completed'}:raise ValueError('Invalid setup request')
    if type(body.get('step')) is not int or not 0<=body['step']<=3 or type(body.get('completed')) is not bool:raise ValueError('Invalid setup progress')
    saved=store.workspace().get('setupState',{})
    identity=volume_id(root) if identity is None else identity
    volumes=dict(saved.get('volumes',{}))
    if identity:volumes[sys.platform]=identity
    store.workspace('setupState',dict(version=1,step=body['step'],completed=body['completed'],volumes=volumes,updatedAt=time.time()))
    return dict(saved=True)
