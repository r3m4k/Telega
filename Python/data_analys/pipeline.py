"""Высокоуровневый pipeline постобработки одного проезда и сессии."""

# System imports
from pathlib import Path
from typing import Optional, Union

# External imports
import pandas as pd

# User imports
from .data_loader import (
    ACC_COLUMNS,
    GYRO_RAD_COLUMNS,
    add_vector_columns,
    load_run_csv,
    vectors_from_columns,
)
from .dpp_axis import (
    build_common_dpp_table,
    detect_direction_from_dpp,
    downsample_common_dpp_table,
    aggregate_by_dpp,
)
from .file_discovery import discover_run_files
from .initialization import initialize_from_static_buffer
from .inertial import process_inertial_data
from .models import (
    DiscoveryResult,
    ProcessingConfig,
    ProcessingResult,
    RunFiles,
    SessionProcessingResult,
)
from .sensor_correction import apply_sensor_corrections
from .trajectory import compute_trajectory

##########################################################

# TODO(data_analys):
# 1. Реализовать температурную компенсацию и offline-фильтрацию либо временно
#    запрещать включение соответствующих флагов в пользовательском интерфейсе.
# 2. Проверить устойчивость начальной выставки по проекции вращения Земли на
#    реальных данных L3GD20; этот шаг чувствителен к bias гироскопа.
# 3. При необходимости сверять expected_direction из номера проезда с
#    фактическим направлением, найденным по DppCode.
# 4. Для ненулевых p_end и обратных проездов привести PositionENU к единой
#    системе отсчета участка перед сравнением нескольких проездов.

##########################################################


def process_run(run_files: RunFiles, config: ProcessingConfig) -> ProcessingResult:
    """Обрабатывает один проезд: static buffer + measurement CSV."""

    static_data = load_run_csv(run_files.static_path, config)
    measuring_data = load_run_csv(run_files.measuring_path, config)
    static_data, measuring_data = apply_sensor_corrections(static_data, measuring_data, config)

    initialization = initialize_from_static_buffer(
        acc_buffer=vectors_from_columns(static_data.dataframe, ACC_COLUMNS),
        gyro_buffer_rad_s=vectors_from_columns(static_data.dataframe, GYRO_RAD_COLUMNS),
        config=config,
    )

    time = measuring_data.time
    inertial_output = process_inertial_data(
        time=time,
        acc_data=vectors_from_columns(measuring_data.dataframe, ACC_COLUMNS),
        gyro_data_rad_s=vectors_from_columns(measuring_data.dataframe, GYRO_RAD_COLUMNS),
        initialization=initialization,
    )
    velocity, position = compute_trajectory(
        time=time,
        acceleration_nav=inertial_output.acceleration_nav,
        p_end=config.p_end,
    )

    detailed_df = measuring_data.dataframe.copy()
    _add_quaternion_columns(detailed_df, inertial_output.quaternions)
    add_vector_columns(detailed_df, "AccNav", inertial_output.acceleration_nav)
    add_vector_columns(detailed_df, "Velocity", velocity)
    add_vector_columns(detailed_df, "Position", position)

    direction = detect_direction_from_dpp(detailed_df)
    detailed_df["Direction"] = direction.value
    dpp_df = aggregate_by_dpp(detailed_df)

    result = ProcessingResult(
        run_files=run_files,
        direction=direction,
        detailed_dataframe=detailed_df,
        dpp_dataframe=dpp_df,
        initialization=initialization,
    )
    if config.save_results:
        _save_run_result(result, config)
    return result


def process_session(
    runs: list[RunFiles],
    config: ProcessingConfig,
) -> SessionProcessingResult:
    """Последовательно обрабатывает набор проездов и сводит их по DppCode."""

    run_results = [process_run(run_files, config) for run_files in runs]
    common_df = build_common_dpp_table(run_results)

    downsampled_df: Optional[pd.DataFrame] = None
    if config.dpp_downsample_step is not None:
        downsampled_df = downsample_common_dpp_table(
            common_df,
            step=config.dpp_downsample_step,
            mode=config.dpp_downsample_mode,
        )

    result = SessionProcessingResult(
        run_results=run_results,
        common_dpp_dataframe=common_df,
        downsampled_dpp_dataframe=downsampled_df,
    )
    if config.save_results:
        _save_session_result(result, config)
    return result


def discover_and_process_session(
    directory: Union[Path, str],
    config: ProcessingConfig,
) -> tuple[DiscoveryResult, SessionProcessingResult]:
    """Автоматически размечает файлы в папке и запускает обработку сессии."""

    discovery = discover_run_files(directory)
    return discovery, process_session(discovery.runs, config)


##########################################################


def _add_quaternion_columns(df: pd.DataFrame, quaternions) -> None:
    """Добавляет компоненты кватерниона в подробную таблицу результата."""

    df["Qw"] = [quaternion.w for quaternion in quaternions]
    df["Qx"] = [quaternion.x for quaternion in quaternions]
    df["Qy"] = [quaternion.y for quaternion in quaternions]
    df["Qz"] = [quaternion.z for quaternion in quaternions]


def _save_run_result(result: ProcessingResult, config: ProcessingConfig) -> None:
    """Сохраняет подробный и DPP-агрегированный результаты одного проезда."""

    output_dir = _run_output_dir(result, config)
    output_dir.mkdir(parents=True, exist_ok=True)
    label = _run_label(result.run_files)

    detailed_path = output_dir / f"{label}_detailed_result.csv"
    dpp_path = output_dir / f"{label}_dpp_result.csv"

    result.detailed_dataframe.to_csv(
        detailed_path,
        sep=config.output_csv_separator,
        index=False,
    )
    result.dpp_dataframe.to_csv(
        dpp_path,
        sep=config.output_csv_separator,
        index=False,
    )
    result.detailed_output_path = detailed_path
    result.dpp_output_path = dpp_path


def _save_session_result(result: SessionProcessingResult, config: ProcessingConfig) -> None:
    """Сохраняет общие таблицы сведения нескольких проездов."""

    config.output_dir.mkdir(parents=True, exist_ok=True)

    common_path = config.output_dir / "session_common_by_dpp.csv"
    result.common_dpp_dataframe.to_csv(
        common_path,
        sep=config.output_csv_separator,
        index=False,
    )
    result.common_output_path = common_path

    if result.downsampled_dpp_dataframe is not None:
        downsampled_path = config.output_dir / "session_common_by_dpp_downsampled.csv"
        result.downsampled_dpp_dataframe.to_csv(
            downsampled_path,
            sep=config.output_csv_separator,
            index=False,
        )
        result.downsampled_output_path = downsampled_path


def _run_output_dir(result: ProcessingResult, config: ProcessingConfig) -> Path:
    """Возвращает папку сохранения результатов одного проезда."""

    return config.output_dir / _run_label(result.run_files)


def _run_label(run_files: RunFiles) -> str:
    """Формирует имя проезда для папок и файлов результатов."""

    if run_files.run_number is not None:
        return f"run_{run_files.run_number}"
    return run_files.measuring_path.stem
