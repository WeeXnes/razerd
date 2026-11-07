#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_DIR}"

# Build production renderer bundle if dist/index.html is missing and not running against dev server
if [[ -z "${VITE_DEV_SERVER_URL:-}" && ! -f "${PROJECT_DIR}/dist/index.html" ]]; then
  npm run build
fi

# Prefer system Electron on Linux (e.g. Arch /usr/bin/electron) or pre-downloaded local Electron binary
if [[ -x "/usr/bin/electron" ]]; then
  ELECTRON_BIN="/usr/bin/electron"
elif [[ -x "${PROJECT_DIR}/node_modules/electron/dist/electron" ]]; then
  ELECTRON_BIN="${PROJECT_DIR}/node_modules/electron/dist/electron"
elif command -v electron >/dev/null 2>&1; then
  ELECTRON_BIN="$(command -v electron)"
else
  ELECTRON_BIN="${PROJECT_DIR}/node_modules/.bin/electron"
fi

exec "${ELECTRON_BIN}" --class=razerd --ozone-platform-hint=auto "${PROJECT_DIR}" "$@"
