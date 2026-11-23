#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$SCRIPT_DIR/lib.sh"

require_docker_compose
ensure_env_file
ensure_docker_daemon
require_ide_runner_stopped

ROOT_DIR="$(cd "$INFRA_DIR/.." && pwd)"
if [[ "$(grep '^ODOO_SOURCE_REV=' "$ENV_FILE" | cut -d= -f2- || true)" == 'local-uncommitted' ]] && command -v git >/dev/null 2>&1; then
  revision="$(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || printf 'local-uncommitted')"
  if [[ -n "$revision" && "$revision" != local-uncommitted ]]; then
    sed "s/^ODOO_SOURCE_REV=.*/ODOO_SOURCE_REV=$revision/" "$ENV_FILE" > "$ENV_FILE.tmp"
    mv "$ENV_FILE.tmp" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
  fi
fi

compose up --build -d
printf '\nOdoo is starting. Open http://%s:%s after the container becomes healthy.\n' \
  "$(sed -n 's/^ODOO_BIND_ADDRESS=//p' "$ENV_FILE" | tail -n 1)" \
  "$(sed -n 's/^ODOO_PORT=//p' "$ENV_FILE" | tail -n 1)"
compose ps
