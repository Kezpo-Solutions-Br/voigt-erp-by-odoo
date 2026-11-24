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

native_prefix="$LOCAL_DIR/native/current"
[[ -d "$native_prefix" ]] || die 'Prefixo nativo local ausente. Execute ide-first-run.sh antes de preparar o SDK Python da IDE.'
wkhtmltox_prefix="$LOCAL_DIR/tooling/wkhtmltox/current/usr/local"
multiarch_triplet="$(dpkg-architecture -qDEB_HOST_MULTIARCH 2>/dev/null || true)"
[[ -n "$multiarch_triplet" ]] || die 'Não foi possível identificar a arquitetura multiarch do host com dpkg-architecture.'
library_dirs=""
binary_dirs=""
pkg_config_dirs=""
include_dirs=""
linker_flags=""
for candidate in \
  "$native_prefix/usr/lib/$multiarch_triplet" \
  "$native_prefix/lib/$multiarch_triplet" \
  "$native_prefix/usr/lib" \
  "$native_prefix/lib" \
  "$wkhtmltox_prefix/lib"; do
  if [[ -d "$candidate" ]]; then
    [[ -z "$library_dirs" ]] || library_dirs="$library_dirs:"
    library_dirs="$library_dirs$candidate"
  fi
done
[[ -n "$library_dirs" ]] || die 'O prefixo nativo local não contém diretórios de bibliotecas compartilhadas.'
for candidate in \
  "$native_prefix/usr/lib/$multiarch_triplet/pkgconfig" \
  "$native_prefix/lib/$multiarch_triplet/pkgconfig" \
  "$native_prefix/usr/lib/pkgconfig" \
  "$native_prefix/usr/share/pkgconfig"; do
  if [[ -d "$candidate" ]]; then
    [[ -z "$pkg_config_dirs" ]] || pkg_config_dirs="$pkg_config_dirs:"
    pkg_config_dirs="$pkg_config_dirs$candidate"
  fi
done
for candidate in "$native_prefix/usr/include" "$native_prefix/include"; do
  if [[ -d "$candidate" ]]; then
    [[ -z "$include_dirs" ]] || include_dirs="$include_dirs:"
    include_dirs="$include_dirs$candidate"
  fi
done
for candidate in \
  "$native_prefix/usr/lib/$multiarch_triplet" \
  "$native_prefix/lib/$multiarch_triplet" \
  "$native_prefix/usr/lib" \
  "$native_prefix/lib"; do
  if [[ -d "$candidate" ]]; then
    [[ -z "$linker_flags" ]] || linker_flags="$linker_flags "
    linker_flags="${linker_flags}-L$candidate"
  fi
done
for candidate in "$wkhtmltox_prefix/bin" "$native_prefix/usr/bin" "$native_prefix/bin"; do
  if [[ -d "$candidate" ]]; then
    [[ -z "$binary_dirs" ]] || binary_dirs="$binary_dirs:"
    binary_dirs="$binary_dirs$candidate"
  fi
done
ide_env_tmp="$LOCAL_DIR/.ide-runner.env.tmp.$$"
trap 'rm -f -- "$ide_env_tmp"' EXIT
chmod 700 "$LOCAL_DIR"
printf 'LD_LIBRARY_PATH=%s\nPATH=%s:%s\n' "$library_dirs" "$binary_dirs" "$PATH" > "$ide_env_tmp"
[[ -z "$pkg_config_dirs" ]] || printf 'PKG_CONFIG_PATH=%s:%s\n' "$pkg_config_dirs" "${PKG_CONFIG_PATH:-}" >> "$ide_env_tmp"
[[ -z "$include_dirs" ]] || {
  printf 'CPATH=%s:%s\n' "$include_dirs" "${CPATH:-}" >> "$ide_env_tmp"
  printf 'C_INCLUDE_PATH=%s:%s\n' "$include_dirs" "${C_INCLUDE_PATH:-}" >> "$ide_env_tmp"
}
[[ -z "$linker_flags" ]] || printf 'LDFLAGS=%s %s\n' "$linker_flags" "${LDFLAGS:-}" >> "$ide_env_tmp"
chmod 600 "$ide_env_tmp"
mv -f -- "$ide_env_tmp" "$LOCAL_DIR/ide-runner.env"
trap - EXIT

printf 'Ambiente seguro do runner IDE preparado em %s\n' "$LOCAL_DIR"
printf '\nConfiguração concluída. No IntelliJ, use %s como interpretador Python; o bootstrap permanece reservado à preparação automatizada.\n' \
  "$ROOT_DIR/.venv/bin/python"
