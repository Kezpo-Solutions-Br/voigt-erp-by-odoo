#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$SCRIPT_DIR/lib.sh"

require_docker_compose
ensure_docker_daemon
require_ide_runner_stopped

# Re-running is safe: native packages are reused from the private prefix and Python deps are hash-checked.
"$SCRIPT_DIR/ide-first-run.sh"

running_services="$(compose ps --status running --services)"
if printf '%s\n' "$running_services" | grep -qx odoo; then
  printf 'Parando somente o serviço Odoo em Compose para liberar o modo IDE...\n'
  compose stop odoo
fi

"$SCRIPT_DIR/start-ide.sh"
printf '\nInfraestrutura pronta. No IntelliJ, execute Run ou Debug em Voigt Odoo Local (IDE Debug/Test).\n'
printf 'O runner inicia o processo Odoo; o serviço PostgreSQL local permanece disponível na porta configurada.\n'
