# System imports
import sys
from multiprocessing import freeze_support

# External imports
from PyQt5.QtWidgets import QApplication

# User imports
from gui.main_window import MainWindow

##########################################################

def main() -> int:
    """Запуск GUI-приложения."""
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    return app.exec_()

# =============================================================

if __name__ == '__main__':
    freeze_support()
    sys.exit(main())
