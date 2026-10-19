#!/usr/bin/env python3
"""Cassandre WORKER - installation strictement dans le profil de l'utilisateur.
Sans sudo, pkexec, UAC, services systeme ni modification de /etc, /opt ou HKLM.
"""
from __future__ import annotations
import argparse
import hashlib
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import venv
import zipfile
import tarfile
from datetime import datetime

REPO = 'SamSamantha1977/Cassandre'
BASE = f'https://github.com/{REPO}/releases/download/worker-bootstrap'
FRAGMENT = f'https://raw.githubusercontent.com/{REPO}/main/worker/sharedsecret.txt'
MIN_PY = (3, 11)
ROOT = ((pathlib.Path(os.environ.get('LOCALAPPDATA') or (pathlib.Path.home() / 'AppData' / 'Local')) / 'Cassandre' / 'Worker')
        if os.name == 'nt' else pathlib.Path(os.environ.get('XDG_DATA_HOME') or (pathlib.Path.home() / '.local' / 'share')) / 'cassandre-worker')
LOG = ROOT / 'Logs' / 'install.cmtrace.log'

def cmtrace(message: str, severity: int = 1, component: str = 'WorkerUserInstaller') -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    safe = str(message).replace(']]>', '] ]>')
    line = (f'<![LOG[{safe}]LOG]!><time="{now:%H:%M:%S}.000" '
            f'date="{now:%m-%d-%Y}" component="{component}" context="" '
            f'type="{severity}" thread="{os.getpid()}" file="bootstrap_user.py">\n')
    with LOG.open('a', encoding='utf-8') as output:
        output.write(line)

def call(args, *, env=None, check=True):
    kw = {'check': check, 'env': env}
    if os.name == 'nt':
        kw['creationflags'] = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
    return subprocess.run([str(arg) for arg in args], **kw)

def fetch(url: str, out: pathlib.Path) -> None:
    req = urllib.request.Request(url, headers={'User-Agent': 'Cassandre-Worker-User-Installer/1.0'})
    with urllib.request.urlopen(req, timeout=60) as response, out.open('wb') as target:
        shutil.copyfileobj(response, target)

def fetch_payload(target: pathlib.Path) -> pathlib.Path:
    asset = 'M3DIA-Worker-Windows.zip' if os.name == 'nt' else 'M3DIA-Worker-Linux.tar.gz'
    archive = target / asset
    checksums = target / 'SHA256SUMS.txt'
    fetch(f'{BASE}/{asset}', archive)
    fetch(f'{BASE}/SHA256SUMS.txt', checksums)
    digest = None
    for raw in checksums.read_text(encoding='utf-8-sig').splitlines():
        match = re.match(r'^\s*([a-fA-F0-9]{64})\s+\*?(.+?)\s*$', raw)
        if match and match.group(2) == asset:
            digest = match.group(1).lower()
            break
    if not digest:
        raise RuntimeError(f'Empreinte SHA-256 absente pour {asset}')
    with archive.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if actual != digest:
        raise RuntimeError('Archive refusee : empreinte SHA-256 incorrecte')
    cmtrace(f'Archive {asset} verifiee en SHA-256.')
    dest = target / 'payload'
    dest.mkdir()
    if os.name == 'nt':
        with zipfile.ZipFile(archive) as z:
            for item in z.infolist():
                resolved = (dest / item.filename.replace('\\', '/')).resolve()
                if dest.resolve() not in resolved.parents and resolved != dest.resolve():
                    raise RuntimeError('Archive ZIP : chemin dangereux')
            z.extractall(dest)
    else:
        with tarfile.open(archive, 'r:gz') as tar:
            for member in tar.getmembers():
                candidate = (dest / member.name).resolve()
                if dest.resolve() not in candidate.parents and candidate != dest.resolve():
                    raise RuntimeError('Archive TAR : chemin dangereux')
                if member.issym() or member.islnk() or member.isdev():
                    raise RuntimeError('Archive TAR : entree speciale refusee')
            tar.extractall(dest)
    if not (dest / 'm3dia' / 'worker.py').is_file() or not (dest / 'config.ini').is_file():
        raise RuntimeError('Package WORKER incomplet')
    return dest

def user_scheduler_patch(path: pathlib.Path) -> None:
    """En mode utilisateur, commandes du worker dans une session non privilegiee.
    L'execution d'une tache arrive par lancement direct, pas par schtasks SYSTEM.
    """
    scheduler = path / 'm3dia' / 'scheduler.py'
    content = scheduler.read_text(encoding='utf-8-sig')
    marker = '    if os.name == "nt":\n        subprocess.run(\n            ["schtasks.exe", "/Run", "/TN", str(name)],'
    if marker not in content:
        raise RuntimeError('scheduler.py incompatible : patch impossible sans risque')
    beginning = content.index('def run_task(name: str) -> None:')
    ending = content.index('\ndef defer_task(name: str, seconds: float) -> None:', beginning)
    replacement = '''def run_task(name: str) -> None:
    # WORKER UTILISATEUR: aucune tache SYSTEM, aucune elevation.
    if str(name) == "M3DIACompute Worker AdminExecutor":
        return
    command = _TASK_COMMANDS.get(str(name))
    if not command:
        return
    kwargs = hidden_process_kwargs() if os.name == "nt" else {"start_new_session": True}
    subprocess.Popen([_pythonw(), _worker_wrapper(), command],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, close_fds=True, **kwargs)

'''
    content = content[:beginning] + replacement + content[ending:]
    # defer_task() Windows attend schtasks; en mode utilisateur on relance run_task.
    beginning = content.index('def defer_task(name: str, seconds: float) -> None:')
    content = content[:beginning] + '''def defer_task(name: str, seconds: float) -> None:
    delay = max(0.0, float(seconds))
    command = _TASK_COMMANDS.get(str(name))
    if not command:
        return
    python = _pythonw()
    wrapper = _worker_wrapper()
    snippet = ("import subprocess,time;time.sleep(" + repr(delay) + ");" +
               "subprocess.Popen(" + repr([python, wrapper, command]) +
               ",stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL," +
               "stderr=subprocess.DEVNULL,close_fds=True," +
               ("creationflags=0x08000000)" if os.name == "nt" else "start_new_session=True)"))
    kwargs = hidden_process_kwargs() if os.name == "nt" else {"start_new_session": True}
    subprocess.Popen([python, "-c", snippet], stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        close_fds=True, **kwargs)
'''
    scheduler.write_text(content, encoding='utf-8')
    worker = path / 'm3dia' / 'worker.py'
    wsource = worker.read_text(encoding='utf-8-sig')
    anchor = '    def schedule_retry(self,when):'
    end = '    def monitor(self,reschedule=True):'
    if anchor not in wsource or end not in wsource:
        raise RuntimeError('worker.py incompatible : mise a jour utilisateur impossible')
    start = wsource.index(anchor)
    stop = wsource.index(end, start)
    wsource = wsource[:start] + '''    def schedule_retry(self,when):
        # Le moniteur utilisateur maintient la boucle; ne pas recreer
        # une tache planifiee Windows privilegiee ou machine.
        return
''' + wsource[stop:]
    worker.write_text(wsource, encoding='utf-8')

def install_payload(payload: pathlib.Path) -> None:
    if sys.version_info < MIN_PY:
        raise RuntimeError('Python 3.11 ou superieur est necessaire dans la session utilisateur')
    if os.name != 'nt' and hasattr(os, 'geteuid') and os.geteuid() == 0:
        raise RuntimeError('Ne pas lancer cet installateur avec sudo/root')
    ROOT.mkdir(parents=True, exist_ok=True)
    envdir = ROOT / 'venv'
    if not (envdir / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')).exists():
        cmtrace('Preparation de l environnement Python prive.')
        venv.create(envdir, with_pip=True)
    py = envdir / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    req = payload / 'requirements.txt'
    if req.exists() and req.stat().st_size:
        call([py, '-m', 'pip', 'install', '--disable-pip-version-check', '-r', req])
    app = ROOT / 'app'
    app.mkdir(exist_ok=True)
    shutil.copytree(payload / 'm3dia', app / 'm3dia', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    user_scheduler_patch(app)
    for folder in ('Config', 'State', 'Logs', 'Inbox', 'Outbox', 'AdminQueue',
                   'AdminDone', 'AdminFailed', 'Updates'):
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    shutil.copy2(payload / 'config.ini', ROOT / 'Config' / 'config.ini')
    wrapper = '''from pathlib import Path
import os, sys
ROOT = Path(__file__).resolve().parent
os.environ['M3DIA_WORKER_CONFIG'] = str(ROOT / 'State' / 'worker.json')
os.environ['M3DIA_USER_MODE'] = '1'
sys.path.insert(0, str(ROOT / 'app'))
from m3dia.worker import main
if __name__ == '__main__':
    main()
'''
    (ROOT / 'worker_main.py').write_text(wrapper, encoding='utf-8')
    daemon = '''from pathlib import Path
import os, sys, time, subprocess, signal
root = Path(__file__).resolve().parent
os.environ['M3DIA_WORKER_CONFIG'] = str(root / 'State' / 'worker.json')
os.environ['M3DIA_USER_MODE'] = '1'
py = root / 'venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
stop = False
def shutdown(*_):
    global stop
    stop = True
signal.signal(signal.SIGTERM, shutdown)
if hasattr(signal, 'SIGINT'): signal.signal(signal.SIGINT, shutdown)
while not stop:
    try:
        kw = {'creationflags': getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)} if os.name == 'nt' else {}
        subprocess.run([str(py), str(root / 'worker_main.py'), 'monitor', '--no-reschedule'],
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=50, **kw)
    except Exception:
        pass
    for _ in range(10):
        if stop: break
        time.sleep(1)
'''
    (ROOT / 'worker_daemon.py').write_text(daemon, encoding='utf-8')
    with tempfile.TemporaryDirectory(prefix='cassandre-secret-') as temp:
        secret = pathlib.Path(temp) / 'fragment'
        fetch(FRAGMENT, secret)
        fragment = secret.read_text(encoding='utf-8-sig').strip()
    if not fragment or len(fragment) > 64:
        raise RuntimeError('Fragment de configuration non conforme')
    sys.path.insert(0, str(app))
    os.environ['M3DIA_WORKER_CONFIG'] = str(ROOT / 'State' / 'worker.json')
    from m3dia.config import default_worker, bootstrap_worker_state, worker_store
    defaults = default_worker(str(ROOT))
    store = worker_store(ROOT / 'State' / 'worker.json', defaults)
    previous = store.load()
    state = bootstrap_worker_state(previous, defaults)
    state.update({'version': '5.1.0', 'install_root': str(ROOT),
                  'install_shared_secret': '', 'install_shared_fragment': fragment,
                  'install_secret_suffix_file': str(ROOT / 'Config' / 'config.ini')})
    store.save(state)
    cmtrace('Configuration d amorcage WORKER utilisateur sauvegardee.')
    # Appel initial au controleur, sans echec bloquant si reseau inaccessible.
    result = call([py, ROOT / 'worker_main.py', 'network'], check=False)
    cmtrace('Premier contact controleur, code=' + str(result.returncode),
            1 if result.returncode == 0 else 2)
    install_autostart(py)
    cmtrace('WORKER UTILISATEUR installe sans privilege administrateur.')

def install_autostart(py: pathlib.Path) -> None:
    if os.name == 'nt':
        import winreg
        pyw = py.with_name('pythonw.exe')
        if not pyw.exists():
            raise RuntimeError('pythonw.exe absent du venv : demarrage silencieux impossible')
        command = subprocess.list2cmdline([str(pyw), str(ROOT / 'worker_daemon.py')])
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,
                                r'Software\Microsoft\Windows\CurrentVersion\Run',
                                0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, 'CassandreWorkerUser', 0, winreg.REG_SZ, command)
        cmtrace('Demarrage automatique configure dans HKCU\\Run.')
        # Lance des a present sans creer de fenetre de commande.
        kwargs = {'creationflags': getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)}
        call_py = [str(pyw), str(ROOT / 'worker_daemon.py')]
        subprocess.Popen(call_py, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, close_fds=True, **kwargs)
    else:
        units = pathlib.Path(os.environ.get('XDG_CONFIG_HOME') or pathlib.Path.home() / '.config') / 'systemd' / 'user'
        units.mkdir(parents=True, exist_ok=True)
        service = units / 'cassandre-worker-user.service'
        service.write_text('[Unit]\nDescription=Cassandre WORKER utilisateur\nAfter=network-online.target\n'
                           '[Service]\nType=simple\nExecStart=' + str(py) + ' ' + str(ROOT / 'worker_daemon.py') +
                           '\nRestart=on-failure\nRestartSec=10\n[Install]\nWantedBy=default.target\n',
                           encoding='utf-8')
        if shutil.which('systemctl'):
            reload = call(['systemctl', '--user', 'daemon-reload'], check=False)
            if reload.returncode == 0:
                activated = call(['systemctl', '--user', 'enable', '--now', 'cassandre-worker-user.service'], check=False)
                if activated.returncode == 0:
                    cmtrace('Service systemd --user active.')
                    return
        # Alternative XDG: demarrage a la prochaine ouverture de session graphique.
        autostart = pathlib.Path(os.environ.get('XDG_CONFIG_HOME') or pathlib.Path.home() / '.config') / 'autostart'
        autostart.mkdir(parents=True, exist_ok=True)
        desktop = autostart / 'cassandre-worker-user.desktop'
        desktop.write_text('[Desktop Entry]\nType=Application\nName=Cassandre WORKER utilisateur\n'
                           'Exec=' + str(py) + ' ' + str(ROOT / 'worker_daemon.py') +
                           '\nTerminal=false\nX-GNOME-Autostart-enabled=true\n', encoding='utf-8')
        cmtrace('Demarrage automatique XDG active (a la prochaine connexion).', 2)

def status() -> None:
    print('Installation :', ROOT)
    print('Configuration :', ROOT / 'State' / 'worker.json')
    print('Journal CMTrace :', LOG)
    print('Installe :', (ROOT / 'worker_main.py').is_file())

def uninstall() -> None:
    cmtrace('Desinstallation du demarrage WORKER utilisateur.')
    if os.name == 'nt':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r'Software\Microsoft\Windows\CurrentVersion\Run',
                                0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, 'CassandreWorkerUser')
        except OSError:
            pass
    else:
        if shutil.which('systemctl'):
            call(['systemctl', '--user', 'disable', '--now', 'cassandre-worker-user.service'], check=False)
        config = pathlib.Path(os.environ.get('XDG_CONFIG_HOME') or pathlib.Path.home() / '.config')
        for file in (config / 'systemd/user/cassandre-worker-user.service',
                     config / 'autostart/cassandre-worker-user.desktop'):
            file.unlink(missing_ok=True)
        if shutil.which('systemctl'):
            call(['systemctl', '--user', 'daemon-reload'], check=False)
    print('Demarrage automatique desactive. Donnees conservees :', ROOT)
    cmtrace('Demarrage automatique desactive. Donnees conservees.')

def main() -> int:
    p = argparse.ArgumentParser(description='Cassandre WORKER - version utilisateur sans administrateur')
    p.add_argument('--mode', choices=('install', 'status', 'uninstall'), default='install')
    p.add_argument('--family', choices=('windows', 'debian', 'fedora', 'universal'), default='universal')
    p.add_argument('--payload-root', type=pathlib.Path)
    args = p.parse_args()
    if args.family == 'windows' and os.name != 'nt':
        raise RuntimeError('Cette variante est reservee a Windows')
    if args.family != 'windows' and os.name == 'nt':
        raise RuntimeError('Cette variante est reservee a Linux')
    if args.mode == 'status': status(); return 0
    if args.mode == 'uninstall': uninstall(); return 0
    if args.payload_root:
        install_payload(args.payload_root)
    else:
        with tempfile.TemporaryDirectory(prefix='cassandre-worker-user-') as temp:
            install_payload(fetch_payload(pathlib.Path(temp)))
    status()
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        try: cmtrace('ERREUR installation : ' + str(error), 3)
        except Exception: pass
        print('Erreur Cassandre WORKER utilisateur :', error, file=sys.stderr)
        sys.exit(1)
