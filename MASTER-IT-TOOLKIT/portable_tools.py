"""Catalog-confined portable launches and reviewed workflow checkpoints."""
import fnmatch
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import threading


def options(root, tool_id, safe_path):
    catalog = json.loads((root / 'assets/toolkit-manifest.json').read_text('utf-8'))
    tool = next((t for t in catalog if t['id'] == tool_id), None)
    if not tool: raise ValueError('Unknown tool')
    reason = ''
    files = []
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
                    if path.suffix.lower() != '.exe' or not path.is_file(): continue
                    if re.search(r'setup|(?:^|[-_.])install(?:er)?(?:[-_.]|$)', path.name, re.I): continue
                    if tool_id == '7zip' and re.match(r'7z\d', path.name, re.I): continue
                    if not any(fnmatch.fnmatchcase(path.name.casefold(), p.casefold()) for p in patterns): continue
                    if not path.stat().st_size: continue
                    files.append({'path': item['path'], 'fullPath': str(path), 'name': path.name})
                except (OSError, ValueError, KeyError): continue
        except (OSError, ValueError, IndexError): pass
        if not files: reason = 'No scanned portable executable is available. Download the portable edition, extract it, then scan.'
    return {'tool': tool_id, 'name': tool['name'], 'files': files[:50], 'reason': reason}


def launch(root, tool_id, executable, safe_path, progress, stopped=lambda: False):
    available = options(root, tool_id, safe_path)
    if executable not in [f['path'] for f in available['files']]:
        raise ValueError(available['reason'] or 'Executable is not in this tool’s scanned inventory')
    path = safe_path(root, executable)
    # Never accept command lines or arguments from the browser. No elevation or shell.
    if stopped(): return 'Workflow stopped before launch.'
    try:
        process = subprocess.Popen([str(path)], cwd=str(path.parent), shell=False)
    except OSError as error:
        if getattr(error, 'winerror', None) == 740:
            raise ValueError('This tool requires administrator access. Open it explicitly as administrator; this workflow will not elevate automatically.') from error
        raise
    progress('Tool opened. Follow its prompts, then close it and review the result.')
    while True:
        try:
            code = process.wait(timeout=0.5)
            break
        except subprocess.TimeoutExpired:
            if stopped(): return 'Workflow stopped. The already-open application remains running.'
    if code: raise RuntimeError('Application exited with code ' + str(code) + '. Review its results before continuing.')
    return 'Application exited. Verify its results; a helper process may still be open. Exit does not certify success.'


class Workflow:
    def __init__(self, root, workflow_id, mode, safe_path, publish):
        definitions = json.loads((root / 'assets/workflows.json').read_text('utf-8'))
        if workflow_id not in definitions or mode not in ('manual', 'automatic'): raise ValueError('Unknown workflow or mode')
        self.definition = definitions[workflow_id]
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
            elif command in ('next', 'skip', 'run') and self.waiting and body.get('step') == self.step and self.command is None:
                self.command = command
                self.waiting = False
            else: raise ValueError('This step is busy or has changed; refresh its status')
            self.condition.notify_all()

    def run_tool(self, step):
        if not step.get('tool'): return 'Manual checkpoint. Complete the instructions before confirming.'
        available = options(self.root, step['tool'], self.safe_path)
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
            if self.mode == 'automatic' and step.get('tool'):
                message = self.run_tool(step)
            while not self.stop:
                with self.condition:
                    self.waiting = True
                    self.state(message)
                    self.condition.wait_for(lambda: self.command is not None or self.stop)
                    command, self.command = self.command, None
                    self.waiting = False
                if self.stop: break
                if command == 'run':
                    self.state('Opening step tool…')
                    message = self.run_tool(step)
                else:
                    self.history.append({'step': index, 'text': step['text'], 'result': 'verified by technician' if command == 'next' else 'skipped — not verified'})
                    break
        return 'Workflow stopped; open applications were left running.' if self.stop else 'Workflow finished. Review the record for skipped steps; no automatic repair or clean-system certification was made.'
