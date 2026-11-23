#!/usr/bin/env bash
set -Eeuo pipefail

INFRA_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$INFRA_DIR/compose.yaml"
ENV_FILE="$INFRA_DIR/.env"
IDE_RUNNER_PID_FILE="$INFRA_DIR/.local/ide-runner.pid"

# Exibe uma mensagem de erro no stderr e encerra o processo com status 1.
# Parâmetros: mensagem, ou conjunto de mensagens, que explica a falha.
# Resultado: encerra o script chamador; não retorna.
die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

# Confirma que a CLI Docker e o subcomando Docker Compose estão disponíveis.
# Resultado: retorna 0 quando ambos respondem; usa die caso algum pré-requisito falte.
require_docker_compose() {
  command -v docker >/dev/null 2>&1 || die 'Docker CLI was not found. Install Docker Desktop or Docker Engine with the Compose plugin.'
  docker compose version >/dev/null 2>&1 || die 'Docker Compose v2 is required (docker compose).'
}

# Garante que o arquivo local de ambiente exista, tenha permissão restrita e não use senhas de exemplo.
# Resultado: retorna 0 quando o arquivo está pronto; cria o modelo e encerra para edição se estiver ausente.
ensure_env_file() {
  if [[ ! -f "$ENV_FILE" ]]; then
    cp "$INFRA_DIR/.env.example" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    die "Created $ENV_FILE from .env.example. Replace both placeholder passwords, then run this command again."
  fi
  chmod 600 "$ENV_FILE"
  if grep -Eq 'replace-with-(a-long-random-password|another-long-random-password)' "$ENV_FILE"; then
    die "Replace placeholder credentials in $ENV_FILE before starting."
  fi
}

# Executa Docker Compose com os caminhos e o arquivo de ambiente deste projeto local.
# Parâmetros: opções e argumentos encaminhados sem alteração ao comando docker compose.
# Resultado: retorna o status e a saída do Docker Compose.
compose() {
  docker compose --project-directory "$INFRA_DIR" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

# Confirma que o daemon Docker pode ser acessado pelo usuário atual.
# Resultado: retorna 0 quando o daemon responde; encerra com orientação se estiver indisponível.
ensure_docker_daemon() {
  docker info >/dev/null 2>&1 || die 'Docker daemon is not reachable. Start Docker Desktop or the Docker service, then retry.'
}

# Impede operações Compose que possam interferir em um processo Odoo ativo na IDE.
# Resultado: retorna 0 se não houver runner ativo e remove marcador obsoleto; encerra se o PID ainda existir.
require_ide_runner_stopped() {
  [[ -f "$IDE_RUNNER_PID_FILE" ]] || return 0
  local pid
  pid="$(<"$IDE_RUNNER_PID_FILE")"
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    die "O runner do IntelliJ está ativo (PID $pid). Pare a configuração no IDE antes de iniciar/parar o Odoo em Compose."
  fi
  rm -f "$IDE_RUNNER_PID_FILE"
}

# Impede iniciar o runner da IDE enquanto o serviço Odoo em container estiver ativo.
# Resultado: retorna 0 quando o serviço está parado; encerra com instrução caso esteja em execução.
require_compose_odoo_stopped() {
  local running
  running="$(compose ps --status running --services)"
  if printf '%s\n' "$running" | grep -qx odoo; then
    die 'O serviço Odoo do Compose está ativo. Pare-o antes de iniciar o runner da IDE.'
  fi
}
