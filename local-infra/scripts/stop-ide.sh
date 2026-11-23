#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$SCRIPT_DIR/lib.sh"
require_docker_compose
ensure_env_file
ensure_docker_daemon
require_ide_runner_stopped
require_compose_odoo_stopped
compose stop db
printf 'PostgreSQL local parado. Os dados persistentes foram preservados.\n'
