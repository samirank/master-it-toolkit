"""Read-only host inventory. Never uses Win32_Product or launches discovered applications."""
import hashlib
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time

ALIASES={
 '7zip':['7-Zip'], 'bcu':['Bulk Crap Uninstaller','BCUninstaller'], 'revo':['Revo Uninstaller Pro'],
 'firefox':['Mozilla Firefox','Firefox'], 'chrome':['Google Chrome'], 'edge':['Microsoft Edge'],
 'vscode':['Microsoft Visual Studio Code','Visual Studio Code','Code'], 'vlc':['VLC media player','VLC'],
 'libreoffice':['LibreOffice'], 'notepad':['Notepad++'], 'git':['Git'], 'python':['Python'],
 'powershell':['PowerShell'], 'cpuz':['CPUID CPU-Z','CPU-Z'], 'hwmonitor':['CPUID HWMonitor','HWMonitor'],
 'hwinfo':['HWiNFO64','HWiNFO32','HWiNFO'], 'thunderbird':['Mozilla Thunderbird','Thunderbird'],
 'obs':['OBS Studio'], 'onlyoffice':['ONLYOFFICE Desktop Editors'], 'etcher':['balenaEtcher'],
 'easeus-videokit':['EaseUS VideFlow','EaseUS VideoKit']
}
PACKAGES={'7zip':['7zip','p7zip-full'],'vscode':['code'],'vlc':['vlc'],'firefox':['firefox','firefox-esr'],
 'chrome':['google-chrome-stable'],'edge':['microsoft-edge-stable'],'notepad':['notepad-plus-plus'],
 'obs':['obs-studio'],'onlyoffice':['onlyoffice-desktopeditors'],'python':['python3'],'powershell':['powershell'],
 'libreoffice':['libreoffice','libreoffice-core'],'thunderbird':['thunderbird'],'clawsmail':['claws-mail'],
 '4kdownloader':['4kvideodownloaderplus']}

def host_id():
    identity=socket.gethostname()+'|'+sys.platform+'|'+os.environ.get('USERNAME',os.environ.get('USER',''))
    try:
        if os.name=='nt':
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\Microsoft\Cryptography',0,winreg.KEY_READ|winreg.KEY_WOW64_64KEY) as key:
                identity+='|'+str(winreg.QueryValueEx(key,'MachineGuid')[0])
        elif sys.platform.startswith('linux'): identity+='|'+Path('/etc/machine-id').read_text().strip()
    except OSError: pass
    return hashlib.sha256(identity.encode()).hexdigest()[:20]

def normalize(value):
    # Keep punctuation that distinguishes applications (Notepad++ is not Notepad).
    value=re.sub(r'\((?:x64|x86|32.bit|64.bit|arm64|user|en.us|en.gb)(?:\s+(?:x64|x86|arm64|en.us|en.gb))*\)', '', value, flags=re.I)
    value=re.sub(r'\s+(?:v?\d+(?:[.\-]\d+)*(?:\s.*)?|portable|installer|embeddable package)$','',value,flags=re.I)
    return re.sub(r'[^a-z0-9+]+',' ',value.casefold()).strip()

def aliases(tool):
    values=ALIASES.get(tool['id'],[re.sub(r'\s*\(.*?\)','',tool['name'])])
    return {normalize(v) for v in values}

def eligible(tool, platform):
    os_name='Windows' if platform=='win32' else 'macOS' if platform=='darwin' else 'Linux'
    if os_name not in tool.get('os',[]) or tool.get('kind') in ('Built-in','Script','Documentation','Firmware','Boot ISO'):
        return False
    return True

def program_index(programs):
    index={}
    for program in programs:
        key=('package',program['package']) if program.get('package') else ('name',normalize(program['name']))
        index.setdefault(key,[]).append(program)
    return index

def matches(tool, programs, platform, index=None):
    if not eligible(tool,platform):return []
    names=aliases(tool)
    packages=set(PACKAGES.get(tool['id'],[tool['id']]))
    index=program_index(programs) if index is None else index
    return [p for key in [('name',name) for name in names]+[('package',name) for name in packages] for p in index.get(key,[])]

def windows_programs():
    import winreg
    result=[];errors=[]
    for hive,label in [(winreg.HKEY_LOCAL_MACHINE,'machine'),(winreg.HKEY_CURRENT_USER,'user')]:
        for view in (winreg.KEY_WOW64_64KEY,winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(hive,r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',0,winreg.KEY_READ|view) as root:
                    for index in range(winreg.QueryInfoKey(root)[0]):
                        try:
                            with winreg.OpenKey(root,winreg.EnumKey(root,index)) as key:
                                def read(name):
                                    try: return str(winreg.QueryValueEx(key,name)[0])
                                    except OSError: return ''
                                name=read('DisplayName')
                                if name: result.append(dict(name=name,version=read('DisplayVersion'),publisher=read('Publisher'),location=read('InstallLocation'),source='Windows uninstall registry ('+label+')'))
                        except OSError as error: errors.append(str(error))
            except FileNotFoundError: pass
            except OSError as error: errors.append(str(error))
    return result,errors,'Registered desktop applications (machine and current user, 32/64 bit); unregistered portable apps and Store-only apps may not appear.'

def linux_programs():
    result=[];errors=[];sources=[]
    commands=[('dpkg-query',['-W','-f=${db:Status-Abbrev}\t${binary:Package}\t${Version}\n']),('rpm',['-qa','--queryformat','%{NAME}\t%{VERSION}-%{RELEASE}\n'])]
    for name,args in commands:
        path=shutil.which(name)
        if not path: continue
        try:
            response=subprocess.run([path,*args],capture_output=True,text=True,timeout=15)
            if response.returncode: raise ValueError(name+' inventory failed')
            sources.append(name)
            for line in response.stdout.splitlines():
                fields=line.split('\t')
                if name=='dpkg-query':
                    if len(fields)!=3 or fields[0][1:2]!='i':continue
                    fields=fields[1:]
                if len(fields)==2:
                    package=fields[0].split(':')[0];result.append(dict(name=package,package=package,version=fields[1],location='',source=name))
        except (OSError,ValueError,subprocess.TimeoutExpired) as error: errors.append(str(error))
    if not sources: errors.append('No supported package database is available')
    return result,errors,'dpkg/rpm packages; manually copied applications, Flatpak, Snap and other package managers are not included.'

def mac_programs():
    import plistlib
    result=[];errors=[]
    for folder in [Path('/Applications'),Path('/Applications/Utilities'),Path.home()/'Applications']:
        if not folder.exists():continue
        try:
            for app in folder.glob('*.app'):
                try:
                    with (app/'Contents/Info.plist').open('rb') as source: info=plistlib.load(source)
                    result.append(dict(name=info.get('CFBundleDisplayName') or info.get('CFBundleName') or app.stem,version=info.get('CFBundleShortVersionString',''),location=str(app),source='macOS application bundle'))
                except (OSError,ValueError):continue
        except OSError as error:errors.append(str(error))
    return result,errors,'Application bundles in /Applications, /Applications/Utilities and ~/Applications; CLI tools and other locations are not included.'

def survey():
    start=time.monotonic()
    try: programs,errors,coverage=windows_programs() if os.name=='nt' else mac_programs() if sys.platform=='darwin' else linux_programs()
    except Exception as error:programs,errors,coverage=[],[str(error)],'Host inventory unavailable'
    programs=list({(p['name'],p.get('version',''),p.get('location','')):p for p in programs}.values())
    return dict(id=host_id(),name=socket.gethostname(),platform=sys.platform,programs=programs,errors=errors,coverage=coverage,durationMs=round((time.monotonic()-start)*1000))

def apply(catalog, inventory, host=None):
    host=survey() if host is None else host
    inventory['host']={k:v for k,v in host.items() if k!='programs'}
    inventory['host']['programCount']=len(host['programs'])
    index=program_index(host['programs'])
    for tool in catalog:
        found=matches(tool,host['programs'],host['platform'],index)
        record=inventory['tools'][tool['id']]
        record['hostInstalled']=True if found else None if host['errors'] or not eligible(tool,host['platform']) else False
        record['hostMatches']=found
        versions=[p.get('version','') for p in found]
        record['hostVersion']=max(versions,key=lambda v:tuple(int(n) for n in re.findall(r'\d+',v)),default='')
    return inventory
