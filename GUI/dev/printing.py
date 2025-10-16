from PyQt5.QtCore import QObject, pyqtSignal
import logging


class Printing(QObject):
    NewText_Signal = pyqtSignal(str)
    def __init__(self, logFilePath=''):
        super().__init__()
        self.logFilePath = logFilePath
        self.logger = logging.getLogger('telega_soft')

    def set_logger(self, logFilePath):
        self.logFilePath = logFilePath
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        file_handler = logging.FileHandler(self.logFilePath, mode='w', encoding='UTF-8')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def printing(self, text='', log_text='', log_level=''):
        """
        Вывод текста в msgList GUI, в консоль и log файл.
        :param text: Текст для msgList и консоли.
        :param log_text: Текст для log файла.
        :param log_level: Уровень логирования.
        """
        if text != '':
            self.NewText_Signal.emit(text)
            # pprint(text)

        if log_text == '':
            return

        match log_level:
            case 'Debug':
                self.logger.debug(log_text)
            case 'Info':
                self.logger.info(log_text)
            case 'Warning':
                self.logger.warning(log_text)
            case 'Error':
                self.logger.error(log_text)
            case 'Critical':
                self.logger.critical(log_text)
            case _:
                pass