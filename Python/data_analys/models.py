"""Модели данных и конфигурации для постобработки измерительных проездов."""

# System imports
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

# External imports
import pandas as pd

# User imports
from .math_tools import Quaternion, Vector

##########################################################


class RunDirection(Enum):
    """Фактическое направление движения тележки по данным ДПП."""

    FORWARD = "forward"
    BACKWARD = "backward"
    UNKNOWN = "unknown"


class DppDownsampleMode(Enum):
    """Режимы прореживания общей таблицы по кодам ДПП."""

    TAKE_EVERY_N = "take_every_n"
    MEAN_BY_BIN = "mean_by_bin"

##########################################################


@dataclass
class TemperatureCompensationConfig:
    """Параметры будущей температурной компенсации смещения нуля."""

    enabled: bool = False
    temperature_column: Optional[str] = None
    coefficients: Optional[dict[str, tuple[float, float]]] = None


@dataclass
class FilterConfig:
    """Параметры будущей offline-фильтрации входных измерений."""

    enabled: bool = False


@dataclass
class ProcessingConfig:
    """Общая конфигурация алгоритма постобработки."""

    period: float  # seconds
    latitude_deg: float
    output_dir: Path = Path("data_processing_results")
    csv_separator: str = r"\s+"
    output_csv_separator: str = " "
    gravity_acceleration: float = 9.80665  # m/s**2
    p_end: Vector = field(default_factory=lambda: Vector([0.0, 0.0, 0.0]))
    save_results: bool = True
    dpp_downsample_step: Optional[int] = None
    dpp_downsample_mode: DppDownsampleMode = DppDownsampleMode.TAKE_EVERY_N
    temperature_compensation: TemperatureCompensationConfig = field(
        default_factory=TemperatureCompensationConfig
    )
    filter_config: FilterConfig = field(default_factory=FilterConfig)

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir)
        if self.period <= 0:
            raise ValueError("period must be positive")
        if self.gravity_acceleration <= 0:
            raise ValueError("gravity_acceleration must be positive")

##########################################################


@dataclass
class RunFiles:
    """Пара файлов, относящихся к одному измерительному проезду."""

    static_path: Path
    measuring_path: Path
    run_number: Optional[int] = None
    expected_direction: Optional[RunDirection] = None

    def __post_init__(self) -> None:
        self.static_path = Path(self.static_path)
        self.measuring_path = Path(self.measuring_path)


@dataclass
class DiscoveryResult:
    """Результат автоматической разметки файлов проездов."""

    runs: list[RunFiles]
    unmatched_static: list[Path] = field(default_factory=list)
    unmatched_measuring: list[Path] = field(default_factory=list)


@dataclass
class RunData:
    """Загруженные табличные данные одного CSV-файла."""

    dataframe: pd.DataFrame
    source_path: Path
    period: float

    @property
    def time(self):
        return self.dataframe["Time"].to_numpy(dtype=float)

##########################################################


@dataclass
class InitializationResult:
    """Результаты начальной выставки по статическому буферу."""

    q_body_to_nav: Quaternion
    bias_acc: Vector
    bias_gyro: Vector
    omega_earth_nav: Vector
    gravity_nav: Vector


@dataclass
class ProcessingResult:
    """Результат обработки одного измерительного проезда."""

    run_files: RunFiles
    direction: RunDirection
    detailed_dataframe: pd.DataFrame
    dpp_dataframe: pd.DataFrame
    initialization: InitializationResult
    detailed_output_path: Optional[Path] = None
    dpp_output_path: Optional[Path] = None


@dataclass
class SessionProcessingResult:
    """Результат обработки и сведения нескольких измерительных проездов."""

    run_results: list[ProcessingResult]
    common_dpp_dataframe: pd.DataFrame
    downsampled_dpp_dataframe: Optional[pd.DataFrame] = None
    common_output_path: Optional[Path] = None
    downsampled_output_path: Optional[Path] = None
