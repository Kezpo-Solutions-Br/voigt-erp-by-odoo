#!/usr/bin/env bash
set -Eeuo pipefail

INFRA_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$INFRA_DIR/compose.yaml"
ENV_FILE="$INFRA_DIR/.env"
IDE_RUNNER_PID_FILE="$INFRA_DIR/.local/ide-runner.pid"

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

require_docker_compose() {
  command -v docker >/dev/null 2>&1 || die 'Docker CLI was not found. Install Docker Desktop or Docker Engine with the Compose plugin.'
  docker compose version >/dev/null 2>&1 || die 'Docker Compose v2 is required (docker compose).'
}

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

compose() {
  docker compose --project-directory "$INFRA_DIR" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

ensure_docker_daemon() {
  docker info >/dev/null 2>&1 || die 'Docker daemon is not reachable. Start Docker Desktop or the Docker service, then retry.'
}

require_ide_runner_stopped() {
  [[ -f "$IDE_RUNNER_PID_FILE" ]] || return 0
  local pid
  pid="$(<"$IDE_RUNNER_PID_FILE")"
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    die "O runner do IntelliJ está ativo (PID $pid). Pare a configuração no IDE antes de iniciar/parar o Odoo em Compose."
  fi
  rm -f "$IDE_RUNNER_PID_FILE"
}

require_compose_odoo_stopped() {
  local running
  running="$(compose ps --status running --services)"
  if printf '%s\n' "$running" | grep -qx odoo; then
    die 'O serviço Odoo do Compose está ativo. Pare-o antes de iniciar o runner da IDE.'
  fi
}
