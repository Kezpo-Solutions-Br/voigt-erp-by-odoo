#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$SCRIPT_DIR/lib.sh"

require_docker_compose
ensure_env_file
ensure_docker_daemon
require_ide_runner_stopped

# Prepara dependências do host sem instalação global; o hash evita reinstalação Python desnecessária.
"$SCRIPT_DIR/ide-first-run.sh"

running_services="$(compose ps --status running --services)"
if printf '%s\n' "$running_services" | grep -qx odoo; then
  printf 'Parando somente o serviço Odoo em Compose para liberar o runner de testes...\n'
  compose stop odoo
fi

"$SCRIPT_DIR/start-ide.sh"
printf '\nInfraestrutura de testes pronta. No IntelliJ, execute Run ou Debug em Voigt Odoo Local (Testes da Plataforma).\n'
printf 'O runner recria e remove um banco de testes isolado; o PostgreSQL permanece ativo ao final.\n'
