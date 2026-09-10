"""Guided PC setup profiles. Run with Python 3.9+; no arbitrary shell commands."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import launcher
import portable_tools
import activity_store
import tool_downloads
import install_tools

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list',action='store_true')
    parser.add_argument('--profile',help='Built-in build-* or saved custom-* ID')
    parser.add_argument('--download',action='store_true',help='Download missing supported packages only; does not install')
    parser.add_argument('--architecture',choices=['x64','arm64','x86'],default='x64')
    parser.add_argument('--mode',choices=['manual','automatic'],default='manual')
    args=parser.parse_args()
    definitions=json.loads((ROOT/'assets/build-profiles.json').read_text('utf-8'))
    store=activity_store.Store(ROOT,launcher.safe_path)
    custom=store.workspace().get('customWorkflows',{})
    definitions.update(portable_tools.validate_custom_workflows(ROOT,custom))
    if args.list or not args.profile:
        for id,definition in definitions.items():print(id+' | '+definition['name']+' | '+definition['platform'])
        return
    if args.profile not in definitions:parser.error('Unknown profile; use --list')
    definition=definitions[args.profile]
    if args.download:
        ids=list(dict.fromkeys(step['tool'] for step in definition['steps'] if step.get('tool')))
        if not ids:print('Manual checkpoints only; no catalog packages.');return
        def scan():subprocess.run([sys.executable,str(ROOT/'60_SCRIPTS/Inventory/update_toolkit_inventory.py')],cwd=ROOT,check=True)
        print(tool_downloads.bulk_download(ROOT,{'tools':ids,'platform':definition['platform'],'architecture':args.architecture,'mode':'missing'},launcher.safe_path,lambda state:print(state.get('message','')),scan,lambda:None))
        return
    print('Guided setup: '+definition['name']+'. Verify backups before changes. Installs require review; automatic mode only launches portable tools.')
    flow=None
    def publish(state):
        w=state['workflow'];print('\nStep '+str(w['step']+1)+'/'+str(w['count'])+': '+w['current']['text']);print(state['message'])
        if w['current'].get('url'):print(w['current']['url'])
        if not w['waiting']:return
        while True:
            choice=input('[n] verified / [s] skip / [r] run portable / [i] review installer / [q] stop: ').strip().lower()
            body={'run':w['id'],'step':w['step']}
            if choice=='i':
                if w['current'].get('action')!='install':print('Not an install step.');continue
                info=install_tools.options(ROOT,w['current']['tool'],launcher.safe_path)
                print(info['reason'] or 'Review the signed installer and recovery prompts.')
                if info['installedOnHost']:print('Already detected on this PC; verify before reinstalling.')
                files=[file for file in info['files'] if file.get('signature',{}).get('status')=='Valid']
                for index,file in enumerate(files,1):print(str(index)+': '+file['name']+' | '+file['signature'].get('publisher',''))
                index=input('Installer number, or Enter to cancel: ')
                if not index.isdigit() or not 1<=int(index)<=len(files):continue
                file=files[int(index)-1];body.update(command='install',package=file['path'],sha256=file['sha256'])
            elif choice in ('n','s','r','q'):
                if choice=='r' and w['current'].get('action')=='manual':print('Complete this checkpoint manually.');continue
                body['command']={'n':'next','s':'skip','r':'run','q':'stop'}[choice]
            else:continue
            flow.control(body);return
    flow=portable_tools.Workflow(ROOT,args.profile,args.mode,launcher.safe_path,publish)
    result=flow.run();print(result)
    record={'name':definition['name'],'profile':args.profile,'steps':flow.history}
    store.record('workflow',{'message':result,'stage':'complete','workflowRecord':flow.history,'workflowName':definition['name'],'workflowProfile':args.profile})

if __name__=='__main__':
    try:main()
    except (KeyboardInterrupt,EOFError):print('\nStopped. Already-open applications remain running.');sys.exit(1)
    except Exception as error:print('Setup stopped: '+str(error),file=sys.stderr);sys.exit(1)
