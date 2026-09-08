#!/usr/bin/env python3
from __future__ import annotations
import io, plistlib, zipfile
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REL=ROOT/"Releases"
LOG=Path(__file__).with_suffix(".cmtrace.log")

def cm(msg,t=1):
    n=datetime.now().astimezone();safe=str(msg).replace("]]>","] ]>")
    line=f'<![LOG[{safe}]LOG]!><time="{n:%H:%M:%S.%f}" date="{n:%m-%d-%Y}" component="VerifyZeroWindow" context="" type="{t}" thread="0" file="verify_zero_window_policy.py">'
    with LOG.open("a",encoding="utf-8") as f:f.write(line+"\n")

def need(ok,msg):
    if not ok:raise AssertionError(msg)

def read(z,name):
    need(name in z.namelist(),"Fichier absent: "+name)
    return z.read(name).decode("utf-8","replace")

def verify_windows():
    p=REL/"M3DIA-Worker-Windows.zip"
    need(p.is_file(),"Package Windows absent")
    with zipfile.ZipFile(p) as z:
        need(z.testzip() is None,"Package Windows corrompu")
        platforms=read(z,"m3dia/platforms.py").lower()
        scheduler=read(z,"m3dia/scheduler.py").lower()
        installer=read(z,"m3dia/installer.py").lower()
        need("create_no_window" in platforms,"Windows: CREATE_NO_WINDOW absent")
        need("startupinfo" in platforms and "sw_hide" in platforms,"Windows: STARTUPINFO/SW_HIDE absents")
        need("pythonw.exe" in scheduler,"Windows: scheduler n impose pas pythonw.exe")
        need("pythonw.exe" in installer,"Windows: installer n impose pas pythonw.exe")
        need("<hidden>true</hidden>" in installer,"Windows: Task Scheduler Hidden=true absent")
        for bad in ("windowsterminal.exe","wt.exe"):
            need(bad not in scheduler and bad not in installer,"Windows: Terminal interdit: "+bad)
    cm("Windows ZERO-WINDOW valide.")

def verify_macos():
    p=REL/"Cass-MacOs.zip"
    need(p.is_file(),"Package macOS public absent")
    with zipfile.ZipFile(p) as pub:
        need(pub.testzip() is None,"Package macOS public corrompu")
        exe="Cassandre-Installer.app/Contents/MacOS/CassandreInstaller"
        need(exe in pub.namelist(),"Installer .app absent")
        mode=(pub.getinfo(exe).external_attr>>16)&0o777
        need(mode&0o111!=0,"Executable .app non executable")
        launcher=pub.read(exe).decode("utf-8","replace").lower()
        need("terminal.app" not in launcher and "open -a terminal" not in launcher,"Installer macOS ouvre Terminal")
        info=plistlib.loads(pub.read("Cassandre-Installer.app/Contents/Info.plist"))
        need(info.get("LSUIElement") is True,"Installer macOS doit etre LSUIElement")
        inner=pub.read("Cassandre-Installer.app/Contents/Resources/M3DIA-Worker-macOS.zip")
    with zipfile.ZipFile(io.BytesIO(inner)) as z:
        need(z.testzip() is None,"Package macOS technique corrompu")
        src=read(z,"m3dia/platform_integration.py")
        ns={}
        exec(compile(src,"<platform_integration>","exec"),ns)
        plists=ns["macos_worker_plists"](Path("/Library/Application Support/M3DIACompute"),"/usr/bin/python3","testuser")
        need(bool(plists),"macOS: aucun LaunchDaemon genere")
        for name,xml in plists.items():
            obj=plistlib.loads(xml.encode("utf-8"))
            argv=list(obj.get("ProgramArguments") or [])
            need(argv and "python" in Path(argv[0]).name.lower(),"macOS: LaunchDaemon n appelle pas Python directement: "+name)
            joined=" ".join(argv).lower()
            for bad in ("terminal.app","open -a terminal","osascript","/bin/sh","/bin/bash","/bin/zsh"):
                need(bad not in joined,"macOS: commande interactive interdite dans "+name+": "+bad)
            need(obj.get("ProcessType")=="Background","macOS: ProcessType != Background: "+name)
    cm("macOS ZERO-WINDOW valide.")

def main():
    cm("Verification ZERO-WINDOW commencee.")
    verify_windows()
    verify_macos()
    cm("Verification ZERO-WINDOW terminee avec succes.")
    print("VERIFY_ZERO_WINDOW=OK")

if __name__=="__main__":
    try:main()
    except Exception as e:
        cm("ECHEC: "+str(e),3)
        print("VERIFY_ZERO_WINDOW=FAILED")
        raise
