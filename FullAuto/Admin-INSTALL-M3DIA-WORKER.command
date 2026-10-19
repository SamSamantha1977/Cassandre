#!/bin/sh
set -u

RAW_URL="https://raw.githubusercontent.com/SamSamantha1977/Cassandre/main/install-macos.sh"
TMP_SCRIPT="/tmp/m3dia-install-macos-$$.sh"
LOG="/tmp/M3DIA-Worker-Installer.cmtrace.log"

cmtrace() {
  msg=$1; typ=${2:-1}; now=$(date '+%H:%M:%S.000'); day=$(date '+%m-%d-%Y')
  printf '<![LOG[%s]LOG]!><time="%s" date="%s" component="PublicLauncher" context="" type="%s" thread="%s" file="">\n' "$msg" "$now" "$day" "$typ" "$$" >> "$LOG" 2>/dev/null || true
}

clear
printf '\nCassandre Worker\n\n'
printf 'L installation va demander une autorisation administrateur une seule fois.\n\n'
cmtrace "Lanceur macOS demarre."

if ! /usr/bin/curl -fsSL "$RAW_URL" -o "$TMP_SCRIPT"; then
  cmtrace "Echec du telechargement du bootstrap macOS." 3
  printf 'Impossible de telecharger l installateur.\nJournal : %s\n' "$LOG"
  printf '\nAppuyez sur Entree pour fermer.\n'; read dummy
  exit 1
fi
/bin/chmod 700 "$TMP_SCRIPT"

ESCAPED=$(printf '%s' "$TMP_SCRIPT" | /usr/bin/sed "s/'/'\\\\''/g")
if /usr/bin/osascript -e "do shell script \"/bin/sh '$ESCAPED'\" with administrator privileges"; then
  rc=0
  cmtrace "Installation macOS terminee avec succes."
  printf '\nCassandre Worker est installe.\n'
else
  rc=$?
  cmtrace "Installation macOS annulee ou en echec; code=$rc." 3
  printf '\nInstallation annulee ou en echec.\nJournal : %s\n' "$LOG"
fi

/bin/rm -f "$TMP_SCRIPT"
printf '\nAppuyez sur Entree pour fermer.\n'
read dummy
exit "$rc"
