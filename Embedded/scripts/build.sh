#!/usr/bin/env bash
set -euo pipefail

script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
embedded_dir="$(CDPATH= cd -- "$script_dir/.." && pwd)"
make_dir="$embedded_dir/make"
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

target="${1:-build_all}"

case "$target" in
    build_all|rebuild_all|clean_all|build_libs|rebuild_lib|clean_libs|build_user|rebuild_user|clean_user)
        ;;
    *)
        echo "Недопустимая цель Make: $target" >&2
        exit 2
        ;;
esac

: "${SYSTEM:?В .env не задана переменная SYSTEM}"
: "${PROGRAM_NAME:?В .env не задана переменная PROGRAM_NAME}"
: "${BUILD_DIR:?В .env не задана переменная BUILD_DIR}"
: "${GCC_PLACE:?В .env не задана переменная GCC_PLACE}"

make_command="${MAKE_COMMAND:-make}"

"$make_command" -C "$make_dir" -f Makefile.mk "$target" \
    "SYSTEM=$SYSTEM" \
    "PROGRAM_NAME=$PROGRAM_NAME" \
    "GCC_PLACE=$GCC_PLACE" \
    "BIN_PLACE=$embedded_dir/$BUILD_DIR"
