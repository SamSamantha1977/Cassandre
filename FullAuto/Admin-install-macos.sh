#!/bin/sh
set -eu

REPO="SamSamantha1977/Cassandre"
ASSET="M3DIA-Worker-macOS.zip"
BASE="https://github.com/$REPO/releases/latest/download"
TMP="/tmp/m3dia-worker-install-$$"
ZIP="$TMP/$ASSET"
PAYLOAD="$TMP/payload"
LOG="/var/log/m3dia-compute-bootstrap.cmtrace.log"

cmtrace() {
  msg=$1; typ=${2:-1}; now=$(date '+%H:%M:%S.000'); day=$(date '+%m-%d-%Y')
  printf '<![LOG[%s]LOG]!><time="%s" date="%s" component="PublicInstaller" context="" type="%s" thread="%s" file="">\n' "$msg" "$now" "$day" "$typ" "$$" >> "$LOG" 2>/dev/null || true
}

if [ "$(id -u)" -ne 0 ]; then
  echo "M3DIA Worker : droits administrateur requis pour l'installation." >&2
  exit 10
fi

trap 'rm -rf "$TMP"' EXIT INT TERM
mkdir -p "$PAYLOAD"
cmtrace "Installation publique macOS commencee."
/usr/bin/curl -fsSL "$BASE/$ASSET" -o "$ZIP"

if /usr/bin/curl -fsSL "$BASE/SHA256SUMS.txt" -o "$TMP/SHA256SUMS.txt" 2>/dev/null; then
  expected=$(awk -v f="$ASSET" '$2==f || $2=="*"f {print toupper($1); exit}' "$TMP/SHA256SUMS.txt" 2>/dev/null || true)
  if [ -n "$expected" ]; then
    actual=$(/usr/bin/shasum -a 256 "$ZIP" | awk '{print toupper($1)}')
    [ "$actual" = "$expected" ] || { cmtrace "Empreinte SHA-256 invalide." 3; exit 20; }
    cmtrace "Empreinte SHA-256 validee."
  fi
fi

/usr/bin/ditto -x -k "$ZIP" "$PAYLOAD"
launcher=$(find "$PAYLOAD" -type f -name 'install.command' -print -quit)
[ -n "$launcher" ] || { cmtrace "install.command introuvable dans le package macOS." 3; exit 21; }
/bin/chmod +x "$launcher"
/usr/bin/xattr -dr com.apple.quarantine "$(dirname "$launcher")" 2>/dev/null || true
cmtrace "Execution du package macOS."
/bin/sh "$launcher"
rc=$?
[ "$rc" -eq 0 ] && cmtrace "Installation publique macOS terminee avec succes." || cmtrace "Installation publique macOS en echec; code=$rc." 3
exit "$rc"
