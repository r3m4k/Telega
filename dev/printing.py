from PyQt5.QtCore import QObject, pyqtSignal

class Printing(QObject):
    NewText_Signal = pyqtSignal(str)
    def __init__(self):
        super().__init__()

    def printing(self, text):
        self.NewText_Signal.emit(text)
        print(text)