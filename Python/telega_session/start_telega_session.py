# -*- coding: utf-8 -*-
"""Асинхронная сессия для работы с МК путеизмерительной тележки.

Запускается в отдельном процессе, общается с родителем через multiprocessing.Queue.
"""

# System imports
import asyncio
import logging
from multiprocessing import Queue
from pathlib import Path
from typing import Optional

# External imports

# User imports
from async_mc_controller.config import McConfig, ComPortConfig, LoggerConfig
from async_mc_controller.logger import McLogger
from async_mc_controller.signal_bus import McBus
from async_mc_controller.async_mc_session import McSession
from telega_session import ComPortTelega, DecoderTelega, ControllerTelega
from telega_session.controller_telega import TelegaStatusCode, TelegaStatusCodeMessages
from telega_session.session_event import SessionEvent
from telega_session.session_event_name import SessionEventName

#########################

async def _run_telega_session(logger_config: LoggerConfig,
                              com_port_config: ComPortConfig,
                              bin_file: Path,
                              command_queue: Queue,
                              response_queue: Queue,
                              data_queue: Queue) -> None:

    """Запуск асинхронной сессии управления путеизмерительной тележкой.

    Args:
       logger_config:   Конфигурация логирования.
       com_port_config: Конфигурация COM-порта (имя, скорость).
       bin_file:        Файл исходного байтового потока для декодера.
       command_queue:   Очередь для получения команд от родителя.
       response_queue:  Очередь для отправки SessionEvent родителю.
       data_queue:      Очередь для отправки пакетов TelegaData.
    """

    # Настроим конфигурацию
    mc_config = McConfig()
    mc_config.logger_config = logger_config
    mc_config.com_port = com_port_config
    mc_config.logger_config.log_level = logging.DEBUG
    mc_config.logger_config.log_filename = 'telega_mc_logger.log'
    mc_config.logger_config.use_console = False

    mc_logger: Optional[McLogger] = None
    decoder: Optional[DecoderTelega] = None
    controller: Optional[ControllerTelega] = None
    session_started = False
    status_messages = TelegaStatusCodeMessages()
    try:
        # Создадим необходимые экземпляры
        mc_logger = McLogger(mc_config)
        bus = McBus(mc_logger)

        com_port = ComPortTelega(
            mc_config.com_port.name,
            mc_config.com_port.baudrate,
            bus,
            mc_logger,
        )

        decoder = DecoderTelega(bus, mc_logger)
        decoder.setup_bin_file(bin_file)

        controller = ControllerTelega(
            bus,
            mc_logger,
            command_queue,
            response_queue,
            data_queue,
        )

        # Порядок входа и выхода компонентов важен, поэтому сессия всегда
        # запускается через единый контекстный менеджер McSession.
        async with McSession(decoder, com_port, controller):
            session_started = True
            await controller.running()

    except Exception as err:
        if mc_logger is not None:
            mc_logger.error(f'Не удалось запустить или выполнить сессию МК: {err}')
        status_code = (
            TelegaStatusCode.UNKNOWN_ERROR
            if session_started
            else TelegaStatusCode.CONNECTION_FAILED
        )
        error_info = f'{status_messages[status_code]}: {err}'
        session_event = SessionEvent(
            event=SessionEventName.SESSION_ERROR,
            params={
                'error_code': status_code.name,
                'error_info': error_info,
            },
        )
        await asyncio.to_thread(response_queue.put, session_event.model_dump())

    finally:
        if mc_logger is not None and decoder is not None:
            mc_logger.debug(str(decoder))

    # Задержка для завершения всех фоновых операций
    await asyncio.sleep(1)
    await asyncio.to_thread(
        response_queue.put,
        SessionEvent(event=SessionEventName.SESSION_STOPPED).model_dump(),
    )

# =============================================================

def start_telega_session(logger_config: LoggerConfig,
                         com_port_config: ComPortConfig,
                         bin_file: Path,
                         command_queue: Queue,
                         response_queue: Queue,
                         data_queue: Queue) -> None:
    """Функция, запускаемая в отдельном процессе
    (точка входа для мультипроцессорной реализации)."""

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_telega_session(logger_config, com_port_config, bin_file,
                                                    command_queue, response_queue, data_queue))
    except Exception as err:
        status_messages = TelegaStatusCodeMessages()
        response_queue.put(
            SessionEvent(
                event=SessionEventName.SESSION_ERROR,
                params={
                    'error_code': TelegaStatusCode.UNKNOWN_ERROR.name,
                    'error_info': (
                        f'{status_messages[TelegaStatusCode.UNKNOWN_ERROR]}: {err}'
                    ),
                },
            ).model_dump()
        )
        response_queue.put(
            SessionEvent(event=SessionEventName.SESSION_STOPPED).model_dump()
        )
    finally:
        # Отменяем все незавершённые задачи
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()

# =============================================================
