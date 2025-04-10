from PyQt5.QtGui import QIcon
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QProgressBar, QPushButton, QFileDialog, QGridLayout, QMessageBox
from PyQt5.QtCore import QObject, pyqtSignal, QEvent

import json
from pprint import pprint, pformat
from random import random
from datetime import date
from time import sleep
from threading import Thread

from message import message
from com_port_gui import COM_Port_GUI
from printing import Printing


JSON_FILE = '../dev/history.json'


# Индексы для Buttons
Start_InitialSetting = 0
Start_Measuring = 1
Stop_Measuring = 2
Stop_ReadingData = 3

# Индексы осей
X = 0; Y = 1; Z = 2

# Индексы для Plot_Widget
Acc = 0; Gyro = 1

# Индексы для Values_Widget
Value_Acc = 2; Value_Gyro = 4

# Индексы для Setting_Widgets
List = 0; Help_Button = 1; UpdateButton = 2

# Индексы для SavingSetting_Widgets
Dir = 0; FileName = 1
LineEdit = 0


class DataCollectingWindow(QMainWindow):

    DataCollectingWindow_Closed = pyqtSignal()

    def __init__(self):
        super(QMainWindow, self).__init__(parent=None)
        self.ui = loadUi('../ui/DataCollecting.ui', self)
        self.setWindowTitle('Сбор данных')
        self.setWindowIcon(QIcon('../ui/Telega.ico'))

        self.printer = Printing()

        self.STM_ComPort = COM_Port_GUI(self.printer, "STM")
        self.GPS_ComPort = COM_Port_GUI(self.printer, "GPS")

        # Загрузим данные с прошлого использования
        with open(JSON_FILE, 'r') as json_file:
            self.json_data = json.load(json_file)

        # Настройка виджетов
        self.Command_Buttons = [self.ui.Buttons.itemAt(i).widget() for i in range(4)]
        self.Plots = [[self.ui.Plot_Widget.itemAtPosition(row, column).widget() for row in range(1, 4)] for column in range(2)]
        self.Sensor_Values = [[self.ui.Values_Widget.itemAtPosition(row, column).widget() for row in range(3)] for column in range(1, 4, 2)]
        self.Saving_Params = [[self.ui.SavingSettings_Widget.itemAtPosition(row, column).widget() for column in range(1, 3)] for row in range(2)]
        self.STM_Settings = [self.ui.COM_Port_STM_Settings.itemAt(i).widget() for i in range(1, 4)]
        self.GPS_Settings = [self.ui.COM_Port_GPS_Settings.itemAt(i).widget() for i in range(1, 4)]

        self.init_UI()

        self.printer.NewText_Signal.connect(lambda text: self.display(text))

    def init_UI(self):
        self.init_Buttons()
        self.init_Plots()
        self.init_Values()
        self.init_SavingSettings()
        self.init_STM_Settings()
        self.init_GPS_Settings()

    def closeEvent(self, event):
        self.DataCollectingWindow_Closed.emit()

        # Вызовем деструкторы COM портов для корректного завершения программы
        self.STM_ComPort.__del__()
        self.GPS_ComPort.__del__()

        # Сохраним данные текущего использования в json файл
        self.json_data["DataCollecting"]["dir"] = self.Saving_Params[Dir][LineEdit].text()      # Сохраним выбранный путь в json файл
        with open(JSON_FILE, 'w') as json_file:
            json.dump(self.json_data, json_file)

        event.accept()

    def display(self, text):
        """
        Выводит text в msgList ("терминал")
        """
        self.ui.msgList.addItem(text)

    ####### Функционал для self.Command_Buttons #######
    def init_Buttons(self):
        self.Command_Buttons[Start_InitialSetting].clicked.connect(self.start_InitialSetting)
        self.Command_Buttons[Start_Measuring].clicked.connect(self.start_Measuring)
        self.Command_Buttons[Stop_Measuring].clicked.connect(self.stop_Measuring)
        self.Command_Buttons[Stop_ReadingData].clicked.connect(self.stop_ReadingData)

    def start_InitialSetting(self):
        print('+++')

    def start_Measuring(self):
        self.STM_ComPort.startMeasuring(com_port_name=self.STM_Settings[List].currentText())

    def stop_Measuring(self):
        self.STM_ComPort.stopMeasuring()

    def stop_ReadingData(self):
        print('===')

    ####### Функционал для self.Plot_Widget #######
    def init_Plots(self):
        for data in [Acc, Gyro]:
            for axis in [X, Y, Z]:
                self.Plots[data][axis].setBackground("w")

    ####### Функционал для self.Sensor_Values #######
    def init_Values(self):
        pass

    def update_Values(self, data: dir):
        self.Sensor_Values[Acc][X].display(data['Acc_X']); self.Sensor_Values[Acc][Y].display(data['Acc_Y']); self.Sensor_Values[Acc][Z].display(data['Acc_Z'])
        self.Sensor_Values[Gyro][X].display(data['Gyro_X']); self.Sensor_Values[Gyro][Y].display(data['Gyro_Y']); self.Sensor_Values[Gyro][Z].display(data['Gyro_Z'])

    ####### Функционал для self.SavingSettings_Widget #######
    def init_SavingSettings(self):
        self.Saving_Params[Dir][LineEdit].setText(self.json_data["DataCollecting"]["dir"])
        self.Saving_Params[Dir][Help_Button].clicked.connect(self.set_SavingPath)

        self.Saving_Params[FileName][LineEdit].setText(f'telega_{str(date.today())}')
        self.Saving_Params[FileName][Help_Button].clicked.connect(lambda: message('Шаблонное название файлов - название, которое будет частью каждого файла, '
                                                                                  'созданного в результате выполнения программы.', icon='Information'))

    def set_SavingPath(self):
        path = QFileDialog().getExistingDirectory(self, 'Выберите путь сохранения', '/')
        if path != '':
            self.ui.Saving_Params[Dir][LineEdit].setText(path)

    ####### Функционал для self.STM_Settings #######
    def init_STM_Settings(self):
        com_ports = self.STM_ComPort.get_ComPorts()
        self.STM_Settings[List].addItems(com_ports)

        # Зададим значение по умолчанию, если в дескрипторе есть 'STM'
        for port in com_ports.keys():
            if 'STM' in com_ports[port]['desc']:
                self.STM_Settings[List].setCurrentIndex(list(com_ports.keys()).index(port))

        self.STM_Settings[Help_Button].clicked.connect(
            lambda: message(self.STM_ComPort.get_ComPorts()[f'{self.STM_Settings[List].currentText()}']["desc"],
                            icon='Information')
        )

        self.STM_Settings[UpdateButton].clicked.connect(self.update_STM_ComPorts)
        self.STM_Settings[UpdateButton].setIcon(QIcon('../ui/update.jpg'))

    def update_STM_ComPorts(self):
        com_ports = self.STM_ComPort.get_ComPorts()
        self.STM_Settings[List].clear()
        self.STM_Settings[List].addItems(com_ports)

    ####### Функционал для self.GPS_Settings #######
    def init_GPS_Settings(self):
        com_ports = self.GPS_ComPort.get_ComPorts()
        self.GPS_Settings[List].addItems(com_ports)

        # Зададим значение по умолчанию, если в дескрипторе есть 'GPS'
        for port in com_ports.keys():
            if 'GPS' in com_ports[port]['desc']:
                self.GPS_Settings[List].setCurrentIndex(list(com_ports.keys()).index(port))

        self.GPS_Settings[Help_Button].clicked.connect(
            lambda: message(self.GPS_ComPort.get_ComPorts()[f'{self.GPS_Settings[List].currentText()}']["desc"],
                            icon='Information')
        )

        self.GPS_Settings[UpdateButton].clicked.connect(self.update_GPS_ComPorts)
        self.GPS_Settings[UpdateButton].setIcon(QIcon('../ui/update.jpg'))

    def update_GPS_ComPorts(self):
        com_ports = self.STM_ComPort.get_ComPorts()
        self.GPS_Settings[List].clear()
        self.GPS_Settings[List].addItems(com_ports)