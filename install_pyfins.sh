#!/usr/bin/env bash
set -euo pipefail

PYFINS_REPO="git+https://github.com/reynoldxu/pyfins.git"

echo "Installing pyfins from GitHub..."

if command -v uv >/dev/null 2>&1; then
  UV_CACHE_DIR="${UV_CACHE_DIR:-.uv-cache}" uv pip install "${PYFINS_REPO}"
else
  python -m pip install "${PYFINS_REPO}"
fi

python - <<'PY'
import importlib

for module_name in ("pyfins", "fins"):
    try:
        module = importlib.import_module(module_name)
        print(f"Installed module import OK: {module_name} -> {module}")
        break
    except ImportError:
        continue
else:
    raise SystemExit("pyfins install finished, but neither 'pyfins' nor 'fins' could be imported.")
PY

echo "pyfins installation check finished."
