"""Модель события межпроцессорного протокола сессии МК и GUI."""

# System imports
from typing import Any

# External imports
from pydantic import BaseModel, ConfigDict, Field

# User imports
from telega_session.session_event_name import SessionEventName

#############################################


class SessionEvent(BaseModel):
    """Событие, передаваемое из асинхронной сессии МК в GUI.

    Attributes:
        event: Идентификатор события.
        params: Параметры события. При отсутствии используются пустые параметры.
    """

    model_config = ConfigDict(extra='forbid')

    event: SessionEventName = Field(description='Идентификатор события')
    params: dict[str, Any] = Field(
        default_factory=dict,
        description='Параметры события',
    )
