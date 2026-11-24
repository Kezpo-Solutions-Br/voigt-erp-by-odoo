#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$SCRIPT_DIR/lib.sh"

# Cria senhas fortes somente para valores vazios/de exemplo e preserva credenciais locais válidas.
# Resultado: atualiza local-infra/.env atomicamente com permissão 0600, sem imprimir os segredos.
ensure_local_test_credentials() {
  local existing_volume="false"
  docker volume inspect voigt-odoo-local_postgres-data >/dev/null 2>&1 && existing_volume="true"

  python3 - "$ENV_FILE" "$existing_volume" <<'PY'
import os
import pathlib
import secrets
import sys
import tempfile

env_file = pathlib.Path(sys.argv[1])
existing_volume = sys.argv[2] == "true"
lines = env_file.read_text(encoding="utf-8").splitlines()
required = {"POSTGRES_PASSWORD", "ODOO_ADMIN_PASSWD"}
seen = set()
updated = []
generated = False
for line in lines:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in line:
        updated.append(line)
        continue
    key, value = line.split("=", 1)
    key = key.strip()
    if key not in required:
        updated.append(line)
        continue
    seen.add(key)
    current = value.strip().strip("\"'")
    if not current or "replace-with-" in current:
        if existing_volume and key == "POSTGRES_PASSWORD":
            raise SystemExit(
                "O volume PostgreSQL já existe, mas POSTGRES_PASSWORD está vazio/de exemplo. "
                "Restaure a senha original de local-infra/.env para preservar o banco; "
                "não gere outra senha para esse volume."
            )
        value = secrets.token_urlsafe(36)
        generated = True
        updated.append(f"{key}={value}")
    else:
        updated.append(line)

missing = required - seen
if missing:
    raise SystemExit("O arquivo .env não contém as chaves obrigatórias: " + ", ".join(sorted(missing)))

new_content = "\n".join(updated) + "\n"
if generated:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{env_file.name}.tmp.", dir=env_file.parent)
    temporary = pathlib.Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(new_content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, env_file)
    finally:
        temporary.unlink(missing_ok=True)
os.chmod(env_file, 0o600)
print("Credenciais locais fortes geradas e protegidas." if generated else "Credenciais locais existentes preservadas e protegidas.")
PY
}

require_docker_compose
ensure_docker_daemon
if [[ ! -f "$ENV_FILE" ]]; then
  cp -- "$INFRA_DIR/.env.example" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  printf 'Arquivo local de ambiente criado em %s.\n' "$ENV_FILE"
fi
ensure_local_test_credentials

# Reutiliza toda a preparação e alternância de serviços do fluxo diário idempotente.
exec "$SCRIPT_DIR/ide-test-day.sh"
