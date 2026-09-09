import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]/'MASTER-IT-TOOLKIT'
sys.path.insert(0,str(ROOT))
import launcher
import install_tools as installs

class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'assets/js').mkdir(parents=True);(self.root/'tools').mkdir()
        (self.root/'assets/toolkit-manifest.json').write_text(json.dumps([{'id':'app','os':['Windows'],'kind':'Installer','localFolder':'tools'}]))
        for name in ['Setup.exe','Portable.exe','package.msi']: (self.root/'tools'/name).write_bytes(b'fixture')
        (self.root/'assets/js/local-inventory.js').write_text('window.LOCAL_INVENTORY = '+json.dumps({'tools':{'app':{'files':[{'path':'tools/'+name} for name in ['Setup.exe','Portable.exe','package.msi']]}}})+';')
    def tearDown(self): self.temp.cleanup()
    def test_only_installers_from_inventory(self):
        tool,files,reason=installs.candidates(self.root,'app',launcher.safe_path)
        self.assertEqual({f['name'] for f in files},{'Setup.exe','package.msi'})
        with self.assertRaises(ValueError): installs.candidates(self.root,'unknown',launcher.safe_path)
    def test_modified_hash_stops_before_any_process(self):
        with patch.object(installs,'shell',return_value='powershell'),patch.object(installs.subprocess,'run') as run:
            with self.assertRaises(ValueError): installs.install(self.root,{'tool':'app','package':'tools/Setup.exe','sha256':'0'*64},launcher.safe_path)
            run.assert_not_called()
    def test_unlisted_path_rejected(self):
        with patch.object(installs,'shell',return_value='powershell'),patch.object(installs.subprocess,'run') as run:
            with self.assertRaises(ValueError): installs.install(self.root,{'tool':'app','package':'../outside.exe','sha256':'0'*64},launcher.safe_path)
            run.assert_not_called()
    @unittest.skipUnless(os.name=='nt','Windows PowerShell simulation')
    def test_checkpoint_and_signature_gate_with_mock_installer(self):
        parent=ROOT/'70_DOCUMENTATION/Service-Notes/Install-History';parent.mkdir(parents=True,exist_ok=True)
        for scenario in ['ok','checkpoint-fails','unsigned','unsigned-approved']:
            with self.subTest(scenario=scenario),tempfile.TemporaryDirectory(dir=parent) as temporary:
                folder=Path(temporary);package=folder/'Setup.exe';package.write_bytes(b'NOT AN EXECUTABLE')
                plan=folder/'test.plan.json';plan.write_text(json.dumps({'tool':'app','host':os.environ['COMPUTERNAME'],'package':str(package),'sha256':installs.digest(package),'acceptUnsigned':scenario=='unsigned-approved'}))
                marker=folder/'launched.txt'
                wrapper=folder/'simulate.ps1'
                wrapper.write_text('''Import-Module Microsoft.PowerShell.Utility -ErrorAction Stop
$script:checkpoint = $null
function Get-AuthenticodeSignature { param($LiteralPath) [pscustomobject]@{Status=SIGNATURE;SignerCertificate=@{Subject='Fixture publisher'}} }
function Get-ItemProperty { param($Path,$ErrorAction) [pscustomobject]@{DisplayName='Fixture App';DisplayVersion='1';Publisher='Fixture';PSChildName='fixture'} }
function Get-ComputerRestorePoint { [CmdletBinding()]param() if ($script:checkpoint) { $script:checkpoint } else { [pscustomobject]@{SequenceNumber=1;Description='Older'} } }
function Checkpoint-Computer { [CmdletBinding()]param($Description,$RestorePointType) CHECKPOINT; $script:checkpoint=[pscustomobject]@{SequenceNumber=2;Description=$Description;CreationTime='fixture'} }
function Start-Process { param($FilePath,$ArgumentList,[switch]$PassThru,[switch]$Wait) 'simulated' | Set-Content -LiteralPath MARKER; @{ExitCode=0} }
& SCRIPT -Plan PLAN -PlanSha256 PLANHASH
'''.replace('SIGNATURE',installs.ps_quote('NotSigned' if scenario.startswith('unsigned') else 'Valid')).replace('CHECKPOINT',"throw 'Fixture checkpoint failure'" if scenario=='checkpoint-fails' else "Write-Output 'Fixture checkpoint created'").replace('MARKER',installs.ps_quote(marker)).replace('SCRIPT',installs.ps_quote(ROOT/'60_SCRIPTS/Inventory/Install-TrackedApplication.ps1')).replace('PLANHASH',installs.ps_quote(installs.digest(plan))).replace('PLAN',installs.ps_quote(plan)),encoding='utf-8')
                result=subprocess.run([shutil.which('powershell.exe'),'-NoProfile','-ExecutionPolicy','Bypass','-File',str(wrapper)],capture_output=True,text=True,timeout=30)
                record=json.loads((folder/'test.result.json').read_text('utf-8-sig'))
                self.assertEqual(marker.exists(),scenario in ('ok','unsigned-approved'),result.stdout+result.stderr+json.dumps(record))
                self.assertEqual(record['status'],'review-required' if scenario in ('ok','unsigned-approved') else 'stopped')
                if scenario in ('ok','unsigned-approved'): self.assertEqual(record['restorePoint']['sequence'],2)

if __name__=='__main__':unittest.main()
