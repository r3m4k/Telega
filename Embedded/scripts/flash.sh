#!/usr/bin/env bash
set -euo pipefail

script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
embedded_dir="$(CDPATH= cd -- "$script_dir/.." && pwd)"
env_file="$embedded_dir/.env"

if [[ ! -f "$env_file" ]]; then
    echo "Не найден файл локальной конфигурации: $env_file" >&2
    echo "Скопируйте .env.example в .env и задайте параметры." >&2
    exit 1
fi

set -a
# shellcheck source=/dev/null
. "$env_file"
set +a

: "${PROGRAM_NAME:?В .env не задана переменная PROGRAM_NAME}"
: "${BUILD_DIR:?В .env не задана переменная BUILD_DIR}"
: "${OPENOCD_EXE:?В .env не задана переменная OPENOCD_EXE}"
: "${OPENOCD_SCRIPTS_DIR:?В .env не задана переменная OPENOCD_SCRIPTS_DIR}"
: "${OPENOCD_CONFIG:?В .env не задана переменная OPENOCD_CONFIG}"

elf_file="${1:-$embedded_dir/$BUILD_DIR/$PROGRAM_NAME.elf}"

if [[ ! -f "$elf_file" ]]; then
    echo "ELF-файл не найден: $elf_file" >&2
    echo "Сначала выполните: scripts/build.sh build_all" >&2
    exit 1
fi

openocd_elf_file="$elf_file"

if [[ "${SYSTEM:-}" == "windows" ]]; then
    openocd_elf_file="$(cygpath -m "$elf_file")"
fi

"$OPENOCD_EXE" \
    -s "$OPENOCD_SCRIPTS_DIR" \
    -f "$OPENOCD_CONFIG" \
    -c "program $openocd_elf_file verify reset exit"
