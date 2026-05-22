"""Зарезервированный слой коррекции входных сигналов датчиков."""

# User imports
from .models import ProcessingConfig, RunData

##########################################################


def apply_sensor_corrections(
    static_data: RunData,
    measuring_data: RunData,
    config: ProcessingConfig,
) -> tuple[RunData, RunData]:
    """Применяет опциональные коррекции к статике и данным проезда."""

    if config.temperature_compensation.enabled:
        static_data = _apply_temperature_compensation(static_data, config)
        measuring_data = _apply_temperature_compensation(measuring_data, config)

    if config.filter_config.enabled:
        static_data = _apply_filtering(static_data, config)
        measuring_data = _apply_filtering(measuring_data, config)

    return static_data, measuring_data


##########################################################


def _apply_temperature_compensation(
    run_data: RunData,
    config: ProcessingConfig,
) -> RunData:
    # Reserved for the temperature-drift model already developed separately.
    return run_data


def _apply_filtering(
    run_data: RunData,
    config: ProcessingConfig,
) -> RunData:
    # Filtering is part of the pipeline contract, but its exact strategy will be
    # chosen after the first inertial-processing implementation is in place.
    return run_data
