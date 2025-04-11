from PyQt5.QtCore import QObject, pyqtSignal
import logging
from pprint import pprint

class Printing(QObject):
    NewText_Signal = pyqtSignal(str)
    def __init__(self):
        super().__init__()

    def printing(self, text='', log_text=''):
        """
        Вывод текста в msgList GUI, в консоль и log файл.
        :param text: Текст для msgList и консоли.
        :param log_text: Текст для log файла.
        """
        if text != '':
            self.NewText_Signal.emit(text)
            pprint(text)

        if log_text != '':
            pass