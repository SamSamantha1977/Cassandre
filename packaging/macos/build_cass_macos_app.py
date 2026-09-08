#!/usr/bin/env python3
from __future__ import annotations
import hashlib, plistlib, zipfile
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
REL=ROOT/"Releases"
TECH=REL/"M3DIA-Worker-macOS.zip"
PUBLIC=REL/"Cass-MacOs.zip"
FRAGMENT_SOURCE=ROOT/"worker"/"sharedsecret.txt"
LOG=Path(__file__).with_suffix(".cmtrace.log")

def cm(msg,t=1):
    n=datetime.now().astimezone(); safe=str(msg).replace("]]>","] ]>")
    line=f'<![LOG[{safe}]LOG]!><time="{n:%H:%M:%S.%f}" date="{n:%m-%d-%Y}" component="BuildCassMacApp" context="" type="{t}" thread="0" file="build_cass_macos_app.py">'
    LOG.parent.mkdir(parents=True,exist_ok=True)
    with LOG.open("a",encoding="utf-8") as f:f.write(line+"\n")

APP_LAUNCHER=r'''#!/bin/sh
set -eu
CONTENTS=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
RES="$CONTENTS/Resources"
BUNDLE="$RES/M3DIA-Worker-macOS.zip"
SUMFILE="$RES/M3DIA-Worker-macOS.zip.sha256"
FRAGMENT_FILE="$RES/worker-shared-fragment.txt"
LOG="/tmp/Cassandre-Worker-Installer.cmtrace.log"
ORIGINAL_USER=${USER:-$(id -un)}

cmtrace(){ msg=$1; typ=${2:-1}; now=$(date '+%H:%M:%S.000'); day=$(date '+%m-%d-%Y'); printf '<![LOG[%s]LOG]!><time="%s" date="%s" component="CassandreMacInstaller" context="" type="%s" thread="%s" file="">\n' "$msg" "$now" "$day" "$typ" "$$" >> "$LOG" 2>/dev/null || true; }
dialog(){ /usr/bin/osascript -e "display dialog \"$1\" buttons {\"OK\"} default button \"OK\" with icon $2" >/dev/null 2>&1 || true; }
fail(){ cmtrace "$1" 3; dialog "Installation Cassandre impossible. Consultez : /tmp/Cassandre-Worker-Installer.cmtrace.log" stop; exit 1; }

cmtrace "Lanceur macOS graphique autonome demarre."
[ -f "$BUNDLE" ] || fail "Paquet WORKER integre introuvable."
[ -f "$SUMFILE" ] || fail "Empreinte SHA-256 integree introuvable."
[ -f "$FRAGMENT_FILE" ] || fail "Fragment d installation integre introuvable."
FRAGMENT=$(tr -d '\r\n' < "$FRAGMENT_FILE")
[ -n "$FRAGMENT" ] && [ "${#FRAGMENT}" -le 64 ] || fail "Fragment d installation invalide."
expected=$(awk 'NF {print toupper($1); exit}' "$SUMFILE")
actual=$(/usr/bin/shasum -a 256 "$BUNDLE" | awk '{print toupper($1)}')
[ -n "$expected" ] || fail "Empreinte attendue vide."
[ "$actual" = "$expected" ] || fail "Paquet WORKER endommage ou incomplet."
cmtrace "Paquet integre verifie SHA-256."

TMP="/tmp/cassandre-worker-install-$$"
/bin/rm -rf "$TMP"
/bin/mkdir -p "$TMP"
/bin/cp "$BUNDLE" "$TMP/M3DIA-Worker-macOS.zip"
/bin/cp "$FRAGMENT_FILE" "$TMP/worker-shared-fragment.txt"
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
if /usr/bin/osascript -e "do shell script \"/bin/sh '$ESCAPED'\" with administrator privileges" >/dev/null 2>&1; then
  rc=0
  cmtrace "Installation macOS terminee avec succes."
  dialog "Cassandre Worker est installe." note
else
  rc=$?
  cmtrace "Installation macOS annulee ou en echec; code=$rc." 3
  dialog "Installation Cassandre annulee ou en echec. Consultez : /tmp/Cassandre-Worker-Installer.cmtrace.log" stop
fi
/bin/rm -rf "$TMP"
exit "$rc"
'''

README="""CASSANDRE WORKER - macOS

1. Double-cliquez sur Cassandre-Installer.app.
2. Si macOS bloque l'application car le developpeur n'est pas identifie :
   - cliquez sur OK ;
   - ouvrez Preferences Systeme > Securite et confidentialite > General ;
   - cliquez sur Ouvrir quand meme ;
   - confirmez Ouvrir.
3. Validez l'autorisation administrateur demandee par macOS.
4. Une boite de dialogue confirme la fin de l'installation.

Aucune fenetre Terminal ne doit apparaitre. Les taches permanentes du WORKER sont
lancees en arriere-plan par launchd et n'ouvrent ni Terminal ni shell interactif.

Journal : /tmp/Cassandre-Worker-Installer.cmtrace.log
"""

INFO={
    "CFBundleDevelopmentRegion":"fr",
    "CFBundleDisplayName":"Cassandre Worker",
    "CFBundleExecutable":"CassandreInstaller",
    "CFBundleIdentifier":"fr.m3dia.cassandre.worker.installer",
    "CFBundleInfoDictionaryVersion":"6.0",
    "CFBundleName":"Cassandre Installer",
    "CFBundlePackageType":"APPL",
    "CFBundleShortVersionString":"1.0",
    "CFBundleVersion":"1",
    "LSUIElement":True,
    "NSHighResolutionCapable":True,
}

def zbytes(z,name,value,mode=0o100644):
    i=zipfile.ZipInfo(name)
    i.create_system=3
    i.external_attr=mode<<16
    i.compress_type=zipfile.ZIP_STORED
    z.writestr(i,value)

def ztext(z,name,value,mode=0o100644):
    zbytes(z,name,value.encode("utf-8"),mode)

def main():
    cm("Construction Cassandre-Installer.app commencee.")
    if not TECH.is_file():raise FileNotFoundError(TECH)
    if not FRAGMENT_SOURCE.is_file():raise FileNotFoundError(FRAGMENT_SOURCE)
    fragment=FRAGMENT_SOURCE.read_text(encoding="utf-8-sig").strip()
    if not fragment or len(fragment)>64:raise RuntimeError("Fragment d installation source invalide")
    tech=TECH.read_bytes()
    tech_sha=hashlib.sha256(tech).hexdigest().upper()
    tmp=PUBLIC.with_suffix(".zip.tmp")
    if tmp.exists():tmp.unlink()
    with zipfile.ZipFile(tmp,"w",zipfile.ZIP_STORED) as z:
        zbytes(z,"Cassandre-Installer.app/Contents/Info.plist",plistlib.dumps(INFO,fmt=plistlib.FMT_XML,sort_keys=False))
        ztext(z,"Cassandre-Installer.app/Contents/MacOS/CassandreInstaller",APP_LAUNCHER,0o100755)
        zbytes(z,"Cassandre-Installer.app/Contents/Resources/M3DIA-Worker-macOS.zip",tech)
        ztext(z,"Cassandre-Installer.app/Contents/Resources/M3DIA-Worker-macOS.zip.sha256",tech_sha+"  M3DIA-Worker-macOS.zip\n")
        ztext(z,"Cassandre-Installer.app/Contents/Resources/worker-shared-fragment.txt",fragment+"\n")
        ztext(z,"LISEZ-MOI.txt",README)
    tmp.replace(PUBLIC)
    digest=hashlib.sha256(PUBLIC.read_bytes()).hexdigest().upper()
    cm("Cass-MacOs.zip graphique construit SHA256="+digest+" size="+str(PUBLIC.stat().st_size))
    print("PUBLIC="+str(PUBLIC))
    print("PUBLIC_SHA256="+digest)

if __name__=="__main__":
    try:main()
    except Exception as e:
        cm("ECHEC: "+str(e),3)
        raise
