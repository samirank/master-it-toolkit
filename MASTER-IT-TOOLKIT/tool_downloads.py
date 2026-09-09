"""Publisher release choices and download-only transfers. Never executes packages."""
import hashlib
import datetime
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import urllib.request
from urllib.parse import urlsplit

def fetch_json(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'MasterITToolkit', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(8_000_001)
    if len(data) > 8_000_000: raise ValueError('Publisher response too large')
    return json.loads(data)

def platform_for(name, supported):
    n = name.lower()
    if any(s in n for s in ('macos', 'darwin', '-mac', 'osx')) or n.endswith(('.dmg', '.pkg')): return 'macOS'
    if any(s in n for s in ('linux', 'appimage')) or n.endswith(('.deb', '.rpm')): return 'Linux'
    if any(s in n for s in ('windows', '-win')) or n.endswith(('.exe', '.msi', '.msix', '.msixbundle')): return 'Windows'
    return supported[0] if len(supported) == 1 else 'Other / check filename'

def options(root, tool_id):
    catalog = json.loads((root / 'assets/toolkit-manifest.json').read_text('utf-8'))
    tool = next((t for t in catalog if t['id'] == tool_id), None)
    if not tool: raise ValueError('Unknown tool')
    result = {'tool': tool_id, 'name': tool['name'], 'source': tool['officialDownload'], 'folder': tool['localFolder'], 'assets': [], 'platforms': tool['os']}
    if tool['license'] == 'Paid': return result
    repo = 'ip7z/7zip' if tool_id == '7zip' else None
    for value in (tool['officialDownload'], tool['officialWebsite']):
        parts = urlsplit(value)
        path = parts.path.strip('/').split('/')
        if parts.hostname == 'github.com' and len(path) >= 2 and all(re.fullmatch(r'[A-Za-z0-9_.-]+', p) for p in path[:2]): repo = '/'.join(path[:2]); break
    if repo:
        release = fetch_json('https://api.github.com/repos/' + repo + '/releases/latest')
        result['version'] = release.get('tag_name', '')
        for asset in release.get('assets', []):
            name, url = asset.get('name', ''), asset.get('browser_download_url', '')
            if re.search(r'(^|[-_.])(src|source|sdk)([-_.]|$)', name, re.I) or (tool_id == '7zip' and name.startswith('lzma')): continue
            if not name or name != Path(name).name or '\\' in name or ':' in name: continue
            if not url.startswith('https://github.com/' + repo + '/releases/download/'): continue
            if not re.search(r'\.(exe|msi|msix|msixbundle|zip|7z|gz|xz|bz2|dmg|pkg|deb|rpm|appimage|iso)$', name, re.I): continue
            result['assets'].append({'id': str(asset['id']), 'name': name, 'url': url, 'size': asset.get('size', 0), 'digest': asset.get('digest'), 'platform': platform_for(name, tool['os'])})
    elif tool_id == 'sysinternals':
        result['assets'] = [{'id': 'suite', 'name': 'SysinternalsSuite.zip', 'url': 'https://download.sysinternals.com/files/SysinternalsSuite.zip', 'size': 0, 'digest': None, 'platform': 'Windows'}]
    return result

def save_selected(root, tool_id, selected, safe_path, progress):
    info = options(root, tool_id)
    assets = {a['id']: a for a in info['assets']}
    if not selected or len(selected) != len(set(selected)) or any(i not in assets for i in selected): raise ValueError('Invalid selection; reload the publisher choices')
    folder = safe_path(root, info['folder'])
    folder.mkdir(parents=True, exist_ok=True)
    results = []
    for index, key in enumerate(selected, 1):
        asset = assets[key]
        destination = safe_path(root, info['folder'] + '/' + asset['name'])
        if destination.exists():
            results.append('Kept existing: ' + asset['name']); continue
        size = asset.get('size', 0)
        if size and 2 * size + 100_000_000 > shutil.disk_usage(folder).free: raise ValueError('Not enough free space for download staging')
        temporary = safe_path(root, info['folder'] + '/.' + asset['name'] + '.' + secrets.token_hex(6) + '.partial')
        digest = hashlib.sha256(); total = 0
        try:
            request = urllib.request.Request(asset['url'], headers={'User-Agent': 'MasterITToolkit'})
            with urllib.request.urlopen(request, timeout=60) as response, temporary.open('xb') as output:
                transfer_size = size or int(getattr(response, 'headers', {}).get('Content-Length', '0'))
                final = urlsplit(response.url)
                if final.scheme != 'https' or final.hostname not in ('github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com', 'download.sysinternals.com'): raise ValueError('Unexpected publisher redirect')
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk: break
                    total += len(chunk)
                    if total > 8_000_000_000: raise ValueError('Package exceeds 8 GB transfer limit')
                    output.write(chunk); digest.update(chunk)
                    progress({'message': 'Downloading ' + asset['name'], 'file': asset['name'], 'received': total, 'total': transfer_size or None, 'index': index, 'count': len(selected), 'stage': 'download'})
            if size and total != size: raise ValueError('Incomplete publisher download')
            expected = asset.get('digest') or ''
            if expected.startswith('sha256:') and digest.hexdigest() != expected[7:]: raise ValueError('Publisher SHA256 mismatch')
            # Exclusive creation prevents overwriting files created during the transfer.
            with destination.open('xb') as output, temporary.open('rb') as source:
                try: shutil.copyfileobj(source, output)
                except Exception:
                    output.close(); destination.unlink(); raise
            results.append('Saved: ' + str(destination) + (' (SHA256 verified)' if expected.startswith('sha256:') else ' (no publisher SHA256 supplied)'))
        finally:
            if temporary.exists(): temporary.unlink()
    receipt_path = safe_path(root, 'assets/download-receipts.json')
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    try: receipts = json.loads(receipt_path.read_text('utf-8'))
    except (OSError, ValueError): receipts = {}
    previous = {r['path']: r for r in receipts.get(tool_id, [])}
    for key in selected:
        asset=assets[key]; destination=safe_path(root, info['folder']+'/'+asset['name'])
        if destination.exists():
            relative=destination.relative_to(root).as_posix()
            # Only newly saved files get release-version attribution; existing files are not re-labelled.
            if any(line.startswith('Saved: '+str(destination)) for line in results):
                previous[relative]={'path':relative,'size':destination.stat().st_size,'version':info.get('version',''),'savedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    receipts[tool_id]=list(previous.values())
    if info.get('version'): receipts.setdefault('_latest',{})[tool_id]=info['version']
    temp=receipt_path.with_name('.download-receipts-'+secrets.token_hex(6)+'.tmp')
    temp.write_text(json.dumps(receipts,indent=2),encoding='utf-8');os.replace(temp,receipt_path)
    return '\n'.join(results) + '\nPackages saved. The following scan extracts recognized ZIP packages; installers are never run automatically.'

def check_updates(root, safe_path):
    inventory=(root/'assets/js/local-inventory.js').read_text('utf-8-sig')
    records=json.loads(inventory.split('window.LOCAL_INVENTORY =',1)[1].strip().rstrip(';'))['tools']
    path=safe_path(root,'assets/download-receipts.json')
    try: receipts=json.loads(path.read_text('utf-8'))
    except (OSError,ValueError): receipts={}
    checked=0; errors=[]
    for id,record in records.items():
        if not (record.get('downloaded') or record.get('installed')): continue
        try:
            info=options(root,id)
            if info.get('version'):receipts.setdefault('_latest',{})[id]=info['version'];checked+=1
        except Exception as error:errors.append(id+': '+str(error))
    path.write_text(json.dumps(receipts,indent=2),encoding='utf-8')
    return 'Checked '+str(checked)+' publisher releases. Vendor-managed tools require their own update check.'+ ('\n'+'\n'.join(errors) if errors else '')
