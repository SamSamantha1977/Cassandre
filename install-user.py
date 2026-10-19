from __future__ import annotations

import argparse
import configparser
import contextlib
import hashlib
import os
import plistlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

REPO = "SamSamantha1977/Cassandre"
BASE_RELEASE = f"https://github.com/{REPO}/releases/latest/download"
FRAGMENT_URLS = (
    f"https://raw.githubusercontent.com/{REPO}/main/worker/sharedsecret.txt",
    f"https://raw.githubusercontent.com/{REPO}/refs/heads/main/worker/sharedsecret.txt",
)
VERSION = "5.1.0-user"


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def cmtrace(log_file: str | Path, message: str, component: str = "UserInstaller", typ: int = 1) -> None:
    p = Path(log_file)
    ensure_dir(p.parent)
    now = datetime.now()
    safe = str(message).replace("]]>", "] ]>")
    line = (
        f'<![LOG[{safe}]LOG]!><time="{now:%H:%M:%S}.{now.microsecond // 1000:03d}" '
        f'date="{now:%m-%d-%Y}" component="{component}" context="" type="{typ}" '
        f'thread="{os.getpid()}" file="">\n'
    )
    with p.open("a", encoding="utf-8") as stream:
        stream.write(line)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def download(url: str, destination: Path, timeout: int = 60) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "CassandreWorkerInstaller/5.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response, destination.open("wb") as stream:
        shutil.copyfileobj(response, stream)


def read_url_text(url: str, timeout: int = 30) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "CassandreWorkerInstaller/5.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8-sig")


def safe_rel(name: str) -> Path:
    normalized = name.replace("\\", "/").lstrip("/")
    pure = PurePosixPath(normalized)
    if not normalized or any(part in ("", ".", "..") for part in pure.parts):
        raise ValueError(f"Archive path refused: {name!r}")
    return Path(*pure.parts)


def extract_zip(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive, "r") as zf:
        for info in zf.infolist():
            raw = info.filename.replace("\\", "/")
            if not raw or raw.endswith("/"):
                if raw:
                    ensure_dir(destination / safe_rel(raw.rstrip("/")))
                continue
            target = destination / safe_rel(raw)
            ensure_dir(target.parent)
            with zf.open(info, "r") as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)


def extract_tar(archive: Path, destination: Path) -> None:
    with tarfile.open(archive, "r:gz") as tf:
        for member in tf.getmembers():
            if not member.isfile() and not member.isdir():
                continue
            target = destination / safe_rel(member.name.rstrip("/") if member.isdir() else member.name)
            if member.isdir():
                ensure_dir(target)
                continue
            ensure_dir(target.parent)
            source = tf.extractfile(member)
            if source is None:
                continue
            with source, target.open("wb") as dst:
                shutil.copyfileobj(source, dst)


def asset_for_platform() -> str:
    if os.name == "nt":
        return "M3DIA-Worker-Windows.zip"
    if sys.platform == "darwin":
        return "M3DIA-Worker-macOS.zip"
    return "M3DIA-Worker-Linux.tar.gz"


def default_install_root() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "CassandreWorker"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "CassandreWorker"
    return Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) / "cassandre-worker"


def fetch_fragment(explicit: str = "") -> str:
    value = str(explicit or "").strip()
    if value:
        if len(value) > 64:
            raise ValueError("SharedSecret fragment too long")
        return value
    errors: list[str] = []
    for url in FRAGMENT_URLS:
        try:
            value = read_url_text(url, timeout=20).strip()
            if value and len(value) <= 64:
                return value
            errors.append(f"{url}: invalid fragment")
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError("Unable to retrieve Cassandre SharedSecret fragment: " + " | ".join(errors))


def expected_hash(asset: str, hashes_text: str) -> str:
    for line in hashes_text.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2:
            continue
        digest, name = parts
        name = name.lstrip("*").strip()
        if name == asset and len(digest) == 64:
            return digest.upper()
    raise RuntimeError(f"SHA256SUMS.txt has no entry for {asset}")


SCHEDULER_SOURCE = r'''from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from .platforms import hidden_process_kwargs

_TASK_COMMANDS = {
    "M3DIACompute Worker Monitor": "monitor",
    "M3DIACompute Worker WakePoll": "wake-poll",
    "M3DIACompute Worker Retry": "retry",
    "M3DIACompute Worker JobRunner": "job",
    "M3DIACompute Worker JobGuard": "guard",
    "M3DIACompute Worker AdminExecutor": "admin-executor",
}


def _python_background() -> str:
    if os.name != "nt":
        return sys.executable
    current = Path(sys.executable)
    pythonw = current if current.name.lower() == "pythonw.exe" else current.with_name("pythonw.exe")
    return str(pythonw if pythonw.is_file() else current)


def _worker_wrapper() -> str:
    cfg = os.getenv("M3DIA_WORKER_CONFIG", "")
    if cfg:
        p = Path(cfg)
        if p.parent.name.lower() == "state":
            return str(p.parent.parent / "worker_main.py")
    argv0 = Path(sys.argv[0]).resolve()
    if argv0.name == "worker_main.py":
        return str(argv0)
    return str(argv0.parent / "worker_main.py")


def _popen(argv: list[str]) -> None:
    kwargs = dict(
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    if os.name == "nt":
        kwargs.update(hidden_process_kwargs())
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(argv, **kwargs)


def run_task(name: str) -> None:
    command = _TASK_COMMANDS.get(str(name))
    if not command:
        return
    _popen([_python_background(), _worker_wrapper(), command])


def defer_task(name: str, seconds: float) -> None:
    command = _TASK_COMMANDS.get(str(name))
    if not command:
        return
    delay = max(0.0, float(seconds))
    target = [_python_background(), _worker_wrapper(), command]
    code = (
        "import subprocess,time;"
        f"time.sleep({delay!r});"
        f"subprocess.Popen({target!r},stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,"
        "stderr=subprocess.DEVNULL,close_fds=True"
        + (",creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0x08000000)" if os.name == "nt" else ",start_new_session=True")
        + ")"
    )
    _popen([_python_background(), "-c", code])
'''

INSTALLER_SHIM_SOURCE = r'''from __future__ import annotations

from datetime import datetime


def windows_schedule_once(name, argv, when, run_as_system=False, wake=False, log_path=None):
    from .scheduler import defer_task
    now = datetime.now(when.tzinfo) if getattr(when, "tzinfo", None) else datetime.now()
    defer_task(name, max(0.0, (when - now).total_seconds()))
'''

WORKER_MAIN_SOURCE = r'''from m3dia.worker import main

if __name__ == "__main__":
    main()
'''

USER_AGENT_SOURCE = r'''from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "State" / "worker.json"
LOG = ROOT / "Logs" / "user-agent.cmtrace.log"
os.environ["M3DIA_WORKER_CONFIG"] = str(CONFIG)


def log(message: str, typ: int = 1) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    safe = str(message).replace("]]>", "] ]>")
    line = (
        f'<![LOG[{safe}]LOG]!><time="{now:%H:%M:%S}.{now.microsecond // 1000:03d}" '
        f'date="{now:%m-%d-%Y}" component="UserAgent" context="" type="{typ}" '
        f'thread="{os.getpid()}" file="">\\n'
    )
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write(line)


def acquire_single_instance():
    if os.name == "nt":
        import ctypes
        handle = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\CassandreWorkerUserAgent")
        if not handle:
            raise OSError("CreateMutexW failed")
        if ctypes.windll.kernel32.GetLastError() == 183:
            return None
        return handle
    import fcntl
    lock_path = ROOT / "State" / "user-agent.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+b")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def child_kwargs() -> dict:
    kwargs = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        kwargs["creationflags"] = int(getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000))
        if hasattr(subprocess, "STARTUPINFO"):
            si = subprocess.STARTUPINFO()
            si.dwFlags |= int(getattr(subprocess, "STARTF_USESHOWWINDOW", 0x00000001))
            si.wShowWindow = int(getattr(subprocess, "SW_HIDE", 0))
            kwargs["startupinfo"] = si
    else:
        kwargs["start_new_session"] = True
    return kwargs


def main() -> int:
    lock = acquire_single_instance()
    if lock is None:
        return 0
    wrapper = ROOT / "worker_main.py"
    log("Cassandre Worker user agent started.")
    while True:
        try:
            result = subprocess.run(
                [sys.executable, str(wrapper), "monitor", "--no-reschedule"],
                timeout=90,
                env={**os.environ, "M3DIA_WORKER_CONFIG": str(CONFIG)},
                **child_kwargs(),
            )
            if result.returncode != 0:
                log(f"Monitor returned {result.returncode}.", 2)
        except subprocess.TimeoutExpired:
            log("Monitor timeout; next cycle will retry.", 2)
        except Exception as exc:
            log(f"Monitor failed: {exc}", 3)
        time.sleep(1.0)


if __name__ == "__main__":
    raise SystemExit(main())
'''


def find_payload_root(extracted: Path) -> Path:
    candidates = [p.parent for p in extracted.rglob("config.ini") if (p.parent / "m3dia").is_dir()]
    if not candidates:
        raise RuntimeError("Package payload containing config.ini and m3dia was not found")
    candidates.sort(key=lambda p: len(p.parts))
    return candidates[0]


def copy_runtime(payload: Path, root: Path, log: Path) -> None:
    for name in ("Logs", "Inbox", "Outbox", "State", "Config", "AdminQueue", "AdminDone", "AdminFailed", "Updates"):
        ensure_dir(root / name)
    shutil.copytree(payload / "m3dia", root / "m3dia", dirs_exist_ok=True)
    shutil.copy2(payload / "config.ini", root / "Config" / "config.ini")
    for optional in ("LICENSE", "README.md", "requirements.txt"):
        source = payload / optional
        if source.is_file():
            shutil.copy2(source, root / optional)
    (root / "m3dia" / "scheduler.py").write_text(SCHEDULER_SOURCE, encoding="utf-8", newline="\n")
    (root / "m3dia" / "installer.py").write_text(INSTALLER_SHIM_SOURCE, encoding="utf-8", newline="\n")
    (root / "worker_main.py").write_text(WORKER_MAIN_SOURCE, encoding="utf-8", newline="\n")
    (root / "user_agent.py").write_text(USER_AGENT_SOURCE, encoding="utf-8", newline="\n")
    cmtrace(log, f"Runtime copied to {root}.")


def initialize_state(root: Path, fragment: str, log: Path) -> Path:
    config_path = root / "State" / "worker.json"
    os.environ["M3DIA_WORKER_CONFIG"] = str(config_path)
    sys.path.insert(0, str(root))
    from m3dia.config import RegistryJsonConfig, bootstrap_worker_state, default_worker, worker_store
    from m3dia.platforms import is_portable

    defaults = default_worker(str(root))
    existing: dict = {}
    if config_path.is_file():
        try:
            import json
            existing = json.loads(config_path.read_text(encoding="utf-8-sig"))
        except Exception:
            existing = {}
    elif os.name == "nt":
        with contextlib.suppress(Exception):
            existing = RegistryJsonConfig("HKCU", r"Software\M3DIA\Compute\Worker", defaults).load()
    state = bootstrap_worker_state(existing, defaults)
    state.update(
        {
            "version": "5.1.0",
            "install_root": str(root),
            "is_portable": is_portable(),
        }
    )
    if not state.get("registered") or not state.get("shared_secret"):
        state.update(
            {
                "install_shared_secret": "",
                "install_shared_fragment": fragment,
                "install_secret_suffix_file": str(root / "Config" / "config.ini"),
            }
        )
    store = worker_store(config_path, defaults)
    store.save(state)
    cmtrace(log, f"Worker state ready: {config_path}.")
    return config_path


def _windows_background_python() -> Path:
    current = Path(sys.executable)
    candidate = current if current.name.lower() == "pythonw.exe" else current.with_name("pythonw.exe")
    return candidate if candidate.is_file() else current


def install_windows_startup(root: Path, config_path: Path, log: Path, start_now: bool) -> None:
    import winreg

    agent = root / "user_agent.py"
    python_bg = _windows_background_python()
    if python_bg.name.lower() == "pythonw.exe":
        command = f'"{python_bg}" "{agent}"'
    else:
        vbs = root / "start-hidden.vbs"
        py = str(python_bg).replace('"', '""')
        ag = str(agent).replace('"', '""')
        vbs.write_text(
            'Set shell = CreateObject("WScript.Shell")\r\n'
            f'shell.Run """{py}"" ""{ag}""", 0, False\r\n',
            encoding="utf-8",
        )
        command = f'wscript.exe //B //NoLogo "{vbs}"'
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "CassandreWorker", 0, winreg.REG_SZ, command)
    cmtrace(log, "Windows startup registered in HKCU Run; no SID and no scheduled task used.")
    if start_now:
        kwargs = {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "close_fds": True,
            "creationflags": int(getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)),
        }
        if hasattr(subprocess, "STARTUPINFO"):
            si = subprocess.STARTUPINFO()
            si.dwFlags |= int(getattr(subprocess, "STARTF_USESHOWWINDOW", 0x00000001))
            si.wShowWindow = int(getattr(subprocess, "SW_HIDE", 0))
            kwargs["startupinfo"] = si
        subprocess.Popen([str(python_bg), str(agent)], env={**os.environ, "M3DIA_WORKER_CONFIG": str(config_path)}, **kwargs)


def install_macos_startup(root: Path, config_path: Path, log: Path, start_now: bool) -> None:
    launch_dir = ensure_dir(Path.home() / "Library" / "LaunchAgents")
    plist_path = launch_dir / "fr.cassandre.worker.plist"
    payload = {
        "Label": "fr.cassandre.worker",
        "ProgramArguments": [sys.executable, str(root / "user_agent.py")],
        "EnvironmentVariables": {"M3DIA_WORKER_CONFIG": str(config_path)},
        "RunAtLoad": True,
        "KeepAlive": True,
        "ProcessType": "Background",
        "LowPriorityIO": True,
        "StandardOutPath": "/dev/null",
        "StandardErrorPath": "/dev/null",
    }
    with plist_path.open("wb") as stream:
        plistlib.dump(payload, stream, fmt=plistlib.FMT_XML, sort_keys=False)
    os.chmod(plist_path, 0o644)
    with contextlib.suppress(Exception):
        subprocess.run(["xattr", "-dr", "com.apple.quarantine", str(root)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    uid = str(os.getuid())
    subprocess.run(["launchctl", "bootout", f"gui/{uid}", str(plist_path)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if start_now:
        result = subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(plist_path)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode != 0:
            cmtrace(log, f"launchctl bootstrap returned {result.returncode}; LaunchAgent remains installed for next login.", typ=2)
            subprocess.Popen([sys.executable, str(root / "user_agent.py")], start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True, env={**os.environ, "M3DIA_WORKER_CONFIG": str(config_path)})
    cmtrace(log, f"macOS LaunchAgent installed: {plist_path}.")


def _systemd_quote(value: str | Path) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def install_linux_startup(root: Path, config_path: Path, log: Path, start_now: bool) -> None:
    unit_dir = ensure_dir(Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "systemd" / "user")
    unit_path = unit_dir / "cassandre-worker.service"
    unit_path.write_text(
        "[Unit]\n"
        "Description=Cassandre Worker user agent\n"
        "After=network-online.target\n"
        "Wants=network-online.target\n\n"
        "[Service]\n"
        "Type=simple\n"
        f"Environment=M3DIA_WORKER_CONFIG={config_path}\n"
        f"ExecStart={_systemd_quote(sys.executable)} {_systemd_quote(root / 'user_agent.py')}\n"
        "Restart=always\n"
        "RestartSec=5\n"
        "Nice=10\n\n"
        "[Install]\n"
        "WantedBy=default.target\n",
        encoding="utf-8",
        newline="\n",
    )
    systemd_ok = False
    if shutil.which("systemctl"):
        reload_result = subprocess.run(["systemctl", "--user", "daemon-reload"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        enable_result = subprocess.run(["systemctl", "--user", "enable", "cassandre-worker.service"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if reload_result.returncode == 0 and enable_result.returncode == 0:
            systemd_ok = True
            if start_now:
                start_result = subprocess.run(["systemctl", "--user", "restart", "cassandre-worker.service"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                systemd_ok = start_result.returncode == 0
    if systemd_ok:
        cmtrace(log, f"Linux user systemd service installed: {unit_path}.")
        return
    autostart = ensure_dir(Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "autostart") / "cassandre-worker.desktop"
    autostart.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Cassandre Worker\n"
        f"Exec={_systemd_quote(sys.executable)} {_systemd_quote(root / 'user_agent.py')}\n"
        "Terminal=false\n"
        "X-GNOME-Autostart-enabled=true\n",
        encoding="utf-8",
        newline="\n",
    )
    cmtrace(log, f"systemd --user unavailable; XDG autostart installed: {autostart}.", typ=2)
    if start_now:
        subprocess.Popen([sys.executable, str(root / "user_agent.py")], start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True, env={**os.environ, "M3DIA_WORKER_CONFIG": str(config_path)})


def initial_contact(root: Path, config_path: Path, log: Path) -> None:
    env = {**os.environ, "M3DIA_WORKER_CONFIG": str(config_path)}
    kwargs = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "env": env,
        "timeout": 45,
        "check": False,
    }
    if os.name == "nt":
        kwargs["creationflags"] = int(getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000))
    result = subprocess.run([sys.executable, str(root / "worker_main.py"), "network"], **kwargs)
    if result.returncode == 0:
        cmtrace(log, "Initial Controller contact succeeded.")
    else:
        cmtrace(log, f"Initial Controller contact returned {result.returncode}; background retry will continue.", typ=2)


def install(args) -> Path:
    root = Path(args.install_root).expanduser().resolve() if args.install_root else default_install_root()
    log = root / "Logs" / "install.cmtrace.log"
    ensure_dir(log.parent)
    cmtrace(log, f"Cassandre Worker user installation started; version={VERSION}.")
    fragment = fetch_fragment(args.fragment)
    cmtrace(log, f"SharedSecret fragment retrieved; length={len(fragment)}; value not logged.")

    with tempfile.TemporaryDirectory(prefix="cassandre-worker-install-") as temporary:
        temp = Path(temporary)
        asset = asset_for_platform()
        archive = Path(args.package).expanduser().resolve() if args.package else temp / asset
        if not args.package:
            cmtrace(log, f"Downloading {asset}.")
            download(f"{BASE_RELEASE}/{asset}", archive)
            hashes_text = read_url_text(f"{BASE_RELEASE}/SHA256SUMS.txt", timeout=30)
            expected = expected_hash(asset, hashes_text)
            actual = sha256_file(archive)
            if actual != expected:
                raise RuntimeError(f"SHA-256 mismatch for {asset}")
            cmtrace(log, f"SHA-256 verified for {asset}.")
        elif args.hash:
            actual = sha256_file(archive)
            if actual != args.hash.strip().upper():
                raise RuntimeError(f"Local package SHA-256 mismatch for {archive.name}")
            cmtrace(log, f"Local package SHA-256 verified for {archive.name}.")

        extracted = ensure_dir(temp / "payload")
        if archive.name.lower().endswith(".zip"):
            extract_zip(archive, extracted)
        else:
            extract_tar(archive, extracted)
        payload = find_payload_root(extracted)
        copy_runtime(payload, root, log)
        config_path = initialize_state(root, fragment, log)

    if not args.no_contact:
        with contextlib.suppress(Exception):
            initial_contact(root, config_path, log)
    if not args.no_start:
        if os.name == "nt":
            install_windows_startup(root, config_path, log, True)
        elif sys.platform == "darwin":
            install_macos_startup(root, config_path, log, True)
        else:
            install_linux_startup(root, config_path, log, True)
    cmtrace(log, "Cassandre Worker user installation completed successfully.")
    return root


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Cassandre Worker user-scope installer")
    parser.add_argument("--package", help="Use a local Worker archive instead of downloading the latest release")
    parser.add_argument("--hash", default="", help="Optional SHA-256 for --package")
    parser.add_argument("--fragment", default="", help=argparse.SUPPRESS)
    parser.add_argument("--install-root", default="")
    parser.add_argument("--no-start", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-contact", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = default_install_root() if not args.install_root else Path(args.install_root).expanduser()
    log = root / "Logs" / "install.cmtrace.log"
    try:
        result = install(args)
        print(f"Cassandre Worker installed for the current user: {result}")
        return 0
    except Exception as exc:
        with contextlib.suppress(Exception):
            cmtrace(log, f"INSTALLATION FAILED: {exc}", typ=3)
        print(f"Cassandre Worker installation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
