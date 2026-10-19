#!/bin/sh
set -eu

RAW_URL="https://raw.githubusercontent.com/SamSamantha1977/Cassandre/main/install-linux.sh"
TMP_SCRIPT="${TMPDIR:-/tmp}/cassandre-install-linux-$$.sh"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
LOG_DIR="$STATE_HOME/cassandre-worker"
LOG="$LOG_DIR/installer.cmtrace.log"

mkdir -p "$LOG_DIR"
cmtrace() {
  msg=$1; typ=${2:-1}; now=$(date '+%H:%M:%S.000'); day=$(date '+%m-%d-%Y')
  printf '<![LOG[%s]LOG]!><time="%s" date="%s" component="PublicLauncher" context="" type="%s" thread="%s" file="">\n' "$msg" "$now" "$day" "$typ" "$$" >> "$LOG" 2>/dev/null || true
}

cmtrace "Lanceur Linux utilisateur demarre."
if command -v curl >/dev/null 2>&1; then
  curl -fsSL "$RAW_URL" -o "$TMP_SCRIPT"
elif command -v wget >/dev/null 2>&1; then
  wget -qO "$TMP_SCRIPT" "$RAW_URL"
else
  cmtrace "curl et wget absents." 3
  echo "Impossible de telecharger l'installateur : curl/wget absent." >&2
  exit 2
fi
chmod 700 "$TMP_SCRIPT"
/bin/sh "$TMP_SCRIPT"
rc=$?
rm -f "$TMP_SCRIPT"
exit "$rc"
