from sys import argv, exit
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.uic import loadUi
from PyQt5.QtGui import QIcon

from data_collecting_ui import DataCollectingWindow
from data_processing_ui import DataProcessingWindow
from message import message


class MainWindow(QMainWindow):

    WindowsCounter = [0, 0]

    def __init__(self):
        super(QMainWindow, self).__init__(parent=None)
        self.ui = loadUi('../ui/MainWindow.ui', self)
        self.setWindowTitle("TelegaSoft")
        self.setWindowIcon(QIcon('../ui/Telega.ico'))

        self.init_UI()

        self.data_collecting_window = DataCollectingWindow()
        self.data_processing_window = DataProcessingWindow()

        self.data_collecting_window.DataCollectingWindow_Closed.connect(self.close_DataCollectingWindow)
        self.data_processing_window.DataProcessingWindow_Closed.connect(self.close_DataProcessingWindow)

    def init_UI(self):
        self.ui.DataCollecting_Button.clicked.connect(self.new_DataCollectingWindow)
        self.ui.DataProcessing_Button.clicked.connect(self.new_DataProcessingWindow)
    
    def new_DataCollectingWindow(self):
        if not self.WindowsCounter[0]:
            self.data_collecting_window.show()
            self.WindowsCounter[0] += 1
        else:
            message('Закройте предыдущее окно', icon=QMessageBox.Warning)

    def close_DataCollectingWindow(self):
        self.WindowsCounter[0] -= 1
    
    def new_DataProcessingWindow(self):
        if not self.WindowsCounter[1]:
            self.data_processing_window.show()
            self.WindowsCounter[1] += 1
        else:
            message('Закройте предыдущее окно', icon=QMessageBox.Warning)

    def close_DataProcessingWindow(self):
        self.WindowsCounter[1] -= 1

    def closeEvent(self, event):
        QApplication.closeAllWindows()
        event.accept()

if __name__ == "__main__":
    app = QApplication(argv)
    window = MainWindow()
    window.show()
    exit(app.exec_())
