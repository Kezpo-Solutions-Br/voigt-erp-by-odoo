#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$SCRIPT_DIR/lib.sh"

native_deps_only=false
if (($# > 0)); then
  [[ "$#" == 1 && "$1" == --native-deps-only ]] || die 'Uso: ide-first-run.sh [--native-deps-only]'
  native_deps_only=true
fi

require_docker_compose
require_ide_runner_stopped

if [[ ! -f "$ENV_FILE" ]]; then
  "$SCRIPT_DIR/setup.sh"
  die 'Edite local-infra/.env, substitua POSTGRES_PASSWORD e ODOO_ADMIN_PASSWD e execute ide-first-run.sh novamente.'
fi

chmod 600 "$ENV_FILE"
python3 - "$ENV_FILE" <<'PY'
import pathlib
import sys

env_file = pathlib.Path(sys.argv[1])
values = {}
for raw in env_file.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    values[key.strip()] = value.strip().strip("\"'")

required = ("POSTGRES_PASSWORD", "ODOO_ADMIN_PASSWD")
missing = [key for key in required if not values.get(key) or "replace-with-" in values[key]]
if missing:
    raise SystemExit("Preencha no local-infra/.env os campos obrigatórios: " + ", ".join(missing))
PY

if [[ "$native_deps_only" == false ]] && ! command -v python3.12 >/dev/null 2>&1; then
  die 'Python 3.12 não está disponível no host. Instale-o por um método aprovado para esta máquina; este script não instala interpretadores globalmente.'
fi

command -v apt-get >/dev/null 2>&1 || die 'apt-get não encontrado; este fluxo de preparação isolada requer um host Debian/Ubuntu compatível.'
command -v dpkg-query >/dev/null 2>&1 || die 'dpkg-query não encontrado; este fluxo de preparação isolada requer pacotes Debian.'
command -v dpkg-deb >/dev/null 2>&1 || die 'dpkg-deb não encontrado; instale as ferramentas de extração de pacotes Debian antes de continuar.'

release_codename=""
if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  source /etc/os-release
  release_codename="${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}"
fi
[[ -n "$release_codename" ]] || die 'Não foi possível identificar o codinome da distribuição. Não instalarei pacotes sem validar a versão do sistema.'

# Os pacotes são baixados e extraídos em local-infra/.local/native, nunca instalados
# pelo dpkg. Isso mantém bibliotecas de desenvolvimento e runtime fora do sistema.
dependency_groups=(
  'build-essential'
  'libffi-dev'
  'libfreetype-dev libfreetype6-dev'
  'libfribidi-dev'
  'libharfbuzz-dev'
  'libjpeg-turbo8-dev libjpeg62-turbo-dev libjpeg-dev'
  'libldap2-dev libldap-dev'
  'liblcms2-dev'
  'libmagic-dev'
  'libopenjp2-7-dev libopenjp2-dev'
  'libpq-dev'
  'libsasl2-dev'
  'libssl-dev'
  'libtiff-dev'
  'libwebp-dev'
  'libxcb1-dev'
  'libxml2-dev'
  'libxslt1-dev'
  'pkg-config'
  'zlib1g-dev'
)
runtime_dependency_groups=(
  'libffi8 libffi8t64'
  'libfreetype6'
  'libfribidi0'
  'libharfbuzz0b'
  'libjpeg-turbo8 libjpeg62-turbo'
  'libldap2 libldap-2.5-0'
  'liblcms2-2'
  'libmagic1t64 libmagic1'
  'libopenjp2-7'
  'libpq5'
  'libsasl2-2'
  'libssl3t64 libssl3'
  'libtiff6 libtiff6t64'
  'libwebp7 libwebp7t64'
  'libxcb1'
  'libxml2'
  'libxslt1.1'
  'zlib1g'
)

missing_packages=()
pending_groups=()
native_root="$INFRA_DIR/.local/native"
mkdir -p "$native_root"
chmod 700 "$native_root"
command -v flock >/dev/null 2>&1 || die 'flock não encontrado; instale util-linux para proteger a preparação concorrente.'
exec 9>"$native_root/.setup.lock"
flock -n 9 || die 'A preparação das dependências nativas locais já está em execução.'
stage_dir=""
cache_dir=""
link_tmp=""
cleanup_stage() {
  [[ -z "$stage_dir" || ! -d "$stage_dir" ]] || rm -rf -- "$stage_dir"
  [[ -z "$cache_dir" || ! -d "$cache_dir" ]] || rm -rf -- "$cache_dir"
  [[ -z "$link_tmp" || ! -L "$link_tmp" ]] || rm -f -- "$link_tmp"
}
trap cleanup_stage EXIT
local_manifest="$native_root/current/manifest.txt"
local_manifest_release=""
if [[ -f "$local_manifest" && -f "$native_root/current/plan.sha256" && -f "$native_root/current/packages.tsv" ]]; then
  IFS= read -r local_manifest_release < "$local_manifest" || true
fi

for group in "${dependency_groups[@]}"; do
  read -r -a candidates <<< "$group"
  installed=false
  available_locally=false
  for candidate in "${candidates[@]}"; do
    status="$(dpkg-query -W -f='${db:Status-Status}' "$candidate" 2>/dev/null || true)"
    if [[ "$status" == installed ]]; then
      installed=true
      break
    fi
    if [[ "$local_manifest_release" == "$release_codename" ]] && grep -Fxq "$candidate" "$local_manifest"; then
      available_locally=true
      break
    fi
  done
  [[ "$installed" == true || "$available_locally" == true ]] || pending_groups+=("$group")
done
for group in "${runtime_dependency_groups[@]}"; do
  available_locally=false
  for candidate in $group; do
    if [[ "$local_manifest_release" == "$release_codename" ]] && grep -Fxq "$candidate" "$local_manifest"; then
      available_locally=true
      break
    fi
  done
  [[ "$available_locally" == true ]] || pending_groups+=("$group")
done

if ((${#pending_groups[@]} > 0)); then
  command -v sudo >/dev/null 2>&1 || die 'Há dependências nativas ausentes e o comando sudo não está disponível.'
  printf 'Atualizando os índices APT para localizar pacotes de %s (sem instalar pacotes no sistema)...\n' "$release_codename"
  sudo apt-get update
fi

simulate_local_download() {
  local package="$1" output line
  output="$(apt-get -s -t "$release_codename" --reinstall install --no-install-recommends "$package" 2>&1)" || return 1
  while IFS= read -r line; do
    if [[ "$line" == Remv\ * ]]; then
      return 1
    fi
    [[ "$line" == Inst\ * ]] || continue
    [[ "$line" == *"/$release_codename"* ]] || return 1
  done <<< "$output"
}

for group in "${pending_groups[@]}"; do
  read -r -a candidates <<< "$group"
  selected=""
  for candidate in "${candidates[@]}"; do
    apt-cache show "$candidate" >/dev/null 2>&1 || continue
    if simulate_local_download "$candidate"; then
      selected="$candidate"
      break
    fi
  done
  [[ -n "$selected" ]] || die "Nenhuma alternativa instalável e compatível com $release_codename para: $group. Verifique os repositórios e prioridades do APT; nenhuma dependência foi instalada."
  missing_packages+=("$selected")
done

if ((${#missing_packages[@]} > 0)); then
  printf 'Validando o conjunto local de dependências para %s...\n' "$release_codename"
  if ! simulation_output="$(apt-get -s -t "$release_codename" --reinstall install --no-install-recommends "${missing_packages[@]}" 2>&1)"; then
    printf '%s\n' "$simulation_output" >&2
    die "O APT não encontrou uma combinação compatível com $release_codename. Nenhum pacote foi instalado; revise as fontes/prioridades APT antes de tentar novamente."
  fi
  while IFS= read -r line; do
    [[ "$line" == Inst\ * ]] || continue
    if [[ "$line" != *"/$release_codename"* ]]; then
      printf '%s\n' "$simulation_output" >&2
      die "A simulação selecionou um pacote fora da versão $release_codename: $line. Nenhum pacote foi instalado."
    fi
  done <<< "$simulation_output"
  mkdir -p "$native_root/releases"
  chmod 700 "$native_root" "$native_root/releases"
  mapfile -t existing_local_packages < <(tail -n +2 "$local_manifest" 2>/dev/null || true)
  all_local_packages=("${existing_local_packages[@]}" "${missing_packages[@]}")
  mapfile -t all_local_packages < <(printf '%s\n' "${all_local_packages[@]}" | sed '/^$/d' | sort -u)
  signature="$(printf '%s\n%s\n' "$release_codename" "${all_local_packages[*]}" "$simulation_output" | sha256sum | cut -c1-20)"
  release_dir="$native_root/releases/$signature"
  current_target="$(readlink "$native_root/current" 2>/dev/null || true)"
  if [[ "$current_target" != "releases/$signature" || ! -d "$release_dir" || ! -f "$release_dir/manifest.txt" || ! -f "$release_dir/plan.sha256" || ! -f "$release_dir/packages.tsv" ]]; then
    stage_dir="$(mktemp -d "$native_root/.stage-$signature.XXXXXX")"
    cache_dir="$(mktemp -d /tmp/voigt-odoo-apt.XXXXXX)"
    mkdir -p "$cache_dir/partial" "$stage_dir/root"
    chmod 755 "$cache_dir" "$cache_dir/partial"
    declare -A native_package_inventory=()
    if [[ -f "$native_root/current/packages.tsv" ]]; then
      while IFS=$'\t' read -r package_name package_version package_arch package_scope; do
        [[ -n "$package_name" ]] || continue
        native_package_inventory["$package_name:$package_arch"]="$package_name"$'\t'"$package_version"$'\t'"$package_arch"$'\t'"$package_scope"
      done < "$native_root/current/packages.tsv"
    fi
    if [[ -d "$native_root/current" ]]; then
      cp -a "$native_root/current/." "$stage_dir/root/"
      rm -f "$stage_dir/root/manifest.txt" "$stage_dir/root/plan.sha256" "$stage_dir/root/packages.tsv"
    fi
    printf 'Baixando dependências para uma área local temporária; nenhum pacote será registrado ou instalado no host.\n'
    sudo apt-get -y -t "$release_codename" --reinstall --download-only \
      -o "Dir::Cache::archives=$cache_dir/" install --no-install-recommends "${missing_packages[@]}"

    mapfile -d '' archives < <(find "$cache_dir" -maxdepth 1 -type f -name '*.deb' -print0)
    ((${#archives[@]} > 0)) || die 'O APT não baixou os arquivos .deb esperados; o prefixo local não foi alterado.'
    for archive in "${archives[@]}"; do
      package_name="$(dpkg-deb -f "$archive" Package)"
      package_version="$(dpkg-deb -f "$archive" Version)"
      package_arch="$(dpkg-deb -f "$archive" Architecture)"
      case "$package_name" in
        libc6|libc-bin|libstdc++6|libgcc-s1|base-files|systemd)
          printf 'Ignorando biblioteca/base do sistema no prefixo local: %s\n' "$package_name"
          package_scope='base-do-sistema'
          ;;
        *)
          dpkg-deb -x "$archive" "$stage_dir/root"
          package_scope='prefixo-local'
          ;;
      esac
      native_package_inventory["$package_name:$package_arch"]="$package_name"$'\t'"$package_version"$'\t'"$package_arch"$'\t'"$package_scope"
    done
    find "$stage_dir/root" -type f -name '*.a' -delete

    pg_config_binary="$(find "$stage_dir/root/usr" -type f -name pg_config -perm /111 -print -quit)"
    if [[ -n "$pg_config_binary" ]]; then
      mkdir -p "$stage_dir/root/bin"
      cat > "$stage_dir/root/bin/pg_config" <<'PG_CONFIG_WRAPPER'
#!/usr/bin/env bash
set -Eeuo pipefail
prefix="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
real_pg_config="$(find "$prefix/usr" -type f -name pg_config -perm /111 -print -quit)"
[[ -n "$real_pg_config" ]] || { printf 'pg_config não encontrado no prefixo nativo local.\n' >&2; exit 1; }
output="$("$real_pg_config" "$@")"
printf '%s\n' "$output" | sed "s|/usr|$prefix/usr|g"
PG_CONFIG_WRAPPER
      chmod 755 "$stage_dir/root/bin/pg_config"
    fi

    printf '%s\n' "$release_codename" "${all_local_packages[@]}" > "$stage_dir/manifest.txt"
    printf '%s' "$simulation_output" | sha256sum | cut -d ' ' -f1 > "$stage_dir/plan.sha256"
    for inventory_key in "${!native_package_inventory[@]}"; do
      printf '%s\n' "${native_package_inventory[$inventory_key]}"
    done | sort -t $'\t' -k1,1 -k3,3 > "$stage_dir/packages.tsv"
    if [[ -d "$release_dir" && ( ! -f "$release_dir/manifest.txt" || ! -f "$release_dir/plan.sha256" || ! -f "$release_dir/packages.tsv" ) ]]; then
      rm -rf -- "$release_dir"
    fi
    if [[ -d "$release_dir" ]]; then
      rm -rf -- "$stage_dir"
      stage_dir=""
    else
      mv -- "$stage_dir/root" "$release_dir"
      mv -- "$stage_dir/manifest.txt" "$release_dir/manifest.txt"
      mv -- "$stage_dir/plan.sha256" "$release_dir/plan.sha256"
      mv -- "$stage_dir/packages.tsv" "$release_dir/packages.tsv"
      rm -rf -- "$stage_dir"
      stage_dir=""
    fi
    link_tmp="$native_root/.current-$signature-$$"
    ln -s "releases/$signature" "$link_tmp"
    mv -Tf -- "$link_tmp" "$native_root/current"
    link_tmp=""
  fi
fi

if [[ "$native_deps_only" == true ]]; then
  printf '\nDependências nativas preparadas em local-infra/.local/native sem instalação no sistema.\n'
  exit 0
fi
"$SCRIPT_DIR/setup-ide.sh"
printf '\nPreparação inicial concluída. No IntelliJ, selecione Voigt Odoo Local (IDE Debug/Test).\n'
printf 'Para iniciar o ambiente de trabalho diário, execute local-infra/scripts/ide-day.sh.\n'
