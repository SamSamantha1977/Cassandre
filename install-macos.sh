#!/bin/sh
set -eu

REPO="SamSamantha1977/Cassandre"
INSTALLER_URL="https://raw.githubusercontent.com/$REPO/main/install-user.py"
ROOT="$HOME/Library/Application Support/CassandreWorker"
LOG="$ROOT/Logs/bootstrap.cmtrace.log"
TMP="${TMPDIR:-/tmp}/cassandre-worker-install-$$"
PYINSTALLER="$TMP/install-user.py"

mkdir -p "$ROOT/Logs" "$TMP"
trap 'rm -rf "$TMP"' EXIT INT TERM
cmtrace() {
  msg=$1; typ=${2:-1}; now=$(date '+%H:%M:%S.000'); day=$(date '+%m-%d-%Y')
  printf '<![LOG[%s]LOG]!><time="%s" date="%s" component="PublicInstaller" context="" type="%s" thread="%s" file="">\n' "$msg" "$now" "$day" "$typ" "$$" >> "$LOG" 2>/dev/null || true
}
valid_python() {
  [ -n "${1:-}" ] && [ -x "$1" ] && "$1" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' >/dev/null 2>&1
}

cmtrace "Installation macOS utilisateur commencee; aucun droit administrateur requis."
PY=""
for candidate in "$(command -v python3 2>/dev/null || true)" "$(command -v python 2>/dev/null || true)" "$HOME/.local/bin/python3.12"; do
  if valid_python "$candidate"; then PY="$candidate"; break; fi
done

if [ -z "$PY" ]; then
  UV_DIR="$ROOT/Tools/uv"
  UV="$UV_DIR/uv"
  mkdir -p "$UV_DIR"
  if [ ! -x "$UV" ]; then
    cmtrace "Python 3.11+ absent : installation utilisateur de uv."
    /usr/bin/curl -LsSf 'https://astral.sh/uv/install.sh' -o "$TMP/uv-install.sh"
    UV_INSTALL_DIR="$UV_DIR" UV_NO_MODIFY_PATH=1 /bin/sh "$TMP/uv-install.sh"
  fi
  "$UV" python install 3.12 --no-progress
  PY=$("$UV" python find '>=3.11' 2>/dev/null | head -n 1 || true)
fi
valid_python "$PY" || { cmtrace "Python 3.11+ introuvable apres bootstrap utilisateur." 3; exit 23; }
cmtrace "Python retenu: $PY"

/usr/bin/curl -fsSL "$INSTALLER_URL" -o "$PYINSTALLER"
cmtrace "install-user.py telecharge depuis le depot public."
"$PY" "$PYINSTALLER"
rc=$?
[ "$rc" -eq 0 ] && cmtrace "Installation macOS utilisateur terminee avec succes." || cmtrace "Installation macOS utilisateur en echec; code=$rc." 3
exit "$rc"
