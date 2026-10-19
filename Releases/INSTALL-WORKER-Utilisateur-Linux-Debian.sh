#!/bin/sh
# Cassandre WORKER utilisateur - famille Linux Debian
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ "$(id -u)" -eq 0 ]; then echo 'Ne pas lancer avec sudo/root.' >&2; exit 10; fi
PYTHON=''
for p in python3.14 python3.13 python3.12 python3.11 python3; do
  if command -v "$p" >/dev/null 2>&1 && "$p" -c 'import sys;raise SystemExit(0 if sys.version_info >= (3,11) else 1)' >/dev/null 2>&1; then
    PYTHON=$p
    break
  fi
done
if [ -z "$PYTHON" ]; then echo 'Python 3.11+ doit etre accessible dans cette session.' >&2; exit 11; fi
exec "$PYTHON" "$ROOT/bootstrap_user.py" --family debian --mode install
