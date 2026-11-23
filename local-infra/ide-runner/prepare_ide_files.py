#!/usr/bin/env python3
"""Prepara credenciais locais com permissões restritas para o runner da IDE."""

from __future__ import annotations

import os
import pathlib
import sys


def load_compose_env(path: pathlib.Path) -> dict[str, str]:
    """Lê as variáveis do arquivo de ambiente usado pelo Compose.

    Args:
        path: Caminho do arquivo `.env` local.

    Returns:
        Mapeamento das chaves e valores encontrados no arquivo.

    Raises:
        RuntimeError: Se o arquivo não existir.
    """
    values: dict[str, str] = {}
    if not path.is_file():
        raise RuntimeError(f"Arquivo ausente: {path}. Execute local-infra/scripts/setup.sh.")
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def prepare_ide_files(
    env_file: pathlib.Path,
    pgpass_file: pathlib.Path,
    odoo_config: pathlib.Path,
    data_dir: pathlib.Path,
) -> dict[str, str]:
    """Gera os arquivos privados de acesso ao banco e a configuração local do Odoo.

    Valida as senhas, prepara os diretórios com permissões restritas e substitui os
    arquivos de configuração de forma atômica.

    Args:
        env_file: Arquivo `.env` que contém as credenciais locais.
        pgpass_file: Destino do arquivo de senha do PostgreSQL.
        odoo_config: Destino do arquivo de configuração do runner Odoo.
        data_dir: Diretório de dados exclusivo do processo Odoo executado pela IDE.

    Returns:
        Variáveis lidas do arquivo de ambiente.

    Raises:
        RuntimeError: Se faltarem senhas locais válidas.
        OSError: Se não for possível criar ou proteger os arquivos e diretórios.
    """
    values = load_compose_env(env_file)
    password = values.get("POSTGRES_PASSWORD", "")
    admin_password = values.get("ODOO_ADMIN_PASSWD", "")
    if not password or "replace-with-" in password or not admin_password or "replace-with-" in admin_password:
        raise RuntimeError("Substitua POSTGRES_PASSWORD e ODOO_ADMIN_PASSWD no arquivo local-infra/.env.")

    pgpass_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    odoo_config.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(pgpass_file.parent, 0o700)
    os.chmod(odoo_config.parent, 0o700)
    os.chmod(data_dir, 0o700)

    def escape_pgpass(value: str) -> str:
        """Escapa separadores e barras invertidas conforme a sintaxe do `.pgpass`."""
        return value.replace("\\", "\\\\").replace(":", "\\:").replace("\n", "")

    host = values.get("DB_IDE_BIND_ADDRESS", "127.0.0.1")
    if host == "0.0.0.0":
        host = "127.0.0.1"
    port = values.get("DB_IDE_PORT", "15432")
    user = values.get("POSTGRES_USER", "odoo")
    pgpass_content = ":".join(map(escape_pgpass, (host, port, "*", user, password))) + "\n"
    config_content = (
        "[options]\n"
        f"admin_passwd = {admin_password}\n"
        f"data_dir = {data_dir.resolve()}\n"
    )

    for target, content in ((pgpass_file, pgpass_content), (odoo_config, config_content)):
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
    return values


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit("Uso: prepare_ide_files.py ENV_FILE PGPASS_FILE ODOO_CONFIG DATA_DIR")
    try:
        prepare_ide_files(*(pathlib.Path(argument) for argument in sys.argv[1:]))
    except (OSError, RuntimeError) as error:
        raise SystemExit(str(error)) from error
