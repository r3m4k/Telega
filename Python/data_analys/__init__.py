"""Пакет постобработки измерительных проездов Telega."""

# User imports
from .data_loader import load_run_csv
from .dpp_axis import (
    aggregate_by_dpp,
    build_common_dpp_table,
    detect_direction_from_dpp,
    downsample_common_dpp_table,
)
from .file_discovery import discover_run_files
from .initialization import initialize_from_static_buffer
from .inertial import process_inertial_data
from .models import (
    DppDownsampleMode,
    FilterConfig,
    ProcessingConfig,
    ProcessingResult,
    RunDirection,
    RunFiles,
    SessionProcessingResult,
    TemperatureCompensationConfig,
)
from .pipeline import discover_and_process_session, process_run, process_session
from .trajectory import compute_trajectory

##########################################################

__all__ = [
    "DppDownsampleMode",
    "FilterConfig",
    "ProcessingConfig",
    "ProcessingResult",
    "RunDirection",
    "RunFiles",
    "SessionProcessingResult",
    "TemperatureCompensationConfig",
    "aggregate_by_dpp",
    "build_common_dpp_table",
    "compute_trajectory",
    "detect_direction_from_dpp",
    "discover_and_process_session",
    "discover_run_files",
    "downsample_common_dpp_table",
    "initialize_from_static_buffer",
    "load_run_csv",
    "process_inertial_data",
    "process_run",
    "process_session",
]
