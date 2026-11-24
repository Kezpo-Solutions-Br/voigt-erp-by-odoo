#!/usr/bin/env python3
"""Executa a suíte padrão de testes do Odoo em um banco local isolado."""

from __future__ import annotations

import os
import pathlib
import runpy
import shutil
import socket
import subprocess
import sys
import sysconfig
import xml.sax.saxutils
import importlib.metadata

from prepare_ide_files import prepare_ide_files


ROOT = pathlib.Path(__file__).resolve().parents[2]
INFRA = ROOT / "local-infra"
WKHTMLTOX_PREFIX = INFRA / ".local" / "tooling" / "wkhtmltox" / "current" / "usr" / "local"
COMPOSE = INFRA / "compose.yaml"
ENV_FILE = INFRA / ".env"
TEST_DATABASE = "voigt_ide_tests"
MINIMUM_PYTHON = (3, 12)
INITIAL_LD_LIBRARY_PATH = os.environ.get("LD_LIBRARY_PATH", "")


def compose(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Executa Docker Compose com a definição e o ambiente desta infraestrutura.

    Args:
        *args: Argumentos encaminhados ao subcomando Docker Compose.
        check: Propaga falhas como exceções quando verdadeiro.

    Returns:
        Resultado do subprocesso com saída e código de retorno.
    """
    command = [
        "docker", "compose", "--project-directory", str(INFRA),
        "--env-file", str(ENV_FILE), "-f", str(COMPOSE), *args,
    ]
    return subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=check)


def fail(message: str) -> None:
    """Mostra uma orientação de erro e termina o runner com status 1.

    Args:
        message: Descrição do problema e da ação sugerida.

    Raises:
        SystemExit: Sempre, com código de saída 1.
    """
    print(f"Testes Odoo IDE: {message}", file=sys.stderr)
    raise SystemExit(1)


def verify_project_interpreter() -> None:
    """Confirma que o IntelliJ iniciou o Python compartilhado pelos dois runners.

    Raises:
        SystemExit: Se a `.venv` do projeto não existir ou outro Python foi selecionado.
    """
    expected = ROOT / ".venv" / "bin" / "python"
    try:
        expected_path = expected.resolve(strict=True)
        actual_path = pathlib.Path(sys.executable).resolve(strict=True)
    except OSError:
        fail("a .venv compartilhada não está pronta; execute ./local-infra/scripts/ide-test-first-run.sh.")
    if actual_path != expected_path:
        fail(
            "o IntelliJ selecionou outro interpretador. Os runners da aplicação e dos testes compartilham "
            f"{expected}; selecione esse mesmo Python na configuração de testes."
        )


def configure_local_native_build_environment(native_prefix: pathlib.Path) -> None:
    """Expose private headers and pkg-config metadata to optional Python builds.

    Args:
        native_prefix: Active, versioned native dependency prefix for this checkout.
    """
    multiarch_dirs = list(native_prefix.glob("usr/lib/*-linux-gnu")) + list(
        native_prefix.glob("lib/*-linux-gnu")
    )
    pkg_config_dirs = [
        *(directory / "pkgconfig" for directory in multiarch_dirs),
        native_prefix / "usr/lib/pkgconfig",
        native_prefix / "usr/share/pkgconfig",
    ]
    include_dirs = [
        native_prefix / "usr/include",
        native_prefix / "usr/include/cairo",
        pathlib.Path("/usr/include/xcb"),
        native_prefix / "include",
        pathlib.Path(sysconfig.get_path("include")),
        pathlib.Path(sysconfig.get_path("platinclude")),
    ]
    library_dirs = [
        *multiarch_dirs,
        native_prefix / "usr/lib",
        native_prefix / "lib",
        WKHTMLTOX_PREFIX / "lib",
    ]

    def prepend(variable: str, paths: list[pathlib.Path]) -> None:
        values = [str(path) for path in paths if path.is_dir()]
        current = os.environ.get(variable, "")
        if current:
            values.append(current)
        if values:
            os.environ[variable] = os.pathsep.join(values)

    prepend("PKG_CONFIG_PATH", pkg_config_dirs)
    # Debian's cairo.pc emits /usr/include/cairo while the headers are privately
    # extracted. Add that header directory directly; a global sysroot also hides
    # the host Python headers and headers for optional system build dependencies.
    os.environ.pop("PKG_CONFIG_SYSROOT_DIR", None)
    prepend("CPATH", include_dirs)
    prepend("C_INCLUDE_PATH", include_dirs)
    prepend("LD_LIBRARY_PATH", library_dirs)
    linker_flags = [f"-L{path}" for path in library_dirs if path.is_dir()]
    current_ldflags = os.environ.get("LDFLAGS", "")
    if current_ldflags:
        linker_flags.append(current_ldflags)
    if linker_flags:
        os.environ["LDFLAGS"] = " ".join(linker_flags)


def restart_with_native_loader_path(native_prefix: pathlib.Path) -> None:
    """Restart once so the dynamic loader sees private libraries from process start.

    Args:
        native_prefix: Active, versioned native dependency prefix for this checkout.
    """
    required_dirs = [
        *native_prefix.glob("usr/lib/*-linux-gnu"),
        *native_prefix.glob("lib/*-linux-gnu"),
        native_prefix / "usr/lib",
        native_prefix / "lib",
        WKHTMLTOX_PREFIX / "lib",
    ]
    initial_dirs = {
        pathlib.Path(item).resolve()
        for item in INITIAL_LD_LIBRARY_PATH.split(os.pathsep)
        if item and pathlib.Path(item).is_dir()
    }
    if all(path.resolve() in initial_dirs for path in required_dirs if path.is_dir()):
        return

    os.execve(sys.executable, [sys.executable, *sys.argv], os.environ)


def prepare_runtime() -> dict[str, str]:
    """Sincroniza dependências, configura credenciais e inicia o PostgreSQL local.

    Returns:
        Variáveis locais carregadas de `local-infra/.env`.

    Raises:
        subprocess.CalledProcessError: Se o bootstrap ou o Compose falhar.
        RuntimeError: Se as credenciais locais forem inválidas.
        OSError: Se o banco não aceitar conexões TCP.
    """
    bootstrap = INFRA / "ide-runner" / "python_interpreter.py"
    subprocess.run([sys.executable, str(bootstrap), "--sync-deps"], cwd=ROOT, check=True)

    # ReportLab 4.1 leaves bitmap rendering as an optional extra. Odoo's barcode
    # QWeb widget uses it, so install its Cairo backend in the shared project venv.
    try:
        importlib.metadata.version("rlPyCairo")
    except importlib.metadata.PackageNotFoundError:
        install_backend = subprocess.run(
            [
                sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
                "reportlab[pycairo]==4.1.0", "-c", str(ROOT / "constraints-voigt.txt"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if install_backend.returncode:
            details = install_backend.stderr.strip() or install_backend.stdout.strip()
            details = "\n".join(details.splitlines()[-80:])
            raise RuntimeError(
                "não foi possível compilar o backend Cairo do ReportLab. Confira no erro abaixo se "
                "os headers privados de Cairo e os headers do Python estão disponíveis.\n"
                f"{details or f'pip terminou com código {install_backend.returncode}'}"
            )

    values = prepare_ide_files(
        ENV_FILE,
        INFRA / ".pgpass",
        INFRA / ".local" / "ide-tests.conf",
        INFRA / "data" / "ide-tests",
    )
    database_host = values.get("DB_IDE_BIND_ADDRESS", "127.0.0.1")
    os.environ["PGHOST"] = "127.0.0.1" if database_host == "0.0.0.0" else database_host
    os.environ["PGPORT"] = values.get("DB_IDE_PORT", "15432")
    os.environ["PGUSER"] = values.get("POSTGRES_USER", "odoo")
    os.environ["PGPASSFILE"] = str(INFRA / ".pgpass")
    os.environ["ODOO_RC"] = str(INFRA / ".local" / "ide-tests.conf")

    if values.get("POSTGRES_DB", "postgres") == TEST_DATABASE:
        fail(f"POSTGRES_DB não pode usar o nome reservado {TEST_DATABASE!r}.")

    compose("up", "--detach", "--wait", "db")
    result = compose(
        "exec", "-T", "db", "pg_isready", "-U", os.environ["PGUSER"],
        "-d", values.get("POSTGRES_DB", "postgres"), check=False,
    )
    if result.returncode != 0:
        fail("o PostgreSQL do Compose não ficou saudável; consulte ./local-infra/scripts/logs.sh db.")
    with socket.create_connection((os.environ["PGHOST"], int(os.environ["PGPORT"])), timeout=3):
        pass
    return values


def run_odoo_db_command(*args: str) -> None:
    """Executa um comando oficial de gerenciamento de banco do `odoo-bin`.

    Args:
        *args: Subcomando e opções após `odoo-bin db`.

    Raises:
        subprocess.CalledProcessError: Se o comando oficial retornar erro.
    """
    subprocess.run([sys.executable, str(ROOT / "odoo-bin"), "db", *args], cwd=ROOT, check=True)


def reset_test_database() -> None:
    """Cria uma base limpa com o procedimento oficial de inicialização do Odoo.

    Inclui dados de demonstração usados por testes da plataforma e substitui
    exclusivamente o banco reservado aos testes desta infraestrutura.

    Raises:
        subprocess.CalledProcessError: Se a inicialização oficial do banco falhar.
        OSError: Se não for possível limpar o filestore remanescente.
    """
    filestore = INFRA / "data" / "ide-tests" / "filestore" / TEST_DATABASE
    if filestore.is_dir():
        shutil.rmtree(filestore)
    run_odoo_db_command("init", "--force", "--with-demo", TEST_DATABASE)


def acquire_runner_lock() -> pathlib.Path:
    """Adquire o marcador compartilhado que impede dois processos Odoo simultâneos.

    Returns:
        Caminho do marcador que deve ser removido no encerramento.

    Raises:
        SystemExit: Se outro runner estiver ativo ou o PID não puder ser inspecionado.
    """
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
            fail("o PID registrado existe, mas não pode ser inspecionado; verifique local-infra/.local/ide-runner.pid.")
        else:
            fail(f"outro runner Odoo está ativo (PID {prior_pid}); encerre-o antes dos testes.")
    os.write(descriptor, f"{os.getpid()}\n".encode("ascii"))
    os.close(descriptor)
    return pid_file


def remove_test_database() -> None:
    """Remove o banco de teste ao terminar e mantém o PostgreSQL compartilhado ativo.

    Raises:
        subprocess.CalledProcessError: Se o comando oficial não conseguir remover o banco.
    """
    run_odoo_db_command("drop", TEST_DATABASE)


def main() -> None:
    """Executa os testes padrão de todos os módulos Odoo em um banco descartável.

    O runner impede execuções simultâneas com o Odoo em container ou na IDE,
    recria o banco reservado pelo comando oficial de inicialização, inicializa
    e atualiza os módulos, executa as tags padrão e remove banco e filestore.
    """
    if sys.version_info < MINIMUM_PYTHON:
        actual = ".".join(map(str, sys.version_info[:3]))
        fail(f"Python {actual} não atende ao mínimo 3.12; selecione $PROJECT_DIR$/.venv/bin/python no IntelliJ.")
    verify_project_interpreter()

    native_prefix = INFRA / ".local" / "native" / "current"
    if not native_prefix.is_dir():
        fail("dependências locais ausentes; execute ./local-infra/scripts/ide-test-first-run.sh.")
    binary_dirs = [WKHTMLTOX_PREFIX / "bin", native_prefix / "usr" / "bin", native_prefix / "bin"]
    os.environ["PATH"] = os.pathsep.join(
        [*(str(path) for path in binary_dirs if path.is_dir()), os.environ.get("PATH", "")]
    )
    configure_local_native_build_environment(native_prefix)
    restart_with_native_loader_path(native_prefix)
    private_font_dirs = [
        native_prefix / "usr" / "share" / "fonts" / name
        for name in ("truetype/dejavu", "truetype/freefont", "truetype/liberation", "opentype/noto")
    ]
    existing_font_dirs = [path for path in private_font_dirs if path.is_dir()]
    if existing_font_dirs:
        font_config = INFRA / ".local" / "ide-test-fonts.conf"
        font_dirs_xml = "\n".join(
            f"  <dir>{xml.sax.saxutils.escape(str(path))}</dir>" for path in existing_font_dirs
        )
        font_config.write_text(
            "<?xml version=\"1.0\"?>\n<!DOCTYPE fontconfig SYSTEM \"/etc/fonts/fonts.dtd\">\n"
            "<fontconfig>\n  <include>/etc/fonts/fonts.conf</include>\n"
            f"{font_dirs_xml}\n</fontconfig>\n",
            encoding="utf-8",
        )
        os.environ["FONTCONFIG_FILE"] = str(font_config)
    library_dirs = [native_prefix / "usr" / "lib", native_prefix / "lib"]
    libpq = [
        file
        for directory in library_dirs if directory.is_dir()
        for file in (*directory.glob("libpq.so.5"), *directory.glob("*-linux-gnu/libpq.so.5"))
        if file.is_file()
    ]
    if not libpq:
        fail("libpq.so.5 ausente no prefixo local; execute ./local-infra/scripts/ide-test-first-run.sh.")
    if libpq[0].parent.resolve() not in {
        pathlib.Path(item).resolve()
        for item in os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep)
        if item and pathlib.Path(item).is_dir()
    }:
        fail("LD_LIBRARY_PATH não foi carregado; execute ide-test-first-run.sh, confirme ENV_FILES e recarregue a configuração IntelliJ de testes.")

    if not ENV_FILE.is_file():
        fail("local-infra/.env não existe; execute ./local-infra/scripts/ide-test-first-run.sh primeiro.")
    pid_file = acquire_runner_lock()

    test_db_created = False
    try:
        running = compose("ps", "--status", "running", "--services").stdout.splitlines()
        if "odoo" in running:
            fail("o serviço Odoo do Compose está ativo; execute ./local-infra/scripts/ide-test-day.sh para alternar com segurança para os testes.")
        values = prepare_runtime()
        reset_test_database()
        test_db_created = True

        print(
            f"Executando testes padrão do Odoo no banco temporário {TEST_DATABASE}; "
            "a suíte será removida ao encerrar.",
            flush=True,
        )
        sys.argv = [
            str(ROOT / "odoo-bin"),
            "--database", TEST_DATABASE,
            "--init", "all",
            "--update", "all",
            "--test-tags", "+standard",
            "--stop-after-init",
        ]
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        runpy.run_path(str(ROOT / "odoo-bin"), run_name="__main__")
    except FileNotFoundError:
        fail("Docker CLI ou executável necessário não encontrado; confira Docker e a preparação do ambiente.")
    except subprocess.CalledProcessError as error:
        details = error.stderr.strip() if error.stderr else str(error)
        fail(f"falha ao preparar as dependências ou o PostgreSQL: {details}")
    except RuntimeError as error:
        fail(str(error))
    except OSError as error:
        fail(f"não foi possível preparar o ambiente local: {error}")
    finally:
        if test_db_created:
            try:
                remove_test_database()
            except (OSError, subprocess.CalledProcessError) as error:
                print(f"Aviso: não foi possível remover o banco temporário {TEST_DATABASE}: {error}", file=sys.stderr)
        try:
            if pid_file.read_text(encoding="ascii").strip() == str(os.getpid()):
                pid_file.unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    main()
