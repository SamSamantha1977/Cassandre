"""Tests unitaires hors-ligne : pas d'installation et pas de modification du poste."""
from __future__ import annotations
import importlib.util
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('user_bootstrap', ROOT / 'bootstrap_user.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class BootstrapUserTests(unittest.TestCase):
    def test_source_no_elevation(self):
        source = (ROOT / 'bootstrap_user.py').read_text(encoding='utf8')
        self.assertNotIn('Start-Process -Verb RunAs', source)
        self.assertNotIn('subprocess.run([\"schtasks.exe\"', source)
        self.assertNotIn('subprocess.run(["pkexec"', source)
        self.assertNotIn('subprocess.run(["sudo"', source)
        self.assertIn("'M3DIA_USER_MODE'", source)
        self.assertIn('SHA-256', source)

    def test_four_installer_entrypoints(self):
        for name in ('INSTALL-WORKER-Utilisateur-Windows.ps1',
                     'INSTALL-WORKER-Utilisateur-Linux-Debian.sh',
                     'INSTALL-WORKER-Utilisateur-Linux-Fedora.sh',
                     'INSTALL-WORKER-Utilisateur-Linux-Universel.sh'):
            self.assertTrue((ROOT / name).is_file(), name)

    def test_scheduler_and_worker_patch(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = pathlib.Path(temp) / 'm3dia'
            folder.mkdir()
            (folder / 'scheduler.py').write_text('''import os,subprocess,sys
from pathlib import Path
from .platforms import hidden_process_kwargs
_TASK_COMMANDS={'M3DIACompute Worker JobRunner':'job'}
def _pythonw():return sys.executable
def _worker_wrapper():return 'worker_main.py'
def run_task(name: str) -> None:
    if os.name == "nt":
        subprocess.run(
            ["schtasks.exe", "/Run", "/TN", str(name)], check=False)
        return
    pass

def defer_task(name: str, seconds: float) -> None:
    pass
''', encoding='utf8')
            (folder / 'worker.py').write_text('''class Worker:
    def schedule_retry(self,when):
        import os
        if os.name == 'nt':
            pass
    def monitor(self,reschedule=True):
        return None
''', encoding='utf8')
            module.user_scheduler_patch(folder.parent)
            src = (folder / 'scheduler.py').read_text(encoding='utf8')
            self.assertNotIn('schtasks.exe', src)
            self.assertIn('subprocess.Popen', src)
            self.assertIn('def defer_task', src)
            self.assertIn('def monitor', (folder / 'worker.py').read_text(encoding='utf8'))
            compile(src, 'scheduler.py', 'exec')
            compile((folder / 'worker.py').read_text(encoding='utf8'), 'worker.py', 'exec')

if __name__ == '__main__':
    unittest.main(verbosity=2)
