# Сборка, загрузка и отладка Embedded-проекта

## Требуемое окружение

Для работы в Windows должны быть доступны через `PATH`:

- Bash (Git Bash, MSYS2 или WSL);
- GNU Make;
- ARM GNU Toolchain (`arm-none-eabi-gcc`, `g++`, `gdb`, `size`, `objcopy`);
- OpenOCD для загрузки и отладки.

Скрипты запускаются в Bash. В VS Code задачи также вызывают `bash` по имени.

## Локальная конфигурация

Создайте `Embedded/.env`, скопировав `Embedded/.env.example`, и заполните пути к инструментам:

```sh
SYSTEM=windows
PROGRAM_NAME=TelegaEmbedded
BUILD_DIR=Debug_Win
MAKE_COMMAND=make
GCC_PLACE=C:/BuildTools/SysGCC/arm-eabi

OPENOCD_EXE=C:/BuildTools/tool-openocd/bin/openOCD
OPENOCD_SCRIPTS_DIR=C:/BuildTools/tool-openocd/scripts
OPENOCD_CONFIG=C:/path/to/openocd/board.cfg
```

`.env` не добавляется в Git. Он загружается Bash, поэтому значения с пробелами должны быть заключены в кавычки.

Параметры `PROGRAM_NAME` и `BUILD_DIR` определяют имена и расположение артефактов:

```text
<BUILD_DIR>/<PROGRAM_NAME>.elf
<BUILD_DIR>/<PROGRAM_NAME>.hex
<BUILD_DIR>/<PROGRAM_NAME>.map
```

## Сборка

Скрипт `scripts/build.sh` загружает `.env`, проверяет обязательные переменные и запускает одну из разрешённых целей Make.

```sh
# Полная сборка
scripts/build.sh build_all

# Полная пересборка
scripts/build.sh rebuild_all

# Сборка или пересборка пользовательских файлов
scripts/build.sh build_user
scripts/build.sh rebuild_user

# Очистка
scripts/build.sh clean_all
```

Допустимые цели: `build_all`, `rebuild_all`, `clean_all`, `build_libs`, `rebuild_lib`, `clean_libs`, `build_user`, `rebuild_user`, `clean_user`.

## Загрузка прошивки

`scripts/flash.sh` не собирает проект самостоятельно. Он проверяет существование ELF и загружает его через OpenOCD.

```sh
# Загрузить ELF, определённый PROGRAM_NAME и BUILD_DIR
scripts/flash.sh

# Загрузить указанный ELF
scripts/flash.sh /path/to/firmware.elf
```

Для стандартной последовательности сначала выполните полную сборку, затем загрузку:

```sh
scripts/build.sh build_all
scripts/flash.sh
```

## VS Code

Проектные задачи находятся в `.vscode/tasks.json`:

- полная пересборка;
- пересборка пользовательских файлов и линковка;
- сборка пользовательских файлов и линковка;
- загрузка через OpenOCD.

`launch.json` предназначен для расширения Cortex-Debug. В пользовательском `settings.json` VS Code должны быть заданы машинно-зависимые пути:

```jsonc
{
    "embeddedDebug.compilerPath": "C:/path/to/arm-none-eabi-g++.exe",
    "embeddedDebug.openocdScriptsDir": "C:/path/to/openocd/scripts",
    "embeddedIncludeDir": "C:/path/to/arm-none-eabi/include",

    "cortex-debug.openocdPath": "C:/path/to/openocd.exe",
    "cortex-debug.gdbPath.windows": "C:/path/to/arm-none-eabi-gdb.exe"
}
```

Пользовательский файл VS Code в Windows расположен по пути:

```text
%APPDATA%\Code\User\settings.json
```

Конфигурация отладки использует стандартный OpenOCD-файл `board/stm32f3discovery.cfg` из `embeddedDebug.openocdScriptsDir`.

## Ограничения текущей Make-системы

- `rebuild_user` не создаёт каталоги объектов и не собирает библиотеки; для первой сборки используйте `build_all` или `rebuild_all`.
- `rebuild_lib` сейчас содержит ошибочную зависимость и требует отдельного исправления.
- Makefile содержит устаревшие настройки linker search path и библиотеки; их следует исправлять отдельно от скриптов и конфигурации VS Code.
