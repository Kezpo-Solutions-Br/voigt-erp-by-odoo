#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$SCRIPT_DIR/lib.sh"

require_docker_compose
if [[ ! -f "$ENV_FILE" ]]; then
  cp "$INFRA_DIR/.env.example" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  printf 'Created %s. Edit its two passwords, then run scripts/start.sh.\n' "$ENV_FILE"
else
  chmod 600 "$ENV_FILE"
  printf 'Environment file already exists: %s\n' "$ENV_FILE"
fi
