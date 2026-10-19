#!/bin/sh
set -eu

REPO="SamSamantha1977/Cassandre"
ASSET="M3DIA-Worker-Linux.tar.gz"
BASE="https://github.com/$REPO/releases/latest/download"
TMP="/tmp/m3dia-worker-install-$$"
ARCHIVE="$TMP/$ASSET"
PAYLOAD="$TMP/payload"
LOG="/var/log/m3dia-compute-bootstrap.cmtrace.log"

cmtrace() {
  msg=$1; typ=${2:-1}; now=$(date '+%H:%M:%S.000'); day=$(date '+%m-%d-%Y')
  printf '<![LOG[%s]LOG]!><time="%s" date="%s" component="PublicInstaller" context="" type="%s" thread="%s" file="">\n' "$msg" "$now" "$day" "$typ" "$$" >> "$LOG" 2>/dev/null || true
}

if [ "$(id -u)" -ne 0 ]; then
  if command -v pkexec >/dev/null 2>&1; then exec pkexec env M3DIA_INSTALL_USER="${USER:-}" /bin/sh "$0"; fi
  if command -v sudo >/dev/null 2>&1; then exec sudo M3DIA_INSTALL_USER="${USER:-}" /bin/sh "$0"; fi
  echo "M3DIA Worker : droits administrateur requis pour l'installation." >&2
  exit 10
fi

trap 'rm -rf "$TMP"' EXIT INT TERM
mkdir -p "$PAYLOAD"
cmtrace "Installation publique Linux commencee."

if command -v curl >/dev/null 2>&1; then curl -fsSL "$BASE/$ASSET" -o "$ARCHIVE"
elif command -v wget >/dev/null 2>&1; then wget -qO "$ARCHIVE" "$BASE/$ASSET"
else cmtrace "curl et wget absents." 3; exit 2
fi

if command -v curl >/dev/null 2>&1; then curl -fsSL "$BASE/SHA256SUMS.txt" -o "$TMP/SHA256SUMS.txt" 2>/dev/null || true
elif command -v wget >/dev/null 2>&1; then wget -qO "$TMP/SHA256SUMS.txt" "$BASE/SHA256SUMS.txt" 2>/dev/null || true
fi
if [ -s "$TMP/SHA256SUMS.txt" ] && command -v sha256sum >/dev/null 2>&1; then
  expected=$(awk -v f="$ASSET" '$2==f || $2=="*"f {print toupper($1); exit}' "$TMP/SHA256SUMS.txt" 2>/dev/null || true)
  if [ -n "$expected" ]; then actual=$(sha256sum "$ARCHIVE" | awk '{print toupper($1)}'); [ "$actual" = "$expected" ] || { cmtrace "Empreinte SHA-256 invalide." 3; exit 20; }; cmtrace "Empreinte SHA-256 validee."; fi
fi

tar -xzf "$ARCHIVE" -C "$PAYLOAD"
launcher=$(find "$PAYLOAD" -type f -name 'install.sh' -print -quit)
[ -n "$launcher" ] || { cmtrace "install.sh introuvable dans le package Linux." 3; exit 21; }
chmod +x "$launcher"
cmtrace "Execution du package Linux."
M3DIA_INSTALL_USER="${M3DIA_INSTALL_USER:-${SUDO_USER:-${USER:-root}}}" /bin/sh "$launcher"
rc=$?
[ "$rc" -eq 0 ] && cmtrace "Installation publique Linux terminee avec succes." || cmtrace "Installation publique Linux en echec; code=$rc." 3
exit "$rc"
