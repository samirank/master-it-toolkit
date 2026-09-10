"""Explicit, interactive Windows installs with a verified recovery checkpoint."""
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import time
import host_inventory

def ps_quote(value): return "'" + str(value).replace("'", "''") + "'"

def shell():
    if os.name != 'nt': raise ValueError('Tracked installation currently requires Windows. Use your platform package manager.')
    value=shutil.which('powershell.exe')
    if not value: raise ValueError('Windows PowerShell is unavailable')
    return value

def history_folder(root, safe_path):
    host=hashlib.sha256(socket.gethostname().encode()).hexdigest()[:16]
    return safe_path(root,'70_DOCUMENTATION/Service-Notes/Install-History/'+host)

def digest(path):
    result=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''): result.update(block)
    return result.hexdigest()

def candidates(root, tool_id, safe_path):
    catalog=json.loads((root/'assets/toolkit-manifest.json').read_text('utf-8'))
    tool=next((t for t in catalog if t['id']==tool_id),None)
    if not tool: raise ValueError('Unknown tool')
    reason=''
    if 'Windows' not in tool.get('os',[]): reason='Use the official installer or package manager for this platform.'
    elif tool.get('kind') in ('Firmware','Driver','Boot ISO','Built-in','Script','Documentation') or tool.get('bootable'):
        reason='This tool requires its own setup procedure; firmware, drivers and boot media are not handled as application installs.'
    records=[]
    if not reason:
        try:
            text=(root/'assets/js/local-inventory.js').read_text('utf-8-sig')
            inventory=json.loads(text.split('window.LOCAL_INVENTORY =',1)[1].strip().rstrip(';'))
            folder=safe_path(root,tool['localFolder'])
            for item in inventory.get('tools',{}).get(tool_id,{}).get('files',[]):
                path=safe_path(root,item['path']);path.relative_to(folder)
                # An arbitrary portable EXE is not an installer. MSI or recognizable setup names only.
                setup=path.suffix.lower()=='.msi' or (path.suffix.lower()=='.exe' and (re.search(r'setup|(?:^|[-_.])install(?:er)?(?:[-_.]|$)',path.name,re.I) or (tool_id=='termius' and path.name.casefold()=='install termius.exe') or (tool_id=='7zip' and re.fullmatch(r'7z\d+(-x64|-arm64)?\.exe',path.name,re.I))))
                if setup and path.is_file() and path.stat().st_size:
                    records.append({'path':item['path'],'name':path.name,'size':path.stat().st_size})
        except (OSError,ValueError,KeyError,IndexError): pass
    return tool,records[:20],reason

def options(root, tool_id, safe_path):
    tool,files,reason=candidates(root,tool_id,safe_path)
    if os.name!='nt': reason='Tracked installs currently require Windows. Use the official installer or your platform package manager.'
    if not reason:
        for item in files:
            path=safe_path(root,item['path']);item['sha256']=digest(path)
            command="$ErrorActionPreference='Stop'; Import-Module (Join-Path $PSHOME 'Modules/Microsoft.PowerShell.Security/Microsoft.PowerShell.Security.psd1'); $s=Get-AuthenticodeSignature -LiteralPath "+ps_quote(path)+'; @{status=[string]$s.Status;publisher=[string]$s.SignerCertificate.Subject}|ConvertTo-Json -Compress'
            result=subprocess.run([shell(),'-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,timeout=60)
            item['signature']=json.loads(result.stdout) if result.returncode==0 and result.stdout.strip() else {'status':'Unavailable','publisher':''}
        if not files: reason='No recognized installer is downloaded. Download an installer and scan first. Portable apps do not need installation.'
    host=host_inventory.survey()
    host_matches=host_inventory.matches(tool,host['programs'],host['platform'])
    return {'hostMatches':host_matches,'installedOnHost':bool(host_matches),'tool':tool_id,'name':tool['name'],'host':socket.gethostname(),'windows':os.name=='nt','files':files,'reason':reason,'history':history(root,safe_path,tool_id)}

def history(root,safe_path,tool_id=None):
    folder=history_folder(root,safe_path)
    result=[]
    if folder.exists():
        for p in sorted(folder.glob('*.result.json'),reverse=True)[:100]:
            try:
                p=safe_path(root,p.relative_to(root).as_posix());entry=json.loads(p.read_text('utf-8-sig'))
                if tool_id is None or entry.get('tool')==tool_id: result.append(entry)
            except (OSError,ValueError): continue
    return result

def install(root,body,safe_path):
    powershell=shell()
    _,files,reason=candidates(root,body['tool'],safe_path)
    if reason or body.get('package') not in [f['path'] for f in files]: raise ValueError(reason or 'Installer is not in the scanned tool inventory')
    package=safe_path(root,body['package'])
    if not re.fullmatch('[a-f0-9]{64}',body.get('sha256','')) or digest(package)!=body['sha256']:
        raise ValueError('Installer changed. Reopen the installation review.')
    folder=history_folder(root,safe_path);folder.mkdir(parents=True,exist_ok=True)
    id=time.strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(4)
    plan=folder/(id+'.plan.json')
    plan.write_text(json.dumps({'tool':body['tool'],'package':str(package),'sha256':body['sha256'],'host':socket.gethostname(),'acceptUnsigned':body.get('acceptUnsigned') is True}),encoding='utf-8')
    script=safe_path(root,'60_SCRIPTS/Inventory/Install-TrackedApplication.ps1')
    # PowerShell receives only a quoted fixed script and a generated plan filename; no installer switches are supplied by the browser.
    arguments=subprocess.list2cmdline(['-NoProfile','-ExecutionPolicy','Bypass','-File',str(script),'-Plan',str(plan),'-PlanSha256',digest(plan)])
    command='$ErrorActionPreference="Stop"; $p=Start-Process -FilePath '+ps_quote(powershell)+' -ArgumentList '+ps_quote(arguments)+' -Verb RunAs -PassThru -Wait; exit $p.ExitCode'
    process=subprocess.run([powershell,'-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True)
    result_path=plan.with_name(id+'.result.json')
    if not result_path.exists(): raise RuntimeError('Installation did not start or UAC was cancelled. No toolkit recovery record was produced.')
    result=json.loads(result_path.read_text('utf-8-sig'))
    if process.returncode or result.get('status')=='stopped': raise RuntimeError(result.get('message','Installation stopped; open install history.'))
    return result.get('message','Installer finished. Review installation history.')

def recovery(action):
    shell()
    windows=Path(os.environ.get('SystemRoot','C:/Windows'))/'System32'
    if action=='installed-apps': subprocess.Popen([str(windows/'control.exe'),'appwiz.cpl'])
    elif action=='system-restore': subprocess.Popen([str(windows/'rstrui.exe')])
    else: raise ValueError('Unknown recovery action')
    return 'Opened the Windows recovery interface. Review the selected program or restore point before making changes.'
