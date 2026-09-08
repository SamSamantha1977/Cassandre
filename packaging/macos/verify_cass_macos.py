#!/usr/bin/env python3
from __future__ import annotations
import hashlib, io, os, re, subprocess, tempfile, urllib.request, zipfile
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PUBLIC=ROOT/"Releases"/"Cass-MacOs.zip"
LOG=Path(__file__).with_suffix(".cmtrace.log")
EXPECTED={"Cassandre-Installer.command","LISEZ-MOI.txt",".cassandre/M3DIA-Worker-macOS.zip",".cassandre/M3DIA-Worker-macOS.zip.sha256",".cassandre/worker-shared-fragment.txt"}
SECRET_URLS=[
 "https://raw.githubusercontent.com/SamSamantha1977/Cassandre/main/worker/sharedsecret.txt",
 "https://raw.githubusercontent.com/SamSamantha1977/Cassandre/refs/heads/main/worker/sharedsecret.txt",
 "https://github.com/SamSamantha1977/Cassandre/raw/refs/heads/main/worker/sharedsecret.txt",
 "https://api.github.com/repos/SamSamantha1977/Cassandre/contents/worker/sharedsecret.txt?ref=main",
]
PYTHON_URL="https://www.python.org/ftp/python/3.14.7/python-3.14.7-macos11.pkg"

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
    req=urllib.request.Request(PYTHON_URL,method="HEAD",headers={"User-Agent":"Cassandre-Worker-Installer-Verify"})
    with urllib.request.urlopen(req,timeout=20) as r:
        need(getattr(r,"status",200)==200,"Python.org HTTP != 200")
        need(int(r.headers.get("Content-Length","0"))>10000000,"Package Python macOS inattendu")
    cm("Package Python macOS accessible.")

def main():
    cm("Verification Cass-MacOs commencee.")
    need(PUBLIC.is_file(),"Cass-MacOs.zip absent")

    with zipfile.ZipFile(PUBLIC,"r") as z:
        need(z.testzip() is None,"Archive publique corrompue")
        need(set(z.namelist())==EXPECTED,"Contenu archive publique inattendu")
        mode=(z.getinfo("Cassandre-Installer.command").external_attr>>16)&0o777
        need(mode&0o111!=0,"Cassandre-Installer.command non executable")
        launcher=z.read("Cassandre-Installer.command")
        need(b"damcuvelier" not in launcher.lower(),"Ancienne URL dans lanceur public")
        need(b"raw.githubusercontent.com" not in launcher.lower(),"Le lanceur public ne doit plus telecharger le bootstrap")
        need(b"M3DIA_INSTALL_SHARED_FRAGMENT" in launcher,"Le fragment integre n est pas transmis au package technique")
        fragment=z.read(".cassandre/worker-shared-fragment.txt").decode("utf-8-sig").strip()
        need(bool(fragment) and len(fragment)<=64,"Fragment integre invalide")
        shell_syntax("Cassandre-Installer.command",launcher)

        inner=z.read(".cassandre/M3DIA-Worker-macOS.zip")
        expected=z.read(".cassandre/M3DIA-Worker-macOS.zip.sha256").decode().split()[0].upper()
        actual=hashlib.sha256(inner).hexdigest().upper()
        need(actual==expected,"SHA-256 package technique integre invalide")

    with zipfile.ZipFile(io.BytesIO(inner),"r") as z:
        need(z.testzip() is None,"Archive technique macOS corrompue")
        need("install.command" in z.namelist(),"install.command absent du package technique")
        install=z.read("install.command")
        s=install.decode("utf-8")
        need("damcuvelier/M3DIACompute" not in s,"Ancienne URL GitHub dans install.command")
        need('FRAGMENT="${M3DIA_INSTALL_SHARED_FRAGMENT:-}"' in s,"Le package technique ne prefere pas le fragment integre")
        for url in SECRET_URLS:need(url in s,"Fallback absent: "+url)
        need(PYTHON_URL in s,"URL Python macOS absente")
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
