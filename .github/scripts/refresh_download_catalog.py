"""Resolve reviewed publisher identities into the repository's public download catalog.
Downloads metadata only. Never runs or redistributes publisher installers.
"""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request
from urllib.parse import urlsplit, unquote

ROOT=Path(__file__).resolve().parents[2]/'MASTER-IT-TOOLKIT'
sys.path.insert(0,str(ROOT))
import tool_downloads as downloads

def winget(source):
    import yaml  # CI-only, safe_load; no YAML dependency in the desktop app.
    package=source['package']
    path='manifests/'+package[0].lower()+'/'+package.replace('.','/')
    entries=downloads.fetch_json('https://api.github.com/repos/microsoft/winget-pkgs/contents/'+path)
    versions=[x['name'] for x in entries if x['type']=='dir' and re.fullmatch(r'[0-9][0-9.\-_]*',x['name'])]
    if not versions: raise ValueError('No stable WinGet version')
    version=max(versions,key=lambda x:tuple(int(p) for p in re.findall(r'\d+',x)))
    url='https://raw.githubusercontent.com/microsoft/winget-pkgs/master/'+path+'/'+version+'/'+package+'.installer.yaml'
    manifest=yaml.safe_load(downloads.fetch_bytes(url).decode('utf-8-sig'))
    assets=[]
    for installer in manifest.get('Installers',[]):
        link=installer.get('InstallerUrl',''); digest=installer.get('InstallerSha256','')
        if not re.fullmatch(r'[a-fA-F0-9]{64}',digest) or not link.startswith('https://'): continue
        # Blender's download pages now use this official mirror. Keep the
        # manifest's exact release path and SHA256; never rewrite other hosts.
        if package=='BlenderFoundation.Blender' and re.fullmatch(r'https://download\.blender\.org/release/Blender[0-9.]+/blender-[0-9.]+-windows-(?:x64|arm64)\.(?:msi|zip)',link):
            link=link.replace('https://download.blender.org/','https://mirror.blender.org/',1)
        locale=installer.get('InstallerLocale',manifest.get('InstallerLocale','en-US'))
        if locale and not locale.lower().startswith('en'): continue
        name=unquote(urlsplit(link).path.rsplit('/',1)[-1])
        kind=installer.get('InstallerType',manifest.get('InstallerType','exe'))
        if not re.search(r'\.(exe|msi|msix|msixbundle|zip|7z)$',name,re.I):
            name=package+'-'+version+'-'+installer['Architecture']+('.msi' if kind=='msi' else '.zip' if kind=='zip' else '.exe')
        # Same filename may cover several architectures or scopes; identity includes URL + hash.
        asset={'id':hashlib.sha256((link+digest).encode()).hexdigest()[:20], 'name':name,'url':link,'digest':'sha256:'+digest.lower(),'size':0,'platform':'Windows','architecture':installer.get('Architecture','neutral').replace('neutral','universal')}
        downloads.validate_asset(asset)
        if not any(a['id']==asset['id'] for a in assets): assets.append(asset)
    if not assets: raise ValueError('No HTTPS packages with SHA256 in WinGet manifest')
    return {'assets':assets,'version':str(manifest.get('PackageVersion',version)),'metadataSource':url}

def fingerprint(entry):
    return (entry.get('version',''),entry.get('sourceRevision',''),sorted((a['url'],a.get('digest') or '') for a in entry.get('assets',[])))

def probe(entry):
    """Check recommended endpoints and record publisher CDN redirects; read one byte only."""
    chosen={a['id']:a for p,arch in [('Windows','x64'),('Linux','x64'),('macOS','arm64')] for a in downloads.recommended(entry,p,arch)}
    # Resolve Blender's rotating redirector for every offered architecture.
    chosen.update({a['id']:a for a in entry['assets'] if urlsplit(a['url']).hostname=='mirror.blender.org'})
    hosts=set()
    class Redirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,request,fp,code,message,headers,url):
            downloads.validate_asset({'name':'probe.exe','url':url})
            hosts.add(urlsplit(url).hostname)
            return super().redirect_request(request,fp,code,message,headers,url)
    for asset in chosen.values():
        # Match the desktop request: some publishers route Range requests
        # differently, hiding redirects that a real download will follow.
        request=urllib.request.Request(asset['url'],headers={'User-Agent':'MasterITToolkit'})
        with urllib.request.build_opener(Redirect()).open(request,timeout=30) as response:
            if 'text/html' in response.headers.get('Content-Type','').lower():raise ValueError('Publisher returned HTML instead of '+asset['name'])
            response.read(1)
            if urlsplit(asset['url']).hostname=='mirror.blender.org' and re.fullmatch(r'sha256:[a-f0-9]{64}',asset.get('digest') or ''):
                # Pin the official redirector's selected mirror for this catalog
                # revision; a later request could otherwise choose a new host.
                downloads.validate_asset(dict(asset,url=response.url))
                asset['url']=response.url
    for asset in entry['assets']:
        asset['redirectHosts']=sorted(hosts)

def generate(previous):
    sources=downloads.sources(ROOT); now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    tools=json.loads((ROOT/'assets/toolkit-manifest.json').read_text('utf-8'))
    def resolve(tool):
        id=tool['id']; source=sources.get(id); old=previous.get('tools',{}).get(id,{})
        entry={'name':tool['name'],'source':tool.get('officialDownload',''),'checkedAt':now,'assets':[]}
        if not tool.get('officialDownload') or tool['kind'] in ('Built-in','Documentation','Script','Online'):
            entry.update(status='not-applicable',reason='Included with the OS/toolkit, package-manager command, or online service.');return id,entry
        if not source or tool['license']=='Paid':
            entry.update(status='manual',reason='Publisher selection required: no reviewed automatic resolver for this edition.');return id,entry
        try:
            result=winget(source) if source['provider']=='winget' else downloads.options(ROOT,id,live=True)
            if source['provider']=='sysinternals':
                request=urllib.request.Request(result['assets'][0]['url'],method='HEAD',headers={'User-Agent':'MasterITToolkit'})
                with urllib.request.urlopen(request,timeout=30) as response:
                    result['sourceRevision']=response.headers.get('ETag','') or response.headers.get('Last-Modified','')
                    result['version']=response.headers.get('Last-Modified','')
                    result['assets'][0]['size']=int(response.headers.get('Content-Length','0'))
            if not result['assets']: raise ValueError('Publisher returned no supported release packages')
            for asset in result['assets']:downloads.validate_asset(asset)
            probe(result)
            entry.update(result);entry.update(status='ready',provider=source['provider'],checkedAt=now)
            entry['recommended']={p+'/'+a:[x['id'] for x in downloads.recommended(entry,p,a,tool.get('portable',False))] for p in ('Windows','Linux','macOS','Boot ISO','All') for a in ('x64','x86','arm64','universal','All')}
        except Exception as error:
            # Preserve the last good link set for diagnosis, but don't silently advertise it as current.
            entry.update({k:old[k] for k in ('assets','version','lastSuccess') if k in old})
            entry.update(status='error',provider=source['provider'],error=str(error),reason='Publisher lookup failed; use the publisher window until refreshed.')
        if entry['status']=='ready':entry['lastSuccess']=now
        return id,entry
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        entries=dict(pool.map(resolve,tools))
    changes=[]
    for id,entry in entries.items():
        old=previous.get('tools',{}).get(id,{})
        if entry['status']=='ready' and (fingerprint(entry)!=fingerprint(old) or old.get('status')=='error'):
            changes.append({'tool':id,'name':entry['name'],'kind':'available' if not old else 'updated','version':entry.get('version',''),'previous':old.get('version','')})
        elif entry['status']=='error' and old.get('status')!='error':
            changes.append({'tool':id,'name':entry['name'],'kind':'source-error','error':entry['error']})
    # Carry the most recent change list across no-change runs so clients can see what changed.
    revision=hashlib.sha256(json.dumps({k:[v['status'],fingerprint(v)] for k,v in entries.items()},sort_keys=True).encode()).hexdigest()[:20]
    return {'schema':1,'generatedAt':now,'revision':revision,'tools':entries,'changes':changes or previous.get('changes',[])},changes

ISSUE_TITLE='Download catalog: sources needing attention'
ISSUE_MARKER='<!-- master-it-toolkit:catalog-health:v1 -->'

def managed_issue(issue):
    author=issue.get('author',{})
    bot=author.get('is_bot') and author.get('login') in ('app/github-actions','github-actions[bot]')
    body=issue.get('body') or ''
    return bool(bot and (ISSUE_MARKER in body or
        re.fullmatch(r'Download catalog [a-f0-9]{20}: [0-9]+ changes',issue.get('title','')) and
        body.startswith('The download catalog was refreshed. Downloads still come from the original publishers.')))

def notify(catalog):
    # Reconcile the complete health snapshot even when the revision did not change.
    # Routine releases stay in the catalog/Actions summary, not open GitHub issues.
    repo=os.environ['GITHUB_REPOSITORY'];owner=repo.split('/')[0]
    existing=json.loads(subprocess.check_output(['gh','issue','list','--repo',repo,'--state','all','--limit','1000','--json','number,title,body,state,author'],text=True))
    owned=sorted([i for i in existing if managed_issue(i)],key=lambda i:i['number'])
    trackers=[i for i in owned if ISSUE_MARKER in (i.get('body') or '')]
    errors=sorted([(id,t) for id,t in catalog['tools'].items() if t.get('status')=='error'])
    tracker=trackers[0] if trackers else (owned[-1] if errors and owned else None)
    clean=lambda value:str(value).replace('|','/').replace('\n',' ').replace('\r',' ')[:500]
    rows=[ISSUE_MARKER,'This automatically maintained issue lists current download-source failures. It closes when all sources recover and reopens if a later check finds a problem.','',
          'Normal version updates are recorded in the toolkit catalog and GitHub Actions summaries.','']
    if errors:
        rows+=['| Tool | Current problem |','| --- | --- |']
        rows+=['| '+clean(t.get('name',id))+' | '+clean(t.get('error') or t.get('reason') or 'Publisher lookup failed')+' |' for id,t in errors]
        rows+=['','Use the official publisher page while an automatic source is unavailable.']
    else:rows+=['All monitored download sources have recovered. No action is needed.']
    content='\n'.join(rows)+'\n'
    body=Path(os.environ.get('RUNNER_TEMP','.'))/'catalog-health.md';body.write_text(content,encoding='utf-8')
    def run(*args):subprocess.run(['gh','issue',*args,'--repo',repo],check=True)
    if tracker:
        if tracker.get('body')!=content or tracker.get('title')!=ISSUE_TITLE:
            run('edit',str(tracker['number']),'--title',ISSUE_TITLE,'--body-file',str(body))
        if errors and tracker['state']=='CLOSED':run('reopen',str(tracker['number']))
        elif not errors and tracker['state']=='OPEN':run('close',str(tracker['number']),'--reason','completed')
    elif errors:
        # Create the replacement before closing old notifications so failures are never lost.
        run('create','--title',ISSUE_TITLE,'--body-file',str(body),'--assignee',owner)
    for issue in owned:
        if issue is not tracker and issue['state']=='OPEN':run('close',str(issue['number']),'--reason','completed')

def summary(catalog,changes):
    destination=os.environ.get('GITHUB_STEP_SUMMARY')
    if not destination:return
    lines=['## Download catalog refresh','',str(len(changes))+' catalog changes; '+str(sum(t.get('status')=='error' for t in catalog['tools'].values()))+' sources need attention.','']
    for change in changes:
        lines.append('- '+str(change.get('name',change['tool'])).replace('\n',' ')+' — '+str(change['kind'])+' '+str(change.get('version','')))
    with Path(destination).open('a',encoding='utf-8') as out:out.write('\n'.join(lines)+'\n')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--notify',action='store_true');args=parser.parse_args()
    try:previous=json.loads(args.output.read_text('utf-8'))
    except (OSError,ValueError):previous={'tools':{}}
    result,changes=generate(previous);args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    from collections import Counter
    print(dict(Counter(x['status'] for x in result['tools'].values())))
    for id,x in result['tools'].items():
        if x['status']=='error':print(id+': '+x['error'])
    summary(result,changes)
    if args.notify:notify(result)

if __name__=='__main__':main()
