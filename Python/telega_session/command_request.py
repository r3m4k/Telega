"""Модель команды межпроцессорного протокола GUI и сессии МК."""

# System imports
from typing import Any

# External imports
from pydantic import BaseModel, ConfigDict, Field

# User imports
from telega_session.command_name import CommandName

#############################################


class CommandRequest(BaseModel):
    """Команда, передаваемая из GUI в асинхронную сессию МК.

    Attributes:
        command: Идентификатор команды.
        params: Параметры команды. При отсутствии используются пустые параметры.
    """

    model_config = ConfigDict(extra='forbid')

    command: CommandName = Field(description='Идентификатор команды')
    params: dict[str, Any] = Field(
        default_factory=dict,
        description='Параметры команды',
    )
