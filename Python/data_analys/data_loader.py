"""Загрузка CSV-файлов и подготовка табличных данных к обработке."""

# System imports
from pathlib import Path
from typing import Iterable, Union

# External imports
import numpy as np
import pandas as pd

# User imports
from .math_tools import Vector
from .models import ProcessingConfig, RunData

##########################################################


RAW_COLUMNS = [
    "PackageNum",
    "DppCode",
    "AccX",
    "AccY",
    "AccZ",
    "GyroX",
    "GyroY",
    "GyroZ",
]

ACC_COLUMNS = ["AccX", "AccY", "AccZ"]
GYRO_DEG_COLUMNS = ["GyroX", "GyroY", "GyroZ"]
GYRO_RAD_COLUMNS = ["GyroRadX", "GyroRadY", "GyroRadZ"]

##########################################################


def load_run_csv(path: Union[Path, str], config: ProcessingConfig) -> RunData:
    """Читает CSV-файл, проверяет поля и добавляет расчетные колонки."""

    path = Path(path)
    df = pd.read_csv(path, sep=config.csv_separator, engine="python")
    _validate_columns(df, RAW_COLUMNS, path)
    df = _normalize_numeric_columns(df, RAW_COLUMNS, path)
    df["Time"] = (df["PackageNum"] - df["PackageNum"].iloc[0]) * config.period
    df[GYRO_RAD_COLUMNS] = np.deg2rad(df[GYRO_DEG_COLUMNS].to_numpy(dtype=float))
    return RunData(dataframe=df, source_path=path, period=config.period)


def vectors_from_columns(df: pd.DataFrame, columns: Iterable[str]) -> list[Vector]:
    """Преобразует три колонки DataFrame в список объектов Vector."""

    values = df[list(columns)].to_numpy(dtype=float)
    return [Vector(row) for row in values]


def vectors_to_array(vectors: Iterable[Vector]) -> np.ndarray:
    """Преобразует список Vector в двумерный numpy-массив."""

    return np.array([vector.to_list() for vector in vectors], dtype=float)


def array_to_vectors(values: np.ndarray) -> list[Vector]:
    """Преобразует двумерный numpy-массив в список Vector."""

    return [Vector(row) for row in np.asarray(values, dtype=float)]


def add_vector_columns(
    df: pd.DataFrame,
    prefix: str,
    vectors: Iterable[Vector],
    axes: tuple[str, str, str] = ("E", "N", "U"),
) -> None:
    """Добавляет в DataFrame три колонки, соответствующие компонентам вектора."""

    values = vectors_to_array(vectors)
    for index, axis in enumerate(axes):
        df[f"{prefix}{axis}"] = values[:, index]

##########################################################


def _validate_columns(df: pd.DataFrame, required_columns: list[str], path: Path) -> None:
    """Проверяет наличие обязательных колонок в CSV-файле."""

    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing required columns: {', '.join(missing)}")


def _normalize_numeric_columns(
    df: pd.DataFrame,
    columns: list[str],
    path: Path,
) -> pd.DataFrame:
    """Приводит обязательные колонки к числовому типу."""

    result = df.copy()
    for column in columns:
        result[column] = pd.to_numeric(result[column], errors="raise")
    if result.empty:
        raise ValueError(f"{path} does not contain measurement rows")
    return result
