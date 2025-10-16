from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QProgressBar, QPushButton, QFileDialog
from PyQt5.uic import loadUi
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QObject, pyqtSignal



class DataProcessingWindow(QMainWindow):
    DataProcessingWindow_Closed = pyqtSignal()

    def __init__(self):
        super(QMainWindow, self).__init__(parent=None)

    def closeEvent(self, event):
        self.DataProcessingWindow_Closed.emit()
        event.accept()