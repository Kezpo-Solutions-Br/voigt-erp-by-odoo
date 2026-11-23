#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$SCRIPT_DIR/lib.sh"
require_docker_compose
ensure_env_file
ensure_docker_daemon
require_ide_runner_stopped
printf 'This permanently deletes the local PostgreSQL database and Odoo filestore volumes.\n'
read -r -p 'Type DELETE to continue: ' confirmation
[[ "$confirmation" == DELETE ]] || { printf 'Cancelled.\n'; exit 0; }
compose down --volumes --remove-orphans
printf 'Local Odoo data has been removed. Run scripts/start.sh to create a fresh instance.\n'
