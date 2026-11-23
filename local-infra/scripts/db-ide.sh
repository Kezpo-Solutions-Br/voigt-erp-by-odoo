#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$SCRIPT_DIR/lib.sh"

usage() {
  printf 'Uso: %s {start|status}\n' "$0"
  printf '  start   inicia somente o PostgreSQL e aguarda a verificação de saúde\n'
  printf '  status  mostra o estado do PostgreSQL e os parâmetros para o JetBrains\n'
}

require_docker_compose
ensure_env_file
ensure_docker_daemon

case "${1:-}" in
  start)
    require_ide_runner_stopped
    require_compose_odoo_stopped
    compose up --detach --wait db
    ;;
  status)
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

compose ps db
printf '\nConfiguração da fonte de dados PostgreSQL no JetBrains Database Tools:\n'
printf '  Driver:    PostgreSQL\n'
printf '  Host:      %s\n' "$(sed -n 's/^DB_IDE_BIND_ADDRESS=//p' "$ENV_FILE" | tail -n 1 | cut -d'#' -f1 | xargs)"
printf '  Porta:     %s\n' "$(sed -n 's/^DB_IDE_PORT=//p' "$ENV_FILE" | tail -n 1 | cut -d'#' -f1 | xargs)"
printf '  Usuário:   %s\n' "$(sed -n 's/^POSTGRES_USER=//p' "$ENV_FILE" | tail -n 1 | cut -d'#' -f1 | xargs)"
printf '  Database:  %s\n' "$(sed -n 's/^POSTGRES_DB=//p' "$ENV_FILE" | tail -n 1 | cut -d'#' -f1 | xargs)"
printf '  Senha:     valor definido em POSTGRES_PASSWORD no arquivo local-infra/.env\n'
printf '\nA porta publicada pelo Compose é somente local, conforme DB_IDE_BIND_ADDRESS.\n'
