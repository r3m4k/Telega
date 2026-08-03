"""Стадии пользовательского сценария главного окна."""

# System imports

# External imports

# User imports
from gui.program_stages.measuring_stage import MeasuringStage
from gui.program_stages.program_stage import MainWindowProtocol, ProgramStage
from gui.program_stages.ready_for_measurement_stage import ReadyForMeasurementStage
from gui.program_stages.ready_for_static_init_stage import ReadyForStaticInitStage
from gui.program_stages.setting_stage import SettingStage
from gui.program_stages.static_init_stage import StaticInitStage

##########################################################


__all__ = [
    'MainWindowProtocol',
    'MeasuringStage',
    'ProgramStage',
    'ReadyForMeasurementStage',
    'ReadyForStaticInitStage',
    'SettingStage',
    'StaticInitStage',
]
