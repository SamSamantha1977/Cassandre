#!/bin/sh
set -u

RAW_URL="https://raw.githubusercontent.com/SamSamantha1977/Cassandre/main/install-macos.sh"
TMP_SCRIPT="${TMPDIR:-/tmp}/cassandre-install-macos-$$.sh"
LOG_DIR="$HOME/Library/Logs/CassandreWorker"
LOG="$LOG_DIR/installer.cmtrace.log"

mkdir -p "$LOG_DIR" 2>/dev/null || true
cmtrace() {
  msg=$1; typ=${2:-1}; now=$(date '+%H:%M:%S.000'); day=$(date '+%m-%d-%Y')
  printf '<![LOG[%s]LOG]!><time="%s" date="%s" component="PublicLauncher" context="" type="%s" thread="%s" file="">\n' "$msg" "$now" "$day" "$typ" "$$" >> "$LOG" 2>/dev/null || true
}

clear
printf '\nCassandre Worker\n\n'
printf 'Installation dans la session de l utilisateur courant, sans mot de passe administrateur.\n\n'
cmtrace "Lanceur macOS utilisateur demarre."

if ! /usr/bin/curl -fsSL "$RAW_URL" -o "$TMP_SCRIPT"; then
  cmtrace "Echec du telechargement du bootstrap macOS." 3
  printf 'Impossible de telecharger l installateur.\nJournal : %s\n' "$LOG"
  printf '\nAppuyez sur Entree pour fermer.\n'; read dummy
  exit 1
fi
/bin/chmod 700 "$TMP_SCRIPT"
/bin/sh "$TMP_SCRIPT"
rc=$?
/bin/rm -f "$TMP_SCRIPT"

if [ "$rc" -eq 0 ]; then
  cmtrace "Installation macOS utilisateur terminee avec succes."
  printf '\nCassandre Worker est installe.\n'
else
  cmtrace "Installation macOS utilisateur en echec; code=$rc." 3
  printf '\nInstallation en echec.\nJournal : %s\n' "$LOG"
fi
printf '\nAppuyez sur Entree pour fermer.\n'
read dummy
exit "$rc"
