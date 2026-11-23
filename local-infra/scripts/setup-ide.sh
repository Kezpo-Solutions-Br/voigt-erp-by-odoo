#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$SCRIPT_DIR/lib.sh"

require_docker_compose
require_ide_runner_stopped
ensure_env_file
ROOT_DIR="$(cd "$INFRA_DIR/.." && pwd)"
LOCAL_DIR="$INFRA_DIR/.local"
mkdir -p "$LOCAL_DIR" "$INFRA_DIR/data/ide-runner"
chmod 700 "$LOCAL_DIR" "$INFRA_DIR/data/ide-runner"

python_bin="$(command -v python3.12 || true)"
[[ -n "$python_bin" ]] || die 'O Odoo deste projeto requer Python 3.12. Instale python3.12 e python3.12-venv.'
"$python_bin" "$INFRA_DIR/ide-runner/python_interpreter.py" --sync-deps
"$ROOT_DIR/.venv/bin/python" "$INFRA_DIR/ide-runner/prepare_ide_files.py" \
  "$ENV_FILE" "$INFRA_DIR/.pgpass" "$LOCAL_DIR/ide-odoo.conf" "$INFRA_DIR/data/ide-runner"

printf 'Ambiente seguro do runner IDE preparado em %s\n' "$LOCAL_DIR"
printf '\nConfiguração concluída. O IntelliJ pode usar o bootstrap %s como interpretador Python compartilhado.\n' \
  "$INFRA_DIR/ide-runner/python_interpreter.py"
