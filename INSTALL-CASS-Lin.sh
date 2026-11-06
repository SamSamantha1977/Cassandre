#!/bin/sh
set -eu

RAW_URL="https://raw.githubusercontent.com/SamSamantha1977/Cassandre/main/install-linux.sh"
TMP_SCRIPT="${TMPDIR:-/tmp}/cassandre-install-linux-$$.sh"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
LOG_DIR="$STATE_HOME/cassandre-worker"
LOG="$LOG_DIR/installer.cmtrace.log"
trap 'rm -f "$TMP_SCRIPT"' EXIT HUP INT TERM

mkdir -p "$LOG_DIR"
cmtrace() {
  msg=$1; typ=${2:-1}; now=$(date '+%H:%M:%S.000'); day=$(date '+%m-%d-%Y')
  printf '<![LOG[%s]LOG]!><time="%s" date="%s" component="PublicLauncher" context="" type="%s" thread="%s" file="">\n' "$msg" "$now" "$day" "$typ" "$$" >> "$LOG" 2>/dev/null || true
}

cmtrace "Lanceur Linux utilisateur demarre."
if command -v curl >/dev/null 2>&1; then
  curl -fsSL "$RAW_URL" -o "$TMP_SCRIPT" || { cmtrace "Telechargement du lanceur Linux impossible (curl)." 3; exit 2; }
elif command -v wget >/dev/null 2>&1; then
  wget -qO "$TMP_SCRIPT" "$RAW_URL" || { cmtrace "Telechargement du lanceur Linux impossible (wget)." 3; exit 2; }
else
  cmtrace "curl et wget absents." 3
  echo "Impossible de telecharger l'installateur : curl/wget absent." >&2
  exit 2
fi
chmod 700 "$TMP_SCRIPT" || { cmtrace "Impossible de preparer le lanceur Linux." 3; exit 2; }
rc=0
/bin/sh "$TMP_SCRIPT" || rc=$?
if [ "$rc" -ne 0 ]; then
 cmtrace "Installation Linux echouee: code=$rc" 3
 printf "Erreur installation Cassandre. Journal : %s\n" "$LOG" >&2
fi
exit "$rc"
