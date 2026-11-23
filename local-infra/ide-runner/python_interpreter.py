#!/usr/bin/env python3
"""Stable IntelliJ interpreter shim that creates and delegates to the project venv."""

from __future__ import annotations

import hashlib
import os
import pathlib
import shutil
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[2]
VENV = ROOT / ".venv"
VENV_PYTHON = VENV / "bin" / "python"
REQUIREMENTS = ROOT / "requirements.txt"
CONSTRAINTS = ROOT / "constraints-voigt.txt"
DEPENDENCY_MARKER = VENV / ".odoo-requirements.sha256"
RUNNER_SCRIPT = "odoo_ide_runner.py"
MINIMUM_PYTHON = (3, 12)
NATIVE_PREFIX = ROOT / "local-infra" / ".local" / "native" / "current"


def configure_local_native_dependencies() -> None:
    """Expose project-local headers, pkg-config metadata, tools, and shared libraries."""
    if not NATIVE_PREFIX.is_dir():
        return

    library_dirs = [
        *NATIVE_PREFIX.glob("usr/lib/*-linux-gnu"),
        *NATIVE_PREFIX.glob("lib/*-linux-gnu"),
        NATIVE_PREFIX / "usr/lib",
        NATIVE_PREFIX / "lib",
        NATIVE_PREFIX / "usr/local/lib",
    ]
    pkg_config_dirs = [
        *NATIVE_PREFIX.glob("usr/lib/*-linux-gnu/pkgconfig"),
        NATIVE_PREFIX / "usr/lib/pkgconfig",
        NATIVE_PREFIX / "usr/share/pkgconfig",
    ]
    include_dirs = [NATIVE_PREFIX / "usr/include", NATIVE_PREFIX / "include"]
    binary_dirs = [NATIVE_PREFIX / "bin", NATIVE_PREFIX / "usr/bin"]

    def prepend(variable: str, paths: list[pathlib.Path]) -> None:
        current = os.environ.get(variable, "")
        values = [str(path) for path in paths if path.is_dir()]
        if current:
            values.append(current)
        if values:
            os.environ[variable] = os.pathsep.join(values)

    prepend("LD_LIBRARY_PATH", library_dirs)
    prepend("PKG_CONFIG_PATH", pkg_config_dirs)
    prepend("CPATH", include_dirs)
    prepend("C_INCLUDE_PATH", include_dirs)
    prepend("PATH", binary_dirs)
    # Put local shared-library directories ahead of /usr for extension builds.
    # LIBRARY_PATH is intentionally left untouched: GNU ld may prefer a .a file
    # from there over the required shared object when building Python extensions.
    linker_flags = [f"-L{path}" for path in library_dirs if path.is_dir()]
    current_linker_flags = os.environ.get("LDFLAGS", "")
    if current_linker_flags:
        linker_flags.append(current_linker_flags)
    if linker_flags:
        os.environ["LDFLAGS"] = " ".join(linker_flags)


def ensure_venv() -> None:
    if VENV.exists() and not VENV.is_dir():
        raise RuntimeError(f"{VENV} existe e não é um diretório; mova-o e tente novamente.")
    if not VENV_PYTHON.exists():
        python = shutil.which("python3.12")
        if not python:
            raise RuntimeError("Python 3.12 não foi encontrado no PATH; instale Python 3.12 e python3.12-venv.")
        print(f"Criando ambiente virtual isolado em {VENV}", flush=True)
        subprocess.run([python, "-m", "venv", str(VENV)], check=True)
    if not VENV_PYTHON.is_file() or not os.access(VENV_PYTHON, os.X_OK):
        raise RuntimeError(f"Não foi possível criar um interpretador executável em {VENV_PYTHON}.")
    version = subprocess.run(
        [str(VENV_PYTHON), "-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    version_parts = tuple(int(part) for part in version.split("."))
    if version_parts < MINIMUM_PYTHON:
        raise RuntimeError(
            f"A .venv existente usa Python {version}; Odoo requer Python >= 3.12. "
            "Mova/remova a .venv antiga e execute ./local-infra/scripts/ide-first-run.sh novamente."
        )


def dependency_hash() -> str:
    digest = hashlib.sha256()
    digest.update(sys.version.encode("utf-8"))
    for requirement_file in (REQUIREMENTS, CONSTRAINTS):
        digest.update(requirement_file.name.encode("utf-8"))
        digest.update(requirement_file.read_bytes())
    native_manifest = NATIVE_PREFIX / "manifest.txt"
    if native_manifest.is_file():
        digest.update(native_manifest.read_bytes())
    native_plan = NATIVE_PREFIX / "plan.sha256"
    if native_plan.is_file():
        digest.update(native_plan.read_bytes())
    native_packages = NATIVE_PREFIX / "packages.tsv"
    if native_packages.is_file():
        digest.update(native_packages.read_bytes())
    return digest.hexdigest()


def synchronize_dependencies(force: bool = False) -> None:
    expected = dependency_hash()
    try:
        current = DEPENDENCY_MARKER.read_text(encoding="ascii").strip()
    except FileNotFoundError:
        current = ""
    if current == expected and not force:
        return

    if not shutil.which("pg_config"):
        raise RuntimeError(
            "pg_config não está disponível. Execute local-infra/scripts/ide-first-run.sh para preparar "
            "as dependências nativas em local-infra/.local/native; esse fluxo não instala bibliotecas no sistema."
        )

    print("Sincronizando dependências Python a partir de requirements.txt e constraints-voigt.txt", flush=True)
    subprocess.run(
        [
            str(VENV_PYTHON), "-m", "pip", "install", "--disable-pip-version-check",
            "-r", str(REQUIREMENTS), "-c", str(CONSTRAINTS),
        ],
        cwd=ROOT,
        check=True,
    )
    temporary_marker = DEPENDENCY_MARKER.with_suffix(".tmp")
    temporary_marker.write_text(expected + "\n", encoding="ascii")
    os.replace(temporary_marker, DEPENDENCY_MARKER)


def main() -> None:
    configure_local_native_dependencies()
    args = sys.argv[1:]
    dependency_mode = args[0] if args and args[0] in {"--sync-deps", "--install-deps"} else ""
    force_dependency_sync = dependency_mode == "--install-deps"
    if dependency_mode:
        args = args[1:]

    try:
        ensure_venv()
        if dependency_mode or any(pathlib.Path(argument).name == RUNNER_SCRIPT for argument in args):
            synchronize_dependencies(force=force_dependency_sync)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Runner Odoo IDE: {error}", file=sys.stderr, flush=True)
        raise SystemExit(1) from error

    if dependency_mode and not args:
        return
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), *args])


if __name__ == "__main__":
    main()
