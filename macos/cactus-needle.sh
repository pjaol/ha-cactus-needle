#!/usr/bin/env bash
set -euo pipefail

LABEL="io.github.pjaol.cactus-needle"
LEGACY_LABEL="com.cactus.ha-router"
CACTUS_VERSION="${CACTUS_VERSION:-4.2.5}"
RELEASE="${CACTUS_NEEDLE_RELEASE:-main}"
PORT="${CACTUS_NEEDLE_PORT:-18080}"
STARTUP_TIMEOUT="${CACTUS_NEEDLE_STARTUP_TIMEOUT:-600}"
INSTALL_DIR="${CACTUS_NEEDLE_HOME:-${HOME}/Library/Application Support/Cactus Needle}"
AGENTS_DIR="${HOME}/Library/LaunchAgents"
PLIST_PATH="${AGENTS_DIR}/${LABEL}.plist"
LEGACY_PLIST_PATH="${AGENTS_DIR}/${LEGACY_LABEL}.plist"
SERVER_PATH="${INSTALL_DIR}/server.py"
VENV_DIR="${INSTALL_DIR}/venv"
PYTHON_PATH="${VENV_DIR}/bin/python"
DOMAIN="gui/$(id -u)"
RAW_SERVER_URL="https://raw.githubusercontent.com/pjaol/ha-cactus-needle/${RELEASE}/cactus_needle/server.py"

usage() {
  printf '%s\n' \
    "Usage: $(basename "$0") [install|update|status|restart|uninstall] [--purge]" \
    "" \
    "Environment overrides:" \
    "  CACTUS_NEEDLE_HOME     Installation directory" \
    "  CACTUS_NEEDLE_PORT     HTTP port (default: 18080)" \
    "  CACTUS_NEEDLE_STARTUP_TIMEOUT  First-start timeout in seconds" \
    "  CACTUS_NEEDLE_RELEASE  Git tag or branch to install (default: main)" \
    "  CACTUS_VERSION         cactus-compute version (default: 4.2.5)"
}

fail() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

validate_paths() {
  [[ -n "$INSTALL_DIR" ]] || fail "The installation directory cannot be empty."
  case "$INSTALL_DIR" in
    /|"$HOME")
      fail "Refusing to use a broad installation directory: $INSTALL_DIR"
      ;;
  esac
}

find_python() {
  local candidate
  for candidate in "${PYTHON:-}" python3 python3.13 python3.12 python3.11 python3.10 python3.9; do
    [[ -n "$candidate" ]] || continue
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c \
      'import sys; raise SystemExit(sys.version_info < (3, 9))' 2>/dev/null; then
      command -v "$candidate"
      return
    fi
  done
  fail "Python 3.9 or newer is required. Install it with Homebrew or python.org."
}

local_server_source() {
  local script_dir repo_server
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  repo_server="${script_dir}/../cactus_needle/server.py"
  [[ -f "$repo_server" ]] && printf '%s\n' "$repo_server"
}

fetch_server() {
  local source_path
  source_path="$(local_server_source || true)"
  if [[ -n "$source_path" ]]; then
    cp "$source_path" "$SERVER_PATH"
    return
  fi
  command -v curl >/dev/null 2>&1 || fail "curl is required to download the service."
  curl --fail --location --silent --show-error "$RAW_SERVER_URL" -o "$SERVER_PATH"
}

write_plist() {
  local plist_python="$1"
  INSTALL_DIR="$INSTALL_DIR" PLIST_PATH="$PLIST_PATH" PYTHON_PATH="$PYTHON_PATH" \
    SERVER_PATH="$SERVER_PATH" PORT="$PORT" LABEL="$LABEL" "$plist_python" - <<'PY'
import os
import plistlib
from pathlib import Path

install_dir = os.environ["INSTALL_DIR"]
payload = {
    "Label": os.environ["LABEL"],
    "ProgramArguments": [
        os.environ["PYTHON_PATH"],
        os.environ["SERVER_PATH"],
        "--host", "0.0.0.0",
        "--port", os.environ["PORT"],
    ],
    "EnvironmentVariables": {
        "CACTUS_TELEMETRY": "0",
        "HF_HOME": f"{install_dir}/cache/huggingface",
        "PYTHONUNBUFFERED": "1",
        "XDG_CACHE_HOME": f"{install_dir}/cache",
    },
    "KeepAlive": True,
    "ProcessType": "Interactive",
    "RunAtLoad": True,
    "StandardErrorPath": f"{install_dir}/logs/error.log",
    "StandardOutPath": f"{install_dir}/logs/service.log",
    "WorkingDirectory": install_dir,
}
path = Path(os.environ["PLIST_PATH"])
with path.open("wb") as stream:
    plistlib.dump(payload, stream, sort_keys=False)
PY
  plutil -lint "$PLIST_PATH" >/dev/null
}

stop_service() {
  launchctl bootout "${DOMAIN}/${LABEL}" 2>/dev/null || true
}

migrate_legacy_service() {
  launchctl bootout "${DOMAIN}/${LEGACY_LABEL}" 2>/dev/null || true
  if [[ -f "$LEGACY_PLIST_PATH" ]]; then
    rm "$LEGACY_PLIST_PATH"
  fi
}

wait_for_health() {
  local waited=0
  while (( waited < STARTUP_TIMEOUT )); do
    if curl --fail --silent --max-time 2 "http://127.0.0.1:${PORT}/health" >/dev/null; then
      printf 'Cactus Needle is ready at http://%s:%s\n' "$(hostname)" "$PORT"
      return
    fi
    sleep 1
    ((waited += 1))
  done
  printf 'Service did not become healthy. Recent errors:\n' >&2
  tail -n 30 "${INSTALL_DIR}/logs/error.log" >&2 || true
  return 1
}

install_service() {
  local system_python
  system_python="$(find_python)"
  mkdir -p "$INSTALL_DIR" "${INSTALL_DIR}/cache" "${INSTALL_DIR}/logs" "$AGENTS_DIR"
  fetch_server

  if [[ ! -x "$PYTHON_PATH" ]]; then
    "$system_python" -m venv "$VENV_DIR"
  fi
  "$PYTHON_PATH" -m pip install --disable-pip-version-check --quiet --upgrade pip
  "$PYTHON_PATH" -m pip install --disable-pip-version-check --quiet \
    "cactus-compute==${CACTUS_VERSION}"

  write_plist "$system_python"
  stop_service
  migrate_legacy_service
  launchctl bootstrap "$DOMAIN" "$PLIST_PATH"
  launchctl kickstart -k "${DOMAIN}/${LABEL}"
  wait_for_health
}

show_status() {
  if ! launchctl print "${DOMAIN}/${LABEL}" >/dev/null 2>&1; then
    printf 'Cactus Needle is not installed or not running.\n'
    return 1
  fi
  curl --fail --silent --show-error --max-time 5 \
    "http://127.0.0.1:${PORT}/health"
  printf '\n'
}

restart_service() {
  launchctl print "${DOMAIN}/${LABEL}" >/dev/null 2>&1 || \
    fail "Cactus Needle is not installed. Run '$0 install' first."
  launchctl kickstart -k "${DOMAIN}/${LABEL}"
  wait_for_health
}

uninstall_service() {
  local purge="${1:-}"
  stop_service
  rm -f "$PLIST_PATH"
  if [[ "$purge" == "--purge" ]]; then
    rm -rf "$INSTALL_DIR"
    printf 'Cactus Needle and its model cache were removed.\n'
  else
    printf 'Cactus Needle was uninstalled. Data remains at %s.\n' "$INSTALL_DIR"
    printf 'Run with --purge to remove the model cache too.\n'
  fi
}

command_name="${1:-install}"
shift || true
validate_paths
case "$command_name" in
  install|update) install_service ;;
  status) show_status ;;
  restart) restart_service ;;
  uninstall) uninstall_service "${1:-}" ;;
  -h|--help|help) usage ;;
  *) usage >&2; exit 2 ;;
esac
