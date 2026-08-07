# System imports
import asyncio
import sys
from multiprocessing import freeze_support
from typing import Optional

# External imports
from PyQt5.QtWidgets import QApplication
from qasync import QEventLoop

# User imports
from gui.main_window import MainWindow

##########################################################


def main() -> int:
    """Запускает GUI в общем event loop Qt и asyncio."""
    app = QApplication(sys.argv)
    event_loop = QEventLoop(app)
    asyncio.set_event_loop(event_loop)

    # Сильная ссылка хранит окно до завершения event loop.
    main_window: Optional[MainWindow] = None

    def create_main_window() -> None:
        """Создаёт окно после фактического запуска event loop."""
        nonlocal main_window

        main_window = MainWindow()
        main_window.show()

    # Callback выполнится в первой итерации уже работающего event loop.
    event_loop.call_soon(create_main_window)

    with event_loop:
        event_loop.run_forever()

    return 0

# =============================================================

if __name__ == '__main__':
    freeze_support()
    sys.exit(main())
