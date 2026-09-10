"""Catalog-confined portable launches and reviewed workflow checkpoints."""
import fnmatch
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import threading


def options(root, tool_id, safe_path):
    catalog = json.loads((root / 'assets/toolkit-manifest.json').read_text('utf-8'))
    tool = next((t for t in catalog if t['id'] == tool_id), None)
    if not tool: raise ValueError('Unknown tool')
    reason = ''
    files = []
    script_tool = tool_id == 'winutil'
    if os.name != 'nt': reason = 'Portable launching currently supports Windows EXEs. Use the native application on this platform.'
    elif tool.get('kind') != 'Portable' or 'Windows' not in tool.get('os', []):
        reason = 'Use this tool’s installation, boot-media or command instructions.'
    if not reason:
        try:
            text = (root / 'assets/js/local-inventory.js').read_text('utf-8-sig')
            inventory = json.loads(text.split('window.LOCAL_INVENTORY =', 1)[1].strip().rstrip(';'))
            folder = safe_path(root, tool['localFolder'])
            patterns = tool.get('inventoryPatterns', [])
            for item in inventory.get('tools', {}).get(tool_id, {}).get('files', []):
                try:
                    path = safe_path(root, item['path']); path.relative_to(folder)
                    if path.suffix.lower() != ('.ps1' if script_tool else '.exe') or not path.is_file(): continue
                    if re.search(r'setup|(?:^|[-_.])install(?:er)?(?:[-_.]|$)', path.name, re.I): continue
                    if tool_id == '7zip' and re.match(r'7z\d', path.name, re.I): continue
                    if not any(fnmatch.fnmatchcase(path.name.casefold(), p.casefold()) for p in patterns): continue
                    if not path.stat().st_size: continue
                    files.append({'path': item['path'], 'fullPath': str(path), 'name': path.name})
                except (OSError, ValueError, KeyError): continue
        except (OSError, ValueError, IndexError): pass
        if not files: reason = 'No scanned WinUtil PowerShell script is available. Download winutil.ps1, then scan; it does not need extraction.' if script_tool else 'No scanned portable executable is available. Download the portable edition, extract it, then scan.'
    return {'tool': tool_id, 'name': tool['name'], 'files': files[:50], 'reason': reason,
            'confirmationRequired':script_tool,'launchNote': 'Runs the downloaded PowerShell script. WinUtil requests administrator access through Windows UAC. Choose changes inside WinUtil; no preset or automatic tweaks are supplied.' if script_tool else ''}


def launch(root, tool_id, executable, safe_path, progress, stopped=lambda: False):
    available = options(root, tool_id, safe_path)
    if executable not in [f['path'] for f in available['files']]:
        raise ValueError(available['reason'] or 'Executable is not in this tool’s scanned inventory')
    path = safe_path(root, executable)
    # Arguments are fixed here, never supplied by the browser. WinUtil owns its UAC prompt.
    if stopped(): return 'Workflow stopped before launch.'
    try:
        command=[str(path)]
        kwargs={}
        if path.suffix.lower()=='.ps1':
            if tool_id!='winutil':raise ValueError('This script is not enabled for launching')
            powershell=shutil.which('powershell.exe')
            if not powershell:raise ValueError('Windows PowerShell is unavailable')
            command=[powershell,'-NoProfile','-ExecutionPolicy','Bypass','-File',str(path)]
            kwargs['creationflags']=getattr(subprocess,'CREATE_NEW_CONSOLE',0)
        process = subprocess.Popen(command, cwd=str(path.parent), shell=False, **kwargs)
    except OSError as error:
        if getattr(error, 'winerror', None) == 740:
            raise ValueError('This tool requires administrator access. Open it explicitly as administrator; this workflow will not elevate automatically.') from error
        raise
    progress('WinUtil PowerShell started. Check the Windows UAC prompt and the WinUtil window.' if tool_id=='winutil' else 'Tool opened. Follow its prompts, then close it and review the result.')
    while True:
        try:
            code = process.wait(timeout=0.5)
            break
        except subprocess.TimeoutExpired:
            if stopped(): return 'Workflow stopped. The already-open application remains running.'
    if code: raise RuntimeError('Application exited with code ' + str(code) + '. Review its results before continuing.')
    if tool_id=='winutil':return 'WinUtil launcher exited. WinUtil may still be open in its elevated window; check the UAC prompt and application. No tweaks were selected by the toolkit.'
    return 'Application exited. Verify its results; a helper process may still be open. Exit does not certify success.'


def validate_custom_workflows(root, definitions):
    catalog={t['id'] for t in json.loads((root/'assets/toolkit-manifest.json').read_text('utf-8'))}
    if not isinstance(definitions,dict) or len(definitions)>100: raise ValueError('Up to 100 custom workflows supported')
    for id,definition in definitions.items():
        if not re.fullmatch(r'custom-[a-zA-Z0-9-]{1,80}',id) or not isinstance(definition,dict): raise ValueError('Invalid custom workflow')
        if not isinstance(definition.get('name'),str) or not 1<=len(definition['name'].strip())<=120: raise ValueError('Name must be 1–120 characters')
        if definition.get('platform') not in ('Windows','Linux','macOS'): raise ValueError('Choose a supported platform')
        steps=definition.get('steps')
        if not isinstance(steps,list) or not 1<=len(steps)<=200: raise ValueError('Use 1–200 steps')
        for step in steps:
            if not isinstance(step,dict) or set(step)-{'text','tool','action','url'}: raise ValueError('Invalid step fields')
            if not isinstance(step.get('text'),str) or not 1<=len(step['text'].strip())<=4000: raise ValueError('Each step needs instructions')
            if step.get('tool') and step['tool'] not in catalog: raise ValueError('Unknown step tool')
            if step.get('action','manual') not in ('manual','install','run'): raise ValueError('Unsupported step action')
            if step.get('action') in ('install','run') and not step.get('tool'): raise ValueError('Choose a tool for this action')
            if step.get('url') and (not isinstance(step['url'],str) or not step['url'].startswith('https://') or len(step['url'])>2000): raise ValueError('Documentation links must use HTTPS')
    return definitions


class Workflow:
    def __init__(self, root, workflow_id, mode, safe_path, publish):
        definitions = json.loads((root / 'assets/workflows.json').read_text('utf-8'))
        if workflow_id.startswith('build-'):
            definitions.update(json.loads((root/'assets/build-profiles.json').read_text('utf-8')))
        elif workflow_id.startswith('custom-'):
            import activity_store
            custom=activity_store.Store(root,safe_path).workspace().get('customWorkflows',{})
            definitions.update(validate_custom_workflows(root,custom))
        if workflow_id not in definitions or mode not in ('manual', 'automatic'): raise ValueError('Unknown workflow or mode')
        self.definition = definitions[workflow_id]
        # A profile for another OS remains useful as a preview, but must not run here.
        import platform
        host={'Windows':'Windows','Linux':'Linux','Darwin':'macOS'}.get(platform.system())
        if self.definition.get('platform') and self.definition['platform']!=host:
            raise ValueError('This build targets '+self.definition['platform']+'. Run it on that operating system, or clone it for this PC.')
        self.root, self.safe_path, self.publish = root, safe_path, publish
        self.mode, self.id = mode, secrets.token_hex(12)
        self.condition = threading.Condition()
        self.command = None
        self.stop = False
        self.step = 0
        self.waiting = False
        self.history = []

    def state(self, message):
        self.publish(dict(workflow={'id': self.id, 'name': self.definition['name'], 'step': self.step,
            'count': len(self.definition['steps']), 'current': self.definition['steps'][self.step],
            'waiting': self.waiting, 'mode': self.mode, 'history': list(self.history)}, message=message))

    def control(self, body):
        with self.condition:
            if body.get('run') != self.id: raise ValueError('This workflow session has changed')
            command = body.get('command')
            if command == 'stop': self.stop = True
            elif command in ('next', 'skip', 'run', 'install') and self.waiting and body.get('step') == self.step and self.command is None:
                if command=='install':
                    if self.definition['steps'][self.step].get('action')!='install': raise ValueError('This is not an install step')
                    self.install_body={'tool':self.definition['steps'][self.step]['tool'],'package':body.get('package'),'sha256':body.get('sha256')}
                self.command = command
                self.waiting = False
            else: raise ValueError('This step is busy or has changed; refresh its status')
            self.condition.notify_all()

    def run_tool(self, step):
        if step.get('action')=='install': return 'Review the installer for this step. Installation needs your explicit review and may request UAC.'
        if not step.get('tool'): return 'Manual checkpoint. Complete the instructions before confirming.'
        available = options(self.root, step['tool'], self.safe_path)
        if available.get('confirmationRequired'):return 'Open this tool using its Run button and review its PowerShell/UAC confirmation before continuing the workflow.'
        if len(available['files']) != 1:
            return available['reason'] or 'Multiple executables found. Stop this workflow to choose one using Run portable, or complete this checkpoint manually in the application.'
        try:
            return launch(self.root, step['tool'], available['files'][0]['path'], self.safe_path, self.state, lambda: self.stop)
        except (OSError, ValueError, RuntimeError) as error: return 'Needs attention: ' + str(error)

    def run(self):
        for index, step in enumerate(self.definition['steps']):
            self.step = index
            if self.stop: break
            self.waiting = False
            message = step['text']
            self.state(message)
            if self.mode == 'automatic' and step.get('tool') and step.get('action','run')=='run':
                message = self.run_tool(step)
            while not self.stop:
                with self.condition:
                    self.waiting = True
                    self.state(message)
                    self.condition.wait_for(lambda: self.command is not None or self.stop)
                    command, self.command = self.command, None
                    self.waiting = False
                if self.stop: break
                if command == 'install':
                    import install_tools
                    self.state('Installing application. Follow UAC and installer prompts…')
                    try: message=install_tools.install(self.root,self.install_body,self.safe_path)
                    except Exception as error: message='Installation needs attention: '+str(error)
                    self.history.append({'step':index,'text':step['text'],'result':message})
                elif command == 'run':
                    self.state('Opening step tool…')
                    message = self.run_tool(step)
                else:
                    self.history.append({'step': index, 'text': step['text'], 'result': 'verified by technician' if command == 'next' else 'skipped — not verified'})
                    break
        return 'Workflow stopped; open applications were left running.' if self.stop else 'Workflow finished. Review the record for skipped steps; no automatic repair or clean-system certification was made.'
