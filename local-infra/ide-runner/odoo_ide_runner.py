#!/usr/bin/env python3
"""Guarded host-side entry point for running/debugging Odoo from IntelliJ."""

from __future__ import annotations

import os
import pathlib
import runpy
import socket
import subprocess
import sys

from prepare_ide_files import prepare_ide_files


ROOT = pathlib.Path(__file__).resolve().parents[2]
INFRA = ROOT / "local-infra"
COMPOSE = INFRA / "compose.yaml"
ENV_FILE = INFRA / ".env"
MINIMUM_PYTHON = (3, 12)


def compose(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    command = [
        "docker", "compose", "--project-directory", str(INFRA),
        "--env-file", str(ENV_FILE), "-f", str(COMPOSE), *args,
    ]
    return subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=check)


def fail(message: str) -> None:
    print(f"Odoo IDE: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if sys.version_info < MINIMUM_PYTHON:
        actual = ".".join(map(str, sys.version_info[:3]))
        required = ".".join(map(str, MINIMUM_PYTHON))
        fail(
            f"Python {actual} foi selecionado pela IDE; o Odoo deste projeto requer Python >= {required}. "
            "Execute ./local-infra/scripts/ide-day.sh e configure o runner para usar "
            "$PROJECT_DIR$/.venv/bin/python (o nome antigo pode estar associado a um SDK de outro projeto)."
        )

    pid_file = INFRA / ".local" / "ide-runner.pid"
    pid_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        descriptor = os.open(pid_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        try:
            prior_pid = int(pid_file.read_text(encoding="ascii").strip())
            os.kill(prior_pid, 0)
        except (ValueError, ProcessLookupError):
            pid_file.unlink(missing_ok=True)
            descriptor = os.open(pid_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except PermissionError:
            fail("um processo com o PID registrado ainda existe e não pode ser inspecionado; verifique .local/ide-runner.pid.")
        else:
            fail(f"outro runner da IDE já está ativo (PID {prior_pid}).")
    os.write(descriptor, f"{os.getpid()}\n".encode("ascii"))
    os.close(descriptor)

    try:
        env = prepare_ide_files(
            ENV_FILE,
            INFRA / ".pgpass",
            INFRA / ".local" / "ide-odoo.conf",
            INFRA / "data" / "ide-runner",
        )
        database_host = env.get("DB_IDE_BIND_ADDRESS", "127.0.0.1")
        os.environ["PGHOST"] = "127.0.0.1" if database_host == "0.0.0.0" else database_host
        os.environ["PGPORT"] = env.get("DB_IDE_PORT", "15432")
        os.environ["PGUSER"] = env.get("POSTGRES_USER", "odoo")
        os.environ["PGPASSFILE"] = str(INFRA / ".pgpass")
        os.environ["ODOO_RC"] = str(INFRA / ".local" / "ide-odoo.conf")

        running = compose("ps", "--status", "running", "--services").stdout.splitlines()
        if "odoo" in running:
            fail("o serviço Odoo do Compose está ativo. Pare-o antes de depurar pelo IntelliJ com scripts/stop.sh.")
        compose("up", "--detach", "--wait", "db")
        result = compose("exec", "-T", "db", "pg_isready", "-U", os.environ["PGUSER"], "-d", env.get("POSTGRES_DB", "postgres"), check=False)
        if result.returncode != 0:
            fail("o PostgreSQL do Compose não ficou saudável; consulte scripts/logs.sh db.")
        with socket.create_connection((os.environ["PGHOST"], int(os.environ["PGPORT"])), timeout=3):
            pass
        print(f"PostgreSQL local pronto em {os.environ['PGHOST']}:{os.environ['PGPORT']}; iniciando Odoo pela IDE.")
        config = INFRA / ".local" / "ide-odoo.conf"
        os.environ["ODOO_RC"] = str(config)
        sys.argv = [str(ROOT / "odoo-bin"), *sys.argv[1:]]
        runpy.run_path(str(ROOT / "odoo-bin"), run_name="__main__")
    except FileNotFoundError:
        fail("Docker CLI não encontrado. Instale/inicie o Docker e repita.")
    except RuntimeError as error:
        fail(str(error))
    except subprocess.CalledProcessError as error:
        fail(f"não foi possível consultar o Compose: {error.stderr.strip() or error}")
    except OSError as error:
        fail(f"não foi possível acessar o PostgreSQL local: {error}")
    finally:
        try:
            if pid_file.read_text(encoding="ascii").strip() == str(os.getpid()):
                pid_file.unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    main()
