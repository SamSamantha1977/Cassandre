#!/usr/bin/env python3
from __future__ import annotations
import hashlib, re, zipfile
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
REL=ROOT/"Releases"
TECH=REL/"M3DIA-Worker-macOS.zip"
PUBLIC=REL/"Cass-MacOs.zip"
FRAGMENT_SOURCE=ROOT/"worker"/"sharedsecret.txt"
LOG=Path(__file__).with_suffix(".cmtrace.log")

def cm(msg,t=1):
    n=datetime.now().astimezone()
    s=msg.replace("]]>","] ]>")
    line=f'<![LOG[{s}]LOG]!><time="{n:%H:%M:%S.%f}" date="{n:%m-%d-%Y}" component="BuildCassMac" context="" type="{t}" thread="0" file="build_cass_macos.py">'
    LOG.parent.mkdir(parents=True,exist_ok=True)
    with LOG.open("a",encoding="utf-8") as f:f.write(line+"\n")

def text(data):
    for enc in ("utf-8-sig","utf-8","cp1252","latin-1"):
        try:return data.decode(enc)
        except UnicodeDecodeError:pass
    return data.decode("latin-1")

def patch_entry(name,data):
    if Path(name).suffix.lower() not in {".txt",".md",".py",".sh",".command",".ini",".json",".yml",".yaml",".cfg",".conf"}:
        return data
    s=text(data)
    normalized=name.replace("\\","/")
    if normalized.endswith("m3dia/platform_integration.py"):
        s=re.sub(r'\n\s*"StandardOutPath": "/dev/null",', "", s)
        s=re.sub(r'\n\s*"StandardErrorPath": "/dev/null",', "", s)
        marker='"ProcessType": "Background",'
        if s.count(marker)!=2:
            raise RuntimeError("Nombre inattendu de ProcessType Background dans platform_integration.py")
        s=s.replace(
            marker,
            marker+'\n        "StandardOutPath": "/dev/null",\n        "StandardErrorPath": "/dev/null",'
        )
        if s.count('"StandardOutPath": "/dev/null"') != 2 or s.count('"StandardErrorPath": "/dev/null"') != 2:
            raise RuntimeError("Redirection /dev/null macOS incomplete dans platform_integration.py")
        return s.encode("utf-8")
    if not name.endswith("install.command"):return s.encode("utf-8")
    pat=re.compile(r"FRAGMENT=\$\(\$PY - <<'PY'\r?\n.*?\r?\nPY\r?\n\)",re.S)
    block="""FRAGMENT="${M3DIA_INSTALL_SHARED_FRAGMENT:-}"
if [ -z "$FRAGMENT" ]; then
FRAGMENT=$($PY - <<'PY'
import base64
import json
import urllib.request
sources=[
 ("raw","https://raw.githubusercontent.com/SamSamantha1977/Cassandre/main/worker/sharedsecret.txt"),
 ("raw","https://raw.githubusercontent.com/SamSamantha1977/Cassandre/refs/heads/main/worker/sharedsecret.txt"),
 ("raw","https://github.com/SamSamantha1977/Cassandre/raw/refs/heads/main/worker/sharedsecret.txt"),
 ("api","https://api.github.com/repos/SamSamantha1977/Cassandre/contents/worker/sharedsecret.txt?ref=main"),
]
errors=[]
for kind,url in sources:
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"Cassandre-Worker-Installer","Accept":"application/vnd.github+json"})
        with urllib.request.urlopen(req,timeout=25) as r:payload=r.read()
        if kind=="api":payload=base64.b64decode(json.loads(payload.decode("utf-8"))["content"])

        value=payload.decode("utf-8-sig").strip()
        if value and len(value)<=64:
            print(value);raise SystemExit(0)
        errors.append(url+": fragment invalide")
    except SystemExit:raise
    except Exception as e:errors.append(url+": "+str(e))
raise SystemExit("Impossible de recuperer le fragment Cassandre: "+" | ".join(errors))
PY
)
fi"""
    marker='FRAGMENT="${M3DIA_INSTALL_SHARED_FRAGMENT:-}"'
    if marker not in s:
        s,n=pat.subn(block,s,count=1)
        if n!=1:raise RuntimeError("Bloc SharedSecret introuvable dans install.command")
    old_python='''PY=$(command -v python3 || true)
if [ -z "$PY" ]; then
  PKG="/tmp/m3dia-python-3.14.7-macos11.pkg"
  URL="https://www.python.org/ftp/python/3.14.7/python-3.14.7-macos11.pkg"
  cmtrace "Python 3 absent; telechargement du package officiel Python 3.14.7."
  /usr/bin/curl -fL --retry 5 --retry-delay 2 --connect-timeout 15 "$URL" -o "$PKG"
  /usr/sbin/installer -pkg "$PKG" -target /
  rm -f "$PKG"
  PY=$(command -v python3 || true)
  [ -n "$PY" ] || PY="/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
fi'''
    new_python='''PY=$(command -v python3 || true)
if [ -n "$PY" ]; then
  "$PY" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' >/dev/null 2>&1 || PY=""
fi
if [ -z "$PY" ]; then
  OSX=$(/usr/bin/sw_vers -productVersion 2>/dev/null || echo "10.15")
  MAJOR=$(printf '%s' "$OSX" | awk -F. '{print $1+0}')
  MINOR=$(printf '%s' "$OSX" | awk -F. '{print $2+0}')
  if [ "$MAJOR" -eq 10 ] && [ "$MINOR" -lt 15 ]; then
    PYVER="3.10.11"
    PKG="/tmp/m3dia-python-3.10.11-macos11.pkg"
    URL="https://www.python.org/ftp/python/3.10.11/python-3.10.11-macos11.pkg"
    FALLBACK="/Library/Frameworks/Python.framework/Versions/3.10/bin/python3"
  else
    PYVER="3.14.7"
    PKG="/tmp/m3dia-python-3.14.7-macos11.pkg"
    URL="https://www.python.org/ftp/python/3.14.7/python-3.14.7-macos11.pkg"
    FALLBACK="/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
  fi
  cmtrace "Python >=3.10 absent; telechargement du package officiel Python $PYVER pour macOS $OSX."
  /usr/bin/curl -fL --retry 5 --retry-delay 2 --connect-timeout 15 "$URL" -o "$PKG"
  /usr/sbin/installer -pkg "$PKG" -target /
  rm -f "$PKG"
  PY=$(command -v python3 || true)
  if [ -n "$PY" ]; then
    "$PY" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' >/dev/null 2>&1 || PY=""
  fi
  [ -n "$PY" ] || PY="$FALLBACK"
fi
"$PY" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' >/dev/null 2>&1 || { cmtrace "Python 3.10+ indisponible apres installation." 3; exit 23; }'''
    if old_python in s:
        s=s.replace(old_python,new_python)
    elif 'PYVER="3.10.11"' not in s:
        raise RuntimeError("Bloc Python macOS inattendu")
    return s.encode("utf-8")

def clone_info(i):
    o=zipfile.ZipInfo(i.filename,date_time=i.date_time)
    o.compress_type=zipfile.ZIP_STORED;o.comment=i.comment;o.extra=i.extra
    o.create_system=i.create_system;o.external_attr=i.external_attr;o.internal_attr=i.internal_attr
    return o

def patch_tech():
    if not TECH.is_file():raise FileNotFoundError(TECH)

    tmp=TECH.with_suffix(".zip.tmp")
    with zipfile.ZipFile(TECH,"r") as zin,zipfile.ZipFile(tmp,"w",zipfile.ZIP_STORED) as zout:
        if "install.command" not in zin.namelist():raise RuntimeError("install.command absent du package technique")
        for i in zin.infolist():zout.writestr(clone_info(i),patch_entry(i.filename,zin.read(i.filename)))
    tmp.replace(TECH)
    h=hashlib.sha256(TECH.read_bytes()).hexdigest().upper()
    cm("Package technique macOS corrige SHA256="+h)
    return h

LAUNCHER=r'''#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BUNDLE="$ROOT/.cassandre/M3DIA-Worker-macOS.zip"
SUMFILE="$ROOT/.cassandre/M3DIA-Worker-macOS.zip.sha256"
FRAGMENT_FILE="$ROOT/.cassandre/worker-shared-fragment.txt"
LOG="/tmp/Cassandre-Worker-Installer.cmtrace.log"
ORIGINAL_USER=${USER:-$(id -un)}
cmtrace(){ msg=$1; typ=${2:-1}; now=$(date '+%H:%M:%S.000'); day=$(date '+%m-%d-%Y'); printf '<![LOG[%s]LOG]!><time="%s" date="%s" component="CassandreMacInstaller" context="" type="%s" thread="%s" file="">\n' "$msg" "$now" "$day" "$typ" "$$" >> "$LOG" 2>/dev/null || true; }
fail(){ cmtrace "$1" 3; printf '\nERREUR : %s\nJournal : %s\n' "$1" "$LOG"; printf '\nAppuyez sur Entree pour fermer.\n'; read dummy; exit 1; }
clear
printf '\nCassandre Worker - Installation macOS\n\n'
cmtrace "Lanceur macOS autonome demarre."
[ -f "$BUNDLE" ] || fail "Le paquet integre du WORKER est introuvable."
[ -f "$SUMFILE" ] || fail "Le fichier de controle SHA-256 est introuvable."
[ -f "$FRAGMENT_FILE" ] || fail "Le fragment d installation integre est introuvable."
FRAGMENT=$(tr -d '\r\n' < "$FRAGMENT_FILE")
[ -n "$FRAGMENT" ] && [ "${#FRAGMENT}" -le 64 ] || fail "Le fragment d installation integre est invalide."
expected=$(awk 'NF {print toupper($1); exit}' "$SUMFILE")

actual=$(/usr/bin/shasum -a 256 "$BUNDLE" | awk '{print toupper($1)}')
[ -n "$expected" ] || fail "Empreinte SHA-256 attendue absente."
[ "$actual" = "$expected" ] || fail "Le paquet du WORKER est endommage ou incomplet."
cmtrace "Paquet integre verifie SHA-256."
TMP="/tmp/cassandre-worker-install-$$"
mkdir -p "$TMP"
cp "$BUNDLE" "$TMP/M3DIA-Worker-macOS.zip"
cp "$FRAGMENT_FILE" "$TMP/worker-shared-fragment.txt"
/bin/chmod 600 "$TMP/worker-shared-fragment.txt"
cat > "$TMP/install-root.sh" <<EOF
#!/bin/sh
set -eu
ZIP="$TMP/M3DIA-Worker-macOS.zip"
PAYLOAD="$TMP/payload"
FRAGMENT=\$(tr -d '\\r\\n' < "$TMP/worker-shared-fragment.txt")
[ -n "\$FRAGMENT" ] && [ "\${#FRAGMENT}" -le 64 ] || exit 22
mkdir -p "\$PAYLOAD"
/usr/bin/ditto -x -k "\$ZIP" "\$PAYLOAD"
launcher=\$(find "\$PAYLOAD" -type f -name 'install.command' -print -quit)
[ -n "\$launcher" ] || exit 21
/bin/chmod +x "\$launcher"
/usr/bin/xattr -dr com.apple.quarantine "\$PAYLOAD" 2>/dev/null || true
/usr/bin/env M3DIA_INSTALL_USER="$ORIGINAL_USER" M3DIA_INSTALL_SHARED_FRAGMENT="\$FRAGMENT" /bin/sh "\$launcher"
EOF
/bin/chmod 700 "$TMP/install-root.sh"
ESCAPED=$(printf '%s' "$TMP/install-root.sh" | /usr/bin/sed "s/'/'\\\\''/g")
printf 'Une autorisation administrateur macOS va etre demandee une seule fois.\n\n'
if /usr/bin/osascript -e "do shell script \"/bin/sh '$ESCAPED'\" with administrator privileges"; then
  rc=0;cmtrace "Installation macOS terminee avec succes.";printf '\nCassandre Worker est installe.\n'
else
  rc=$?;cmtrace "Installation macOS annulee ou en echec; code=$rc." 3;printf '\nInstallation annulee ou en echec.\nJournal : %s\n' "$LOG"
fi
/bin/rm -rf "$TMP"
printf '\nAppuyez sur Entree pour fermer.\n';read dummy
exit "$rc"
'''

README="""CASSANDRE WORKER - macOS

1. Double-cliquez sur Cassandre-Installer.command.
2. Si macOS indique que le developpeur n'est pas identifie :
   - cliquez sur OK ;
   - ouvrez Preferences Systeme > Securite et confidentialite > General ;
   - cliquez sur Ouvrir quand meme ;
   - confirmez Ouvrir.
3. Validez l'autorisation administrateur demandee par macOS.
4. Attendez le message : Cassandre Worker est installe.

Le ZIP est autonome : le paquet du WORKER et les donnees d amorcage necessaires
sont inclus et controles avant installation. Aucun autre fichier GitHub n'est a choisir.

Journal : /tmp/Cassandre-Worker-Installer.cmtrace.log
"""

def ztext(z,name,value,mode=0o100644):
    i=zipfile.ZipInfo(name);i.create_system=3;i.external_attr=mode<<16;i.compress_type=zipfile.ZIP_STORED
    z.writestr(i,value.encode("utf-8"))

def zbytes(z,name,value,mode=0o100644):
    i=zipfile.ZipInfo(name);i.create_system=3;i.external_attr=mode<<16;i.compress_type=zipfile.ZIP_STORED
    z.writestr(i,value)

def build_public(tech_sha):
    if not FRAGMENT_SOURCE.is_file():raise FileNotFoundError(FRAGMENT_SOURCE)
    fragment=FRAGMENT_SOURCE.read_text(encoding="utf-8-sig").strip()
    if not fragment or len(fragment)>64:raise RuntimeError("Fragment d installation source invalide")
    tmp=PUBLIC.with_suffix(".zip.tmp")

    if tmp.exists():tmp.unlink()
    with zipfile.ZipFile(tmp,"w",zipfile.ZIP_STORED) as z:
        ztext(z,"Cassandre-Installer.command",LAUNCHER,0o100755)
        ztext(z,"LISEZ-MOI.txt",README)
        zbytes(z,".cassandre/M3DIA-Worker-macOS.zip",TECH.read_bytes())
        ztext(z,".cassandre/M3DIA-Worker-macOS.zip.sha256",tech_sha+"  M3DIA-Worker-macOS.zip\n")
        ztext(z,".cassandre/worker-shared-fragment.txt",fragment+"\n")
    tmp.replace(PUBLIC)
    h=hashlib.sha256(PUBLIC.read_bytes()).hexdigest().upper()
    cm("Cass-MacOs.zip construit SHA256="+h+" size="+str(PUBLIC.stat().st_size))
    return h

def main():
    cm("Construction macOS commencee.")
    th=patch_tech()
    ph=build_public(th)
    print("TECH_SHA256="+th)
    print("PUBLIC="+str(PUBLIC))
    print("PUBLIC_SHA256="+ph)
    cm("Construction macOS terminee avec succes.")

if __name__=="__main__":
    try:main()
    except Exception as e:
        cm("ECHEC: "+str(e),3)
        raise
