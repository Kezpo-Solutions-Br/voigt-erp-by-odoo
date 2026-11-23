#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$SCRIPT_DIR/lib.sh"

require_docker_compose
ensure_env_file
ROOT_DIR="$(cd "$INFRA_DIR/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
LOCAL_DIR="$INFRA_DIR/.local"
mkdir -p "$LOCAL_DIR" "$INFRA_DIR/data/ide-runner"
chmod 700 "$LOCAL_DIR" "$INFRA_DIR/data/ide-runner"

python_bin="$(command -v python3.12 || true)"
[[ -n "$python_bin" ]] || die 'O Odoo deste projeto requer Python 3.12. Instale python3.12 e python3.12-venv.'
if ! command -v pg_config >/dev/null 2>&1; then
  die 'Dependência de compilação ausente: pg_config. No Ubuntu/Debian, instale libpq-dev, libldap2-dev, libsasl2-dev, libxml2-dev, libxslt1-dev, libjpeg62-turbo-dev e build-essential; depois execute este script novamente.'
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  "$python_bin" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" "$INFRA_DIR/ide-runner/prepare_ide_files.py" \
  "$ENV_FILE" "$INFRA_DIR/.pgpass" "$LOCAL_DIR/ide-odoo.conf" "$INFRA_DIR/data/ide-runner"

printf 'Ambiente seguro do runner IDE preparado em %s\n' "$LOCAL_DIR"
printf 'Instalando dependências Python do Odoo na .venv do projeto...\n'
"$VENV_DIR/bin/python" -m pip install --disable-pip-version-check -r "$ROOT_DIR/requirements.txt" -c "$ROOT_DIR/constraints-voigt.txt"
printf '\nConfiguração concluída. Se o IntelliJ estiver aberto, selecione %s como interpretador do projeto.\n' "$VENV_DIR/bin/python"
