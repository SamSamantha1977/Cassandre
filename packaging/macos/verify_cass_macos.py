#!/usr/bin/env python3
from __future__ import annotations
import hashlib, io, os, plistlib, re, subprocess, tempfile, urllib.request, zipfile
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PUBLIC=ROOT/"Releases"/"Cass-MacOs.zip"
LOG=Path(__file__).with_suffix(".cmtrace.log")
EXPECTED={"Cassandre-Installer.app/Contents/Info.plist","Cassandre-Installer.app/Contents/MacOS/CassandreInstaller","Cassandre-Installer.app/Contents/Resources/M3DIA-Worker-macOS.zip","Cassandre-Installer.app/Contents/Resources/M3DIA-Worker-macOS.zip.sha256","Cassandre-Installer.app/Contents/Resources/worker-shared-fragment.txt","LISEZ-MOI.txt"}
SECRET_URLS=[
 "https://raw.githubusercontent.com/SamSamantha1977/Cassandre/main/worker/sharedsecret.txt",
 "https://raw.githubusercontent.com/SamSamantha1977/Cassandre/refs/heads/main/worker/sharedsecret.txt",
 "https://github.com/SamSamantha1977/Cassandre/raw/refs/heads/main/worker/sharedsecret.txt",
 "https://api.github.com/repos/SamSamantha1977/Cassandre/contents/worker/sharedsecret.txt?ref=main",
]
PYTHON_URLS=["https://www.python.org/ftp/python/3.14.7/python-3.14.7-macos11.pkg","https://www.python.org/ftp/python/3.10.11/python-3.10.11-macos11.pkg"]

def cm(msg,t=1):
    n=datetime.now().astimezone();s=msg.replace("]]>","] ]>")
    line=f'<![LOG[{s}]LOG]!><time="{n:%H:%M:%S.%f}" date="{n:%m-%d-%Y}" component="VerifyCassMac" context="" type="{t}" thread="0" file="verify_cass_macos.py">'
    with LOG.open("a",encoding="utf-8") as f:f.write(line+"\n")

def need(ok,msg):
    if not ok:raise AssertionError(msg)

def shell_syntax(name,data):
    sh=Path("/bin/sh")
    if not sh.exists():
        cm("Verification /bin/sh ignoree sur cette plateforme.")
        return
    with tempfile.TemporaryDirectory() as td:
        f=Path(td)/Path(name).name
        f.write_bytes(data);os.chmod(f,0o755)
        p=subprocess.run([str(sh),"-n",str(f)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        need(p.returncode==0,name+" syntaxe shell invalide: "+p.stderr.strip())

def network():
    good=0
    for url in SECRET_URLS:
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"Cassandre-Worker-Installer-Verify","Accept":"application/vnd.github+json"})
            with urllib.request.urlopen(req,timeout=20) as r:data=r.read()
            need(getattr(r,"status",200)==200,url+" HTTP != 200")
            need(len(data)>0,url+" reponse vide")
            good+=1;cm("Endpoint SharedSecret OK: "+url)
        except Exception as e:cm("Endpoint SharedSecret KO: "+url+" :: "+str(e),2)
    need(good>=2,"Moins de deux endpoints SharedSecret accessibles.")
    for python_url in PYTHON_URLS:
        req=urllib.request.Request(python_url,method="HEAD",headers={"User-Agent":"Cassandre-Worker-Installer-Verify"})
        with urllib.request.urlopen(req,timeout=20) as r:
            need(getattr(r,"status",200)==200,"Python.org HTTP != 200: "+python_url)
            need(int(r.headers.get("Content-Length","0"))>10000000,"Package Python macOS inattendu: "+python_url)
        cm("Package Python macOS accessible: "+python_url)

def main():
    cm("Verification Cass-MacOs commencee.")
    need(PUBLIC.is_file(),"Cass-MacOs.zip absent")

    with zipfile.ZipFile(PUBLIC,"r") as z:
        need(z.testzip() is None,"Archive publique corrompue")
        need(set(z.namelist())==EXPECTED,"Contenu archive publique inattendu")
        exe="Cassandre-Installer.app/Contents/MacOS/CassandreInstaller"
        mode=(z.getinfo(exe).external_attr>>16)&0o777
        need(mode&0o111!=0,"Executable .app non executable")
        launcher=z.read(exe)
        low=launcher.lower()
        need(b"damcuvelier" not in low,"Ancienne URL dans lanceur public")
        need(b"raw.githubusercontent.com" not in low,"Le lanceur public ne doit plus telecharger le bootstrap")
        need(b"m3dia_install_shared_fragment" in low,"Le fragment integre n est pas transmis au package technique")
        need(b"terminal.app" not in low and b"open -a terminal" not in low,"Le lanceur public ne doit jamais ouvrir Terminal")
        need(b"read dummy" not in low,"Le lanceur graphique ne doit pas attendre un terminal interactif")
        info=plistlib.loads(z.read("Cassandre-Installer.app/Contents/Info.plist"))
        need(info.get("CFBundlePackageType")=="APPL","Bundle macOS invalide")
        need(info.get("CFBundleExecutable")=="CassandreInstaller","Executable bundle inattendu")
        need(info.get("LSUIElement") is True,"Installer doit etre agent graphique sans Dock/Terminal")
        fragment=z.read("Cassandre-Installer.app/Contents/Resources/worker-shared-fragment.txt").decode("utf-8-sig").strip()
        need(bool(fragment) and len(fragment)<=64,"Fragment integre invalide")
        shell_syntax("CassandreInstaller",launcher)

        inner=z.read("Cassandre-Installer.app/Contents/Resources/M3DIA-Worker-macOS.zip")
        expected=z.read("Cassandre-Installer.app/Contents/Resources/M3DIA-Worker-macOS.zip.sha256").decode().split()[0].upper()
        actual=hashlib.sha256(inner).hexdigest().upper()
        need(actual==expected,"SHA-256 package technique integre invalide")

    with zipfile.ZipFile(io.BytesIO(inner),"r") as z:
        need(z.testzip() is None,"Archive technique macOS corrompue")
        need("install.command" in z.namelist(),"install.command absent du package technique")
        install=z.read("install.command")
        s=install.decode("utf-8")
        for logical in ("m3dia/platform_integration.py","m3dia/scheduler.py"):
            need(logical in z.namelist(),"Runtime macOS absent: "+logical)
            runtime=z.read(logical).decode("utf-8")
            low_runtime=runtime.lower()
            need("terminal.app" not in low_runtime and "open -a terminal" not in low_runtime,"Runtime persistant interdit d ouvrir Terminal: "+logical)
        platform_source=z.read("m3dia/platform_integration.py")
        ns={}
        exec(compile(platform_source,"<platform_integration>","exec"),ns)
        generated=ns["macos_worker_plists"](Path("/Library/Application Support/M3DIACompute"),"/usr/bin/python3","testuser")
        need(bool(generated),"Aucun LaunchDaemon macOS genere")
        for name,content in generated.items():
            obj=plistlib.loads(content.encode("utf-8"))
            argv=list(obj.get("ProgramArguments") or [])
            need(argv and "python" in Path(argv[0]).name.lower(),"LaunchDaemon doit appeler Python directement: "+name)
            joined=" ".join(argv).lower()
            for forbidden in ("terminal.app","open -a terminal","/bin/zsh","/bin/bash","/bin/sh","osascript"):
                need(forbidden not in joined,"Commande interactive interdite dans LaunchDaemon "+name+": "+forbidden)
            need(obj.get("ProcessType")=="Background","LaunchDaemon non Background: "+name)
        need("damcuvelier/M3DIACompute" not in s,"Ancienne URL GitHub dans install.command")
        need('FRAGMENT="${M3DIA_INSTALL_SHARED_FRAGMENT:-}"' in s,"Le package technique ne prefere pas le fragment integre")
        for url in SECRET_URLS:need(url in s,"Fallback absent: "+url)
        for python_url in PYTHON_URLS:need(python_url in s,"URL Python macOS absente: "+python_url)
        need('PYVER="3.10.11"' in s and 'PYVER="3.14.7"' in s,"Selection Python selon version macOS absente")
        m=re.search(r"FRAGMENT=\$\(\$PY - <<'PY'\r?\n(.*?)\r?\nPY\r?\n\)",s,re.S)
        need(m is not None,"Bloc Python SharedSecret introuvable")
        compile(m.group(1),"<sharedsecret-bootstrap>","exec")
        shell_syntax("install.command",install)

    network()
    cm("Verification Cass-MacOs terminee avec succes.")
    print("VERIFY_CASS_MACOS=OK")
    print("PUBLIC_SHA256="+hashlib.sha256(PUBLIC.read_bytes()).hexdigest().upper())

if __name__=="__main__":
    try:main()
    except Exception as e:
        cm("ECHEC: "+str(e),3)
        print("VERIFY_CASS_MACOS=FAILED")
        raise
