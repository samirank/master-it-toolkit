"""Publisher release choices and download-only transfers. Never executes packages."""
import fnmatch
import hashlib
import datetime
import json
import ipaddress
import os
from pathlib import Path
import re
import secrets
import shutil
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit, unquote, quote

FEED_URL = 'https://raw.githubusercontent.com/samirank/master-it-toolkit/download-catalog/catalog.json'

def fetch_bytes(url, limit=8_000_000):
    headers = {'User-Agent': 'MasterITToolkit', 'Accept': 'application/json, application/xml, */*'}
    if urlsplit(url).hostname == 'api.github.com' and os.environ.get('GITHUB_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
                data = response.read(limit + 1)
            if len(data) > limit: raise ValueError('Publisher response too large')
            return data
        except (urllib.error.URLError, TimeoutError) as error:
            if isinstance(error, urllib.error.HTTPError) and error.code not in (408, 429, 500, 502, 503, 504): raise
            if attempt == 2: raise
            time.sleep(2 ** attempt)

def fetch_json(url):
    return json.loads(fetch_bytes(url))

def architecture(name):
    if re.search(r'arm64|aarch64', name, re.I): return 'arm64'
    if re.search(r'armv?[67]|armhf|[-_.]arm[-_.]', name, re.I): return 'arm'
    if re.search(r'x86_64|amd64|x64|win64|64bit', name, re.I): return 'x64'
    if re.search(r'i[3-6]86|x86|win32|32bit|ia32', name, re.I): return 'x86'
    return 'universal'

def sources(root):
    path = root / 'assets/download-sources.json'
    return json.loads(path.read_text('utf-8')) if path.exists() else {}

def cached_catalog(root):
    for name in ('assets/download-catalog-cache.json', 'assets/download-catalog.json'):
        try:
            data = json.loads((root/name).read_text('utf-8'))
            if data.get('schema') == 1: return data
        except (OSError, ValueError): pass
    return {'schema': 1, 'tools': {}}

def refresh_catalog(root, safe_path):
    data = fetch_json(FEED_URL)
    if data.get('schema') != 1 or not isinstance(data.get('tools'), dict): raise ValueError('Invalid download catalog')
    for item in data['tools'].values():
        for asset in item.get('assets', []): validate_asset(asset)
    path = safe_path(root, 'assets/download-catalog-cache.json')
    temp = path.with_name('.catalog-'+secrets.token_hex(6)+'.tmp'); temp.write_text(json.dumps(data), encoding='utf-8'); os.replace(temp, path)
    return data

def validate_asset(asset):
    name = asset.get('name', '')
    if not name or len(name)>220 or name != Path(name).name or any(c in name for c in '\\/:\x00<>|?*') or name in ('.','..') or name.endswith(('.', ' ')):
        raise ValueError('Unsafe publisher filename')
    u = urlsplit(asset.get('url',''))
    if u.scheme != 'https' or not u.hostname or u.username or u.password or u.port not in (None,443): raise ValueError('Invalid publisher URL')
    if u.hostname=='localhost' or u.hostname.endswith(('.localhost','.local','.internal')):raise ValueError('Local network download URL is not allowed')
    try: address=ipaddress.ip_address(u.hostname)
    except ValueError: address=None
    if address is not None and not address.is_global:raise ValueError('Private network download URL is not allowed')
    if not isinstance(asset.get('size',0), int) or asset.get('size',0)<0: raise ValueError('Invalid package size')
    digest = asset.get('digest')
    if digest and not re.fullmatch('sha256:[a-fA-F0-9]{64}', digest): raise ValueError('Invalid publisher checksum')

def sourceforge(source):
    import xml.etree.ElementTree as ET
    project, folder = source['project'], source['folder']
    tree = ET.fromstring(fetch_bytes('https://sourceforge.net/projects/'+project+'/rss?path=/'+quote(folder)))
    assets=[]; version=None
    for item in tree.findall('./channel/item'):
        url=item.findtext('link',''); prefix='https://sourceforge.net/projects/'+project+'/files/'+folder+'/'
        if not url.startswith(prefix): continue
        parts=unquote(url[len(prefix):]).split('/')
        if len(parts)!=3 or parts[-1]!='download' or not parts[1].endswith('.iso'): continue
        if version is None: version=parts[0]
        if parts[0]!=version: continue
        media=item.find('{http://video.search.yahoo.com/mrss/}content')
        asset={'id':parts[1], 'name':parts[1], 'url':'https://downloads.sourceforge.net/project/'+project+'/'+folder+'/'+quote(parts[0])+'/'+quote(parts[1]), 'size':int(media.get('filesize','0')) if media is not None else 0, 'platform':'Boot ISO', 'architecture':architecture(parts[1]), 'digest':None}
        validate_asset(asset); assets.append(asset)
    if not assets: raise ValueError('No stable ISO in publisher feed')
    # The checksum filename is discovered from the release feed, not tied to a release number.
    for item in tree.findall('./channel/item'):
        url=item.findtext('link','')
        if '/'+str(version)+'/' not in url: continue
        name=unquote(url).split('/')[-2]
        if name.lower() not in ('sha256sum.txt','sha256sums','sha256sums.txt','checksums.txt'): continue
        text=fetch_bytes(url.replace('https://sourceforge.net/projects/'+project+'/files/','https://downloads.sourceforge.net/project/'+project+'/').removesuffix('/download'),1_000_000).decode('utf-8')
        for asset in assets:
            match=re.search(r'(?im)^([a-f0-9]{64})\s+\*?'+re.escape(asset['name'])+r'\s*$',text)
            if match: asset['digest']='sha256:'+match[1].lower()
        break
    return {'version':version, 'assets':assets}

def platform_for(name, supported):
    n = name.lower()
    if any(s in n for s in ('macos', 'darwin', '-mac', 'osx')) or n.endswith(('.dmg', '.pkg')): return 'macOS'
    if any(s in n for s in ('linux', 'appimage')) or n.endswith(('.deb', '.rpm')): return 'Linux'
    if any(s in n for s in ('windows', '-win')) or n.endswith(('.exe', '.msi', '.msix', '.msixbundle')): return 'Windows'
    return supported[0] if len(supported) == 1 else 'Other / check filename'

def options(root, tool_id, live=False):
    catalog = json.loads((root / 'assets/toolkit-manifest.json').read_text('utf-8'))
    tool = next((t for t in catalog if t['id'] == tool_id), None)
    if not tool: raise ValueError('Unknown tool')
    result = {'tool': tool_id, 'name': tool['name'], 'source': tool['officialDownload'], 'folder': tool['localFolder'], 'assets': [], 'platforms': tool['os']}
    if tool['license'] == 'Paid': return result
    source=sources(root).get(tool_id,{})
    cached=cached_catalog(root).get('tools',{}).get(tool_id,{})
    if not live and cached.get('assets') and cached.get('status')=='ready':
        for asset in cached['assets']: validate_asset(asset)
        result.update({k:cached[k] for k in ('assets','version','checkedAt','provider','recommended') if k in cached})
        return result
    if not live:
        result['reason']=cached.get('reason') or cached.get('error') or 'No automatic package is currently published in the toolkit repository. Refresh the catalog or use the publisher window.'
        result['status']=cached.get('status','manual')
        return result
    if source.get('provider')=='sourceforge':
        result.update(sourceforge(source)); return result
    if source.get('provider')=='winget':
        # YAML resolution runs in Actions; the desktop has no package-manager dependency.
        if cached.get('assets'):
            for asset in cached['assets']: validate_asset(asset)
            result.update(cached)
        else: result['reason']='Package catalog has not resolved this publisher yet. Refresh the catalog or use the publisher window.'
        return result
    if source.get('provider')=='sysinternals':
        name=source['file']
        result['assets']=[{'id':name,'name':name,'url':'https://download.sysinternals.com/files/'+name,'size':0,'digest':None,'platform':'Windows','architecture':'universal'}]
        return result
    repo = source.get('repo') or ('ip7z/7zip' if tool_id == '7zip' else None)
    for value in (() if source.get('repo') else (tool['officialDownload'], tool['officialWebsite'])):
        parts = urlsplit(value)
        path = parts.path.strip('/').split('/')
        if parts.hostname == 'github.com' and len(path) >= 2 and all(re.fullmatch(r'[A-Za-z0-9_.-]+', p) for p in path[:2]): repo = '/'.join(path[:2]); break
    if repo:
        release = fetch_json('https://api.github.com/repos/' + repo + '/releases/latest')
        # The GitHub API follows repository transfers; use its canonical repository URL.
        canonical=release.get('html_url','').split('/releases/')[0]
        prefix=canonical+'/releases/download/' if re.fullmatch(r'https://github.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',canonical) else 'https://github.com/'+repo+'/releases/download/'
        result['version'] = release.get('tag_name', '')
        for asset in release.get('assets', []):
            name, url = asset.get('name', ''), asset.get('browser_download_url', '')
            if re.search(r'(^|[-_.])(src|source|sdk)([-_.]|$)', name, re.I) or (tool_id == '7zip' and name.startswith('lzma')): continue
            if not name or name != Path(name).name or '\\' in name or ':' in name: continue
            if not url.lower().startswith(prefix.lower()): continue
            if not re.search(r'\.(exe|msi|msix|msixbundle|zip|7z|gz|xz|bz2|dmg|pkg|deb|rpm|appimage|iso)$', name, re.I) and not (name.lower().endswith('.ps1') and any(fnmatch.fnmatchcase(name.casefold(),p.casefold()) for p in tool.get('inventoryPatterns',[]) if p.lower().endswith('.ps1'))): continue
            result['assets'].append({'id': str(asset['id']), 'name': name, 'url': url, 'size': asset.get('size', 0), 'digest': asset.get('digest'), 'platform': platform_for(name, tool['os'])})
    elif tool_id == 'sysinternals':
        result['assets'] = [{'id': 'suite', 'name': 'SysinternalsSuite.zip', 'url': 'https://download.sysinternals.com/files/SysinternalsSuite.zip', 'size': 0, 'digest': None, 'platform': 'Windows'}]
    for asset in result['assets']:
        asset['architecture']=architecture(asset['name'])
        if tool.get('bootable') and asset['name'].endswith('.iso'): asset['platform']='Boot ISO'
    return result

def save_selected(root, tool_id, selected, safe_path, progress, resolved=None):
    info = resolved or options(root, tool_id)
    assets = {a['id']: a for a in info['assets']}
    if not selected or len(selected) != len(set(selected)) or any(i not in assets for i in selected): raise ValueError('Invalid selection; reload the publisher choices')
    folder = safe_path(root, info['folder'])
    folder.mkdir(parents=True, exist_ok=True)
    results = []
    for index, key in enumerate(selected, 1):
        asset = assets[key]
        validate_asset(asset)
        destination = safe_path(root, info['folder'] + '/' + asset['name'])
        if destination.exists():
            expected=asset.get('digest') or ''
            actual=hashlib.sha256()
            with destination.open('rb') as existing:
                for block in iter(lambda:existing.read(1024*1024),b''):actual.update(block)
            if expected and expected!='sha256:'+actual.hexdigest():
                # Keep the older package and use a distinct checksum-based name for the new release.
                destination=safe_path(root,info['folder']+'/'+destination.stem+'-'+expected[7:19]+destination.suffix)
                if destination.exists():
                    verify=hashlib.sha256()
                    with destination.open('rb') as existing:
                        for block in iter(lambda:existing.read(1024*1024),b''):verify.update(block)
                    if 'sha256:'+verify.hexdigest()!=expected:raise ValueError('Existing package conflicts with publisher checksum')
                    record_saved(root,tool_id,info,key,destination,verify.hexdigest(),safe_path)
                    results.append('Kept existing: '+destination.name);continue
            elif not expected and info.get('version'):
                # Unversioned publisher filenames need a new path when their release marker changes.
                suffix=hashlib.sha256(str(info['version']).encode()).hexdigest()[:12]
                alternate=safe_path(root,info['folder']+'/'+destination.stem+'-'+suffix+destination.suffix)
                try: receipts=json.loads(safe_path(root,'assets/download-receipts.json').read_text('utf-8')).get(tool_id,[])
                except (OSError,ValueError): receipts=[]
                known=next((r for r in receipts if r.get('version')==info['version'] and r.get('path')==destination.relative_to(root).as_posix() and r.get('sha256')==actual.hexdigest()),None)
                if known:results.append('Kept existing: '+destination.name);continue
                if alternate.exists():
                    known=next((r for r in receipts if r.get('version')==info['version'] and r.get('path')==alternate.relative_to(root).as_posix() and r.get('size')==alternate.stat().st_size),None)
                    if known:results.append('Kept existing: '+alternate.name);continue
                    raise ValueError('Existing versioned package requires manual review: '+alternate.name)
                destination=alternate
            else:
                if expected:record_saved(root,tool_id,info,key,destination,actual.hexdigest(),safe_path)
                results.append('Kept existing: ' + asset['name'] + ('' if expected else ' (no publisher checksum; compare manually)')); continue
        size = asset.get('size', 0)
        if size and 2 * size + 100_000_000 > shutil.disk_usage(folder).free: raise ValueError('Not enough free space for download staging')
        temporary = safe_path(root, info['folder'] + '/.' + asset['name'] + '.' + secrets.token_hex(6) + '.partial')
        digest = hashlib.sha256(); total = 0
        try:
            with open_package(asset) as response, temporary.open('xb') as output:
                transfer_size = size or int(getattr(response, 'headers', {}).get('Content-Length', '0'))
                final = urlsplit(response.url)
                if not allowed_download(asset, response.url): raise ValueError('Unexpected publisher redirect')
                if 'text/html' in getattr(response,'headers',{}).get('Content-Type','').lower(): raise ValueError('Publisher returned a web page instead of a package')
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk: break
                    total += len(chunk)
                    if total > 8_000_000_000: raise ValueError('Package exceeds 8 GB transfer limit')
                    output.write(chunk); digest.update(chunk)
                    progress({'message': 'Downloading ' + asset['name'], 'file': asset['name'], 'received': total, 'total': transfer_size or None, 'index': index, 'count': len(selected), 'stage': 'download'})
            if size and total != size: raise ValueError('Incomplete publisher download')
            if total == 0: raise ValueError('Empty publisher download')
            expected = asset.get('digest') or ''
            if expected.startswith('sha256:') and digest.hexdigest() != expected[7:]: raise ValueError('Publisher SHA256 mismatch')
            # Exclusive creation prevents overwriting files created during the transfer.
            with destination.open('xb') as output, temporary.open('rb') as source:
                try: shutil.copyfileobj(source, output)
                except Exception:
                    output.close(); destination.unlink(); raise
            results.append('Saved: ' + str(destination) + (' (SHA256 verified)' if expected.startswith('sha256:') else ' (no publisher SHA256 supplied)'))
            # Commit each receipt immediately, so an interrupted multi-file job can resume safely.
            record_saved(root,tool_id,info,key,destination,digest.hexdigest(),safe_path)
        finally:
            if temporary.exists(): temporary.unlink()
    return '\n'.join(results) + '\nPackages saved. The following scan extracts recognized ZIP packages; installers are never run automatically.'

def record_saved(root, tool_id, info, key, destination, checksum, safe_path):
    receipt_path = safe_path(root, 'assets/download-receipts.json')
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    try: receipts = json.loads(receipt_path.read_text('utf-8'))
    except (OSError, ValueError): receipts = {}
    previous = {r['path']: r for r in receipts.get(tool_id, [])}
    relative=destination.relative_to(root).as_posix()
    previous[relative]={'path':relative,'size':destination.stat().st_size,'version':info.get('version',''),'sha256':checksum,'assetId':key,'savedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    receipts[tool_id]=list(previous.values())
    if info.get('version'): receipts.setdefault('_latest',{})[tool_id]=info['version']
    temp=receipt_path.with_name('.download-receipts-'+secrets.token_hex(6)+'.tmp')
    temp.write_text(json.dumps(receipts,indent=2),encoding='utf-8');os.replace(temp,receipt_path)

def allowed_download(asset, url):
    parsed=urlsplit(url); host=parsed.hostname or ''
    if parsed.scheme!='https' or parsed.username or parsed.password or parsed.port not in (None,443): return False
    origin=urlsplit(asset['url']).hostname
    if origin=='github.com': return host in ('github.com','release-assets.githubusercontent.com','objects.githubusercontent.com')
    if origin=='downloads.sourceforge.net': return host=='downloads.sourceforge.net' or host.endswith('.dl.sourceforge.net')
    return host==origin or host in asset.get('redirectHosts',[])

def open_package(asset):
    validate_asset(asset)
    class Redirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, message, headers, url):
            if not allowed_download(asset,url):raise ValueError('Unexpected publisher redirect; refresh the download catalog')
            validate_asset(dict(asset,url=url))
            return super().redirect_request(request,fp,code,message,headers,url)
    request=urllib.request.Request(asset['url'],headers={'User-Agent':'MasterITToolkit'})
    return urllib.request.build_opener(Redirect()).open(request,timeout=60)

def recommended(info, platform='Windows', arch='x64', portable=False):
    """One package per platform/architecture, never every redundant release asset."""
    groups={}
    for asset in info.get('assets',[]):
        p=asset.get('platform','Other / check filename'); a=asset.get('architecture') or architecture(asset['name'])
        if p not in ('Windows','Linux','macOS','Boot ISO'): continue
        if platform!='All' and p not in (platform,'Boot ISO'): continue
        if arch!='All' and a not in (arch,'universal') and not (p=='Windows' and arch=='x64' and a=='x86'): continue
        name=asset['name'].lower()
        if re.search(r'debug|symbols|pdb|source|sdk|\.blockmap|\btest\b',name): continue
        if p=='Boot ISO' and not name.endswith('.iso'): continue
        group=(p, a if arch=='All' else arch)
        score=(0 if a==arch else 1 if a=='universal' else 2, 0 if (portable and any(s in name for s in ('portable','bin.','binary'))) else 1,
               0 if name.endswith(('.iso','.msi','.dmg','.appimage')) else 1 if name.endswith('.exe') else 2, name)
        if group not in groups or score<groups[group][0]: groups[group]=(score,asset)
    return [value[1] for value in sorted(groups.values(),key=lambda v:v[0])]

def bulk_download(root, selection, safe_path, progress, scan, completed, cancelled=lambda:False):
    platform,arch=selection.get('platform','Windows'),selection.get('architecture','x64')
    mode=selection.get('mode','missing')
    catalog=json.loads((root/'assets/toolkit-manifest.json').read_text('utf-8'))
    selected=selection.get('tools')
    if selected is not None:
        known={t['id'] for t in catalog}
        if not isinstance(selected,list) or not 1 <= len(selected) <= 500 or any(not isinstance(id,str) or id not in known for id in selected):
            raise ValueError('Select valid tools before starting the queue')
        catalog=[t for t in catalog if t['id'] in selected]
    progress({'message':'Scanning existing files before downloading…','stage':'scan'})
    scan();completed()
    inventory=json.loads((root/'assets/js/local-inventory.js').read_text('utf-8-sig').split('window.LOCAL_INVENTORY =',1)[1].strip().rstrip(';')).get('tools',{})
    results=[]; counts={'downloaded':0,'present':0,'manual':0,'failed':0,'notApplicable':0}
    eligible=[t for t in catalog if t.get('officialDownload') and t.get('kind') not in ('Built-in','Documentation','Script','Online')]
    # Respect the user's preference for free/open-source packages first.
    eligible.sort(key=lambda t:(t.get('license') not in ('Open source','Free'),t.get('priority','P3'),t['name']))
    for index,tool in enumerate(eligible,1):
        if cancelled(): results.append('Queue cancelled; completed packages were kept.');break
        id=tool['id']; record=inventory.get(id,{})
        progress({'tool':id,'message':'Resolving '+tool['name'],'stage':'resolve','index':index,'count':len(eligible)})
        if mode=='missing' and (record.get('downloaded') or record.get('installed')):
            counts['present']+=1;continue
        if tool.get('kind') in ('Driver','Firmware') or tool.get('license') not in ('Open source','Free','Freemium','Personal free'):
            counts['manual']+=1;results.append('↗ '+tool['name']+': edition, license or hardware selection required');continue
        try:
            info=options(root,id)
            if not info['assets']:
                counts['manual']+=1;results.append('↗ '+tool['name']+': '+info.get('reason','Publisher-managed download'));continue
            assets=recommended(info,platform,arch,tool.get('portable',False))
            if not assets: counts['notApplicable']+=1;continue
            for asset in assets:
                for attempt in range(3):
                    if cancelled(): break
                    try:
                        report=save_selected(root,id,[asset['id']],safe_path,
                            lambda state:progress(dict(state,tool=id,queueIndex=index,queueCount=len(eligible))),resolved=info)
                        results.append(tool['name']+': '+report.split('\n')[0]);break
                    except (urllib.error.URLError,TimeoutError) as error:
                        if attempt==2: raise
                        progress({'tool':id,'message':'Retrying '+tool['name']+' ('+str(attempt+2)+'/3)','stage':'retry'})
                        time.sleep(2**attempt)
                if cancelled(): break
            if cancelled(): results.append('Queue cancelled; completed packages were kept.');break
            counts['downloaded']+=1
            progress({'tool':id,'message':'Organizing '+tool['name'],'stage':'scan'})
            scan();completed()
        except Exception as error:
            counts['failed']+=1;results.append('✗ '+tool['name']+': '+str(error))
    summary='✓ Queue finished · '+str(counts['downloaded'])+' processed · '+str(counts['present'])+' already present\n↗ '+str(counts['manual'])+' need publisher selection · '+str(counts['failed'])+' failed · '+str(counts['notApplicable'])+' outside selected platform'
    path=safe_path(root,'70_DOCUMENTATION/Service-Notes/download-queue.json');path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps({'counts':counts,'results':results,'selection':selection,'finishedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2),encoding='utf-8')
    return summary+'\n'+'\n'.join(results)

def check_updates(root, safe_path):
    refresh_catalog(root,safe_path)
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
