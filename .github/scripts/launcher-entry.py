"""Frozen bootstrap: updated source is loaded on restart, without replacing the EXE."""
import launcher  # Included so PyInstaller collects its standard-library dependencies.
import runpy
import argparse
import datetime
import fnmatch
import tempfile
import sys
from pathlib import Path

root = Path(sys.executable).resolve().parent
if (root / 'MASTER-IT-TOOLKIT' / 'launcher.py').is_file(): root = root / 'MASTER-IT-TOOLKIT'
sys.path.insert(0, str(root))
if '--self-test' in sys.argv:
    print('Master IT Toolkit standalone runtime ready.')
elif '--inventory' in sys.argv:
    script = root / '60_SCRIPTS/Inventory/update_toolkit_inventory.py'
    sys.argv = [str(script)]
    runpy.run_path(str(script), run_name='__main__')
else:
    runpy.run_path(str(root / 'launcher.py'), run_name='__main__')
