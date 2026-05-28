"""Автоматическая разметка файлов статических буферов и измерительных проездов."""

# System imports
import re
from pathlib import Path
from typing import Union

# User imports
from .models import DiscoveryResult, RunDirection, RunFiles

##########################################################


STATIC_PATTERN = re.compile(r"^(?P<prefix>.+)_static_init_(?P<run>\d+)\.csv$")
MEASURING_PATTERN = re.compile(r"^(?P<prefix>.+)_measuring_(?P<run>\d+)\.csv$")

##########################################################


def discover_run_files(directory: Union[Path, str]) -> DiscoveryResult:
    """Ищет пары файлов по шаблонам имен, принятым в GUI-приложении."""

    directory = Path(directory)
    static_files: dict[tuple[str, int], Path] = {}
    measuring_files: dict[tuple[str, int], Path] = {}

    for path in directory.glob("*.csv"):
        static_match = STATIC_PATTERN.match(path.name)
        if static_match:
            key = (static_match.group("prefix"), int(static_match.group("run")))
            static_files[key] = path
            continue

        measuring_match = MEASURING_PATTERN.match(path.name)
        if measuring_match:
            key = (measuring_match.group("prefix"), int(measuring_match.group("run")))
            measuring_files[key] = path

    runs: list[RunFiles] = []
    for key in sorted(static_files.keys() & measuring_files.keys(), key=lambda item: item[1]):
        _, run_number = key
        runs.append(
            RunFiles(
                static_path=static_files[key],
                measuring_path=measuring_files[key],
                run_number=run_number,
                expected_direction=expected_direction_from_run_number(run_number),
            )
        )

    unmatched_static = [static_files[key] for key in sorted(static_files.keys() - measuring_files.keys())]
    unmatched_measuring = [
        measuring_files[key] for key in sorted(measuring_files.keys() - static_files.keys())
    ]
    return DiscoveryResult(
        runs=runs,
        unmatched_static=unmatched_static,
        unmatched_measuring=unmatched_measuring,
    )


def expected_direction_from_run_number(run_number: int) -> RunDirection:
    """Возвращает ожидаемое направление проезда по его порядковому номеру."""

    if run_number <= 0:
        return RunDirection.UNKNOWN
    return RunDirection.FORWARD if run_number % 2 == 1 else RunDirection.BACKWARD
