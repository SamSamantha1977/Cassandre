#!/bin/sh
set -eu

RAW_URL="https://raw.githubusercontent.com/SamSamantha1977/Cassandre/main/install-linux.sh"
TMP_SCRIPT="/tmp/m3dia-install-linux-$$.sh"
LOG="/tmp/M3DIA-Worker-Installer.cmtrace.log"

cmtrace() {
  msg=$1; typ=${2:-1}; now=$(date '+%H:%M:%S.000'); day=$(date '+%m-%d-%Y')
  printf '<![LOG[%s]LOG]!><time="%s" date="%s" component="PublicLauncher" context="" type="%s" thread="%s" file="">\n' "$msg" "$now" "$day" "$typ" "$$" >> "$LOG" 2>/dev/null || true
}

cmtrace "Lanceur Linux demarre."
if command -v curl >/dev/null 2>&1; then curl -fsSL "$RAW_URL" -o "$TMP_SCRIPT"
elif command -v wget >/dev/null 2>&1; then wget -qO "$TMP_SCRIPT" "$RAW_URL"
else cmtrace "curl et wget absents." 3; echo "Impossible de telecharger l'installateur : curl/wget absent." >&2; exit 2
fi
chmod 700 "$TMP_SCRIPT"

if [ "$(id -u)" -eq 0 ]; then /bin/sh "$TMP_SCRIPT"; rc=$?
elif command -v pkexec >/dev/null 2>&1; then pkexec env M3DIA_INSTALL_USER="${USER:-}" /bin/sh "$TMP_SCRIPT"; rc=$?
elif command -v sudo >/dev/null 2>&1; then sudo M3DIA_INSTALL_USER="${USER:-}" /bin/sh "$TMP_SCRIPT"; rc=$?
else cmtrace "Aucun mecanisme d'elevation disponible." 3; echo "Droits administrateur requis." >&2; rc=10
fi
rm -f "$TMP_SCRIPT"
exit "$rc"
