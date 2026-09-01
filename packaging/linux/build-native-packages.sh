#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
RELEASES="$ROOT/Releases"
SOURCE="$RELEASES/M3DIA-Worker-Linux.tar.gz"
TMP="${TMPDIR:-/tmp}/m3dia-linux-packages-$$"
STAGE="$TMP/stage"
PAYLOAD="$STAGE/usr/lib/m3dia-worker-bootstrap"
AFTER="$TMP/after-install.sh"

[ -f "$SOURCE" ] || { echo "Missing $SOURCE" >&2; exit 2; }
command -v fpm >/dev/null 2>&1 || { echo "fpm is required" >&2; exit 3; }
mkdir -p "$PAYLOAD"
tar -xzf "$SOURCE" -C "$PAYLOAD"
chmod +x "$PAYLOAD/install.sh" 2>/dev/null || true

cat > "$AFTER" <<'POST'
#!/bin/sh
set -eu
TARGET_USER="${SUDO_USER:-}"
if [ -z "$TARGET_USER" ] && [ -n "${PKEXEC_UID:-}" ] && command -v getent >/dev/null 2>&1; then TARGET_USER=$(getent passwd "$PKEXEC_UID" | cut -d: -f1 || true); fi
if [ -z "$TARGET_USER" ] && command -v loginctl >/dev/null 2>&1; then TARGET_USER=$(loginctl list-sessions --no-legend 2>/dev/null | awk '$3!="root" {print $3; exit}' || true); fi
[ -n "$TARGET_USER" ] || TARGET_USER="root"
M3DIA_INSTALL_USER="$TARGET_USER" /bin/sh /usr/lib/m3dia-worker-bootstrap/install.sh
POST
chmod 755 "$AFTER"

rm -f "$RELEASES/M3DIA-Worker.deb" "$RELEASES/M3DIA-Worker.rpm"

fpm -s dir -t deb -n m3dia-worker-bootstrap -v 5.1.0 -a all \
  --description "Cassandre Worker bootstrap" \
  --license "MIT" \
  --depends python3 \
  --after-install "$AFTER" \
  -C "$STAGE" \
  -p "$RELEASES/M3DIA-Worker.deb" .

fpm -s dir -t rpm -n m3dia-worker-bootstrap -v 5.1.0 -a noarch \
  --description "Cassandre Worker bootstrap" \
  --license "MIT" \
  --depends python3 \
  --after-install "$AFTER" \
  -C "$STAGE" \
  -p "$RELEASES/M3DIA-Worker.rpm" .

rm -rf "$TMP"
