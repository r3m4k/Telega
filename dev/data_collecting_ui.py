import numpy as np
from PyQt5.QtGui import QIcon
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QProgressBar, QPushButton, QFileDialog, QGridLayout, QMessageBox
from PyQt5.QtCore import QObject, pyqtSignal, QEvent, Qt
from PyQt5 import QtCore
import pyqtgraph as pg

import json
from pprint import pprint, pformat
from random import random
from datetime import date
from time import sleep
from threading import Thread

from consts import CWD
from message import message
from com_port import COM_Port_GUI, get_ComPorts, STM_ComPort, GPS_ComPort
from printing import Printing


JSON_FILE = f'{CWD}/dev/history.json'


# Индексы для Buttons
Start_InitialSetting = 0
Start_Measuring = 1
Stop_Measuring = 2
Get_Coordinates = 3

# Индексы осей
X = 0; Y = 1; Z = 2

# Индексы для Plot_Widget
Acc = 0; Gyro = 1

# Индексы для Values_Widget
Value_Acc = 2; Value_Gyro = 4

# Индексы для Setting_Widgets (COM_Port settings)
List = 0; Help_Button = 1; UpdateButton = 2

# Индексы для SavingSetting_Widgets
Dir = 0; FileName = 1
LineEdit = 0

# # Параметры для графиков
# titles = ["Acc_X", "Acc_Y", "Acc_Z", "Gyro_X", "Gyro_Y", "Gyro_Z"]
# colors = [["#1F77B4", "#D62728", "#2CA02C"],
#           ["#17BECF", "#FF7F0E", "#9467BD"]]
# y_labels = [["Acc_X, m/s**2", "Acc_Y, m/s**2", "Acc_Z, m/s**2"],
#             ["Gyro_X, mdps", "Gyro_Y, mdps", "Gyro_Z, mdps"]]
# MAX_X_LENGTH = 32       # Максимальное количество точек на графиках
# PERIOD = 0.25           # Период получения данных с платы STM


class DataCollectingWindow(QMainWindow):

    DataCollectingWindow_Closed = pyqtSignal()

    def __init__(self):
        super(QMainWindow, self).__init__(parent=None)
        self.ui = loadUi(f'{CWD}/ui/DataCollecting.ui', self)
        self.setWindowTitle('Сбор данных')
        self.setWindowIcon(QIcon(f'{CWD}/ui/Telega.ico'))

        self.PassageNum = 1                   # Номер проезда
        self.UsingGps_Flag: bool = True       # Флаг использования GPS модуля
        self.LoggerReady: bool = False        # Флаг законченной настройки логгера в self.printer
        self.CoordinatesAreCollected = False

        # Загрузим данные с прошлого использования
        with open(JSON_FILE, 'r') as json_file:
            self.json_data = json.load(json_file)

        # Настройка виджетов
        self.Command_Buttons = [self.ui.Buttons.itemAt(i).widget() for i in range(4)]
        # self.Plots = [[self.ui.Plot_Widget.itemAtPosition(row, column).widget() for row in range(1, 4)] for column in range(2)]
        self.Sensor_Values = [[self.ui.Values_Widget.itemAtPosition(row, column).widget() for row in range(3)] for column in range(1, 4, 2)]
        self.Saving_Params = [[self.ui.SavingSettings_Widget.itemAtPosition(row, column).widget() for column in range(1, 3)] for row in range(2)]
        self.STM_Settings = [self.ui.COM_Port_STM_Settings.itemAt(i).widget() for i in range(1, 4)]
        self.GPS_Settings = [self.ui.COM_Port_GPS_Settings.itemAt(i).widget() for i in range(1, 4)]
        self.Latitude_Value = self.ui.Latitude_Value
        self.Longitude_Value = self.ui.Longitude_Value
        self.PassageNum_Widget = self.ui.Passage_Num
        self.GPS_CheckBox = self.ui.GPScheckBox
        #-------------------
        self.PassageNum_Widget.setText(f'№ {self.PassageNum}')
        self.GPS_CheckBox.setChecked(True)
        #-------------------

        # Настройка графиков
        # self.pens = [[pg.mkPen(colors[data][axis], width=2) for axis in [X, Y, Z]] for data in [Acc, Gyro]]
        # self.lines = [[self.Plots[data][axis].plot() for axis in [X, Y, Z]] for data in [Acc, Gyro]]
        # self.x_index = 0
        # self.x_array = np.arange(0, MAX_X_LENGTH * PERIOD, PERIOD)
        # self.plot_values = {"Acc_X": np.zeros_like(self.x_array), "Acc_Y": np.zeros_like(self.x_array), "Acc_Z": np.zeros_like(self.x_array),
        #                     "Gyro_X": np.zeros_like(self.x_array), "Gyro_Y": np.zeros_like(self.x_array), "Gyro_Z": np.zeros_like(self.x_array)}

        # Создадим нужные экземпляры классов
        self.printer = Printing()
        self.STM_ComPort = STM_ComPort(self.printer)
        self.GPS_ComPort = GPS_ComPort(self.printer)

        self.init_UI()

        # Подключим сигналы
        self.printer.NewText_Signal.connect(lambda text: self.display(text))

        self.STM_ComPort.NewData_Signal.connect(lambda values: self.update_Data(values))
        self.GPS_ComPort.NewData_Signal.connect(lambda values: self.update_Data(values))

        self.STM_ComPort.Error_ComPort.connect(lambda error: self.error_handler(error))
        self.GPS_ComPort.Error_ComPort.connect(lambda error: self.error_handler(error))

        self.STM_ComPort.EndOfInitialSettings.connect(self.end_of_initialSetting)
        self.GPS_ComPort.EndOfCollectingCoordinates.connect(self.end_of_getting_coordinates)

    def init_UI(self):
        self.init_Buttons()
        # self.init_Plots()
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

    def update_logger(self):
        if not self.LoggerReady:
            self.printer.set_logger(f'{self.Saving_Params[Dir][LineEdit].text()}/{self.Saving_Params[FileName][LineEdit].text()}_logger.log')
            self.LoggerReady = True

    def display(self, text):
        """
        Выводит text в msgList ("терминал")
        """
        self.ui.msgList.addItem(text)

    def update_Data(self, data: dir):
        match data["type_port"]:
            case "STM":
                self.update_STMData(data["values"])
            case "GPS":
                self.update_GPSData(data["values"])
            case _:
                pass

    def update_STMData(self, values: dir):
        # self.update_Plots(values)
        self.update_Values(values)

    def update_GPSData(self, values: dir):
        self.Latitude_Value.display(values['Latitude'])
        self.Longitude_Value.display(values['Longitude'])

    def blockInputs(self):
        """
        Блокировка виджетов, предназначенных для ввода информации от пользователя для корректной работы программы
        """
        # Заблокируем кнопки управления
        self.Command_Buttons[Start_InitialSetting].setEnabled(False)
        self.Command_Buttons[Start_Measuring].setEnabled(False)
        self.Command_Buttons[Get_Coordinates].setEnabled(False)

        # Заблокируем параметры сохранения
        self.Saving_Params[Dir][LineEdit].setReadOnly(True)
        self.Saving_Params[Dir][Help_Button].setEnabled(False)

        self.Saving_Params[FileName][LineEdit].setReadOnly(True)

        # Заблокируем параметры COM портов
        self.STM_Settings[List].setEnabled(False)
        self.STM_Settings[UpdateButton].setEnabled(False)

        self.GPS_Settings[List].setEnabled(False)
        self.GPS_Settings[UpdateButton].setEnabled(False)

        self.GPS_CheckBox.setEnabled(False)

    def unblockInputs(self):
        """
        Разблокировка виджетов, предназначенных для ввода информации от пользователя
        """
        # Разблокируем кнопки управления
        # self.Command_Buttons[Start_InitialSetting].setEnabled(True)
        self.Command_Buttons[Start_Measuring].setEnabled(True)
        self.Command_Buttons[Get_Coordinates].setEnabled(True)

        # Разблокируем параметры сохранения
        self.Saving_Params[Dir][LineEdit].setReadOnly(False)
        self.Saving_Params[Dir][Help_Button].setEnabled(True)

        self.Saving_Params[FileName][LineEdit].setReadOnly(False)

        # Разблокируем параметры COM портов
        self.STM_Settings[List].setEnabled(True)
        self.STM_Settings[UpdateButton].setEnabled(True)

        self.GPS_Settings[List].setEnabled(True)
        self.GPS_Settings[UpdateButton].setEnabled(True)

        self.GPS_CheckBox.setEnabled(True)

    def error_handler(self, error: dir):
        match error["type_port"]:
            case "STM":
                self.STM_ComPort.stopMeasuring()
                self.unblockInputs()
                message(text=error["message"], icon='Critical')
            case "GPS":
                self.unblockInputs()
                message(text=error["message"], icon='Critical')

    ####### Функционал для self.Command_Buttons #######
    def init_Buttons(self):
        self.Command_Buttons[Start_InitialSetting].clicked.connect(self.start_InitialSetting)
        self.Command_Buttons[Start_Measuring].clicked.connect(self.start_Measuring)
        self.Command_Buttons[Stop_Measuring].clicked.connect(self.stop_Measuring)
        self.Command_Buttons[Get_Coordinates].clicked.connect(self.get_Coordinates)

        self.Command_Buttons[Stop_Measuring].setEnabled(False)

    def start_InitialSetting(self):
        self.update_logger()

        # Сбросим накопленные данные
        # self.x_index = 0    # Индекс полученного пакета данных

        # Запуск чтения данных с платы STM
        if self.STM_Settings[List].currentText() == '-----':
            message('Выберите корректный COM порт для STM', icon='Warning')
            return

        self.blockInputs()

        self.Command_Buttons[Stop_Measuring].setEnabled(True)
        self.Command_Buttons[Start_Measuring].setEnabled(False)

        self.STM_ComPort.startInitialSettings(
            com_port_name=self.STM_Settings[List].currentText(),
            saving_path=self.Saving_Params[Dir][LineEdit].text(),
            template_name=self.Saving_Params[FileName][LineEdit].text(),
        )

    # Такой кнопки нет, но всё равно разместим эту функцию в этой части кода

    def start_Measuring(self):
        self.update_logger()
        self.PassageNum_Widget.setText(f'№ {self.PassageNum}')

        # Сбросим накопленные данные
        # self.x_index = 0    # Индекс полученного пакета данных

        # Проверим корректность подключения платы STM
        if self.STM_Settings[List].currentText() == '-----':
            message('Выберите корректный COM порт для STM', icon='Warning')
            return

        # Проверим корректность подключения GPS модуля
        if self.GPS_CheckBox.checkState() == Qt.CheckState.Checked:
            if self.GPS_Settings[List].currentText() == '-----':
                message('Выберите корректный COM порт для GPS', icon='Warning')
                return
        else:
            self.printer.printing(text='GPS модуль не подключён!')
            self.GPS_Settings[List].setCurrentIndex(self.STM_Settings[List].findText('-----'))
            self.UsingGps_Flag = False


        # Если используем GPS модуль, то уведомим пользователя о необходимости сбора координат текущего местоположения
        if self.UsingGps_Flag:
            if not self.CoordinatesAreCollected:
                msg = QMessageBox()
                msg.setWindowIcon(QIcon('../ui/Telega.ico'))
                msg.setWindowTitle('Уведомление')
                msg.setText('Начать сбор координат местоположения?')
                msg.setStandardButtons(QMessageBox.Ok | QMessageBox.No)
                msg.setIcon(QMessageBox.Question)
                msg.show()
                if msg.exec_() == QMessageBox.Ok:
                    self.get_Coordinates()
                    return
                else:
                    pass

        self.blockInputs()
        self.Command_Buttons[Stop_Measuring].setEnabled(True)
        self.CoordinatesAreCollected = False
        self.STM_ComPort.startMeasuring(
            com_port_name=self.STM_Settings[List].currentText(),
            saving_path=self.Saving_Params[Dir][LineEdit].text(),
            template_name=self.Saving_Params[FileName][LineEdit].text(),
            data_type=f'RawData_{self.PassageNum}'
        )

    def stop_Measuring(self):
        self.unblockInputs()

        self.Command_Buttons[Stop_Measuring].setEnabled(True)
        self.Command_Buttons[Get_Coordinates].setEnabled(True)

        self.STM_ComPort.stopMeasuring()

        self.PassageNum += 1
        self.Command_Buttons[Stop_Measuring].setEnabled(False)

    def get_Coordinates(self):
        # Запуск чтения данных с модуля GPS
        if self.GPS_CheckBox.checkState() == Qt.CheckState.Checked:
            if self.GPS_Settings[List].currentText() == '-----':
                message('Выберите корректный COM порт для GPS', icon='Warning')
                return

            self.Command_Buttons[Stop_Measuring].setEnabled(False)
            self.Command_Buttons[Start_Measuring].setEnabled(False)
            self.Command_Buttons[Get_Coordinates].setEnabled(False)

            self.GPS_ComPort.gettingCoordinates(
                com_port_name=self.GPS_Settings[List].currentText(),
                saving_path=self.Saving_Params[Dir][LineEdit].text(),
                template_name=self.Saving_Params[FileName][LineEdit].text(),
            )
        else:
            self.printer.printing(text='GPS модуль не подключён!')
            self.GPS_Settings[List].setCurrentIndex(self.STM_Settings[List].findText('-----'))
            self.UsingGps_Flag = False

    ####### Функционал для self.Plot_Widget #######
    # def init_Plots(self):
    #     for data in [Acc, Gyro]:
    #         for axis in [X, Y, Z]:
    #             self.Plots[data][axis].setBackground("w")
    #             self.Plots[data][axis].showGrid(x=True, y=True)
    #             plot_style = {"color": "grey", "font-size": "14px"}
    #             self.Plots[data][axis].setLabel("left", y_labels[data][axis], **plot_style)
    #             if axis == Z:
    #                 self.Plots[data][axis].setLabel("bottom", "Time, seconds", **plot_style)
    #
    #             self.lines[data][axis] = self.Plots[data][axis].plot(self.x_array, self.plot_values[titles[3 * data + axis]], pen=self.pens[data][axis])
    #
    # def update_Plots(self, values: dir):
    #     if self.x_index < MAX_X_LENGTH:
    #         self.x_array[self.x_index] = values["Time"]
    #         for title in titles:
    #             self.plot_values[title][self.x_index] = values[title]
    #
    #         # Если получили первую посылку данных, то выровняем графики
    #         if self.x_index == 0:
    #             self.x_array = np.arange(values["Time"], values["Time"] + MAX_X_LENGTH * PERIOD, PERIOD)
    #             for data in [Acc, Gyro]:
    #                 for axis in [X, Y, Z]:
    #                     for index in range(1, len(self.x_array)):
    #                         self.plot_values[titles[3 * data + axis]][index] = self.plot_values[titles[3 * data + axis]][0]
    #
    #         self.x_index += 1
    #
    #     else:
    #         self.x_array = self.x_array[1:]
    #         self.x_array = np.append(self.x_array, values["Time"])
    #         for title in titles:
    #             self.plot_values[title] = self.plot_values[title][1:]
    #             self.plot_values[title] = np.append(self.plot_values[title], values[title])
    #
    #     for data in [Acc, Gyro]:
    #         for axis in [X, Y, Z]:
    #             self.lines[data][axis].setData(self.x_array, self.plot_values[titles[3 * data + axis]])

    ####### Функционал для self.Sensor_Values #######
    def init_Values(self):
        pass

    def update_Values(self, values: dir):
        self.Sensor_Values[Acc][X].display(values['Acc_X']); self.Sensor_Values[Acc][Y].display(values['Acc_Y']); self.Sensor_Values[Acc][Z].display(values['Acc_Z'])
        self.Sensor_Values[Gyro][X].display(values['Gyro_X']); self.Sensor_Values[Gyro][Y].display(values['Gyro_Y']); self.Sensor_Values[Gyro][Z].display(values['Gyro_Z'])

    ####### Функционал для self.SavingSettings_Widget #######
    def init_SavingSettings(self):
        try:
            self.Saving_Params[Dir][LineEdit].setText(self.json_data["DataCollecting"]["dir"])
        except Exception:
            pass

        self.Saving_Params[Dir][LineEdit].setEnabled(False)
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
        com_ports = get_ComPorts()
        self.STM_Settings[List].addItems(com_ports)

        # Зададим значение по умолчанию, если в дескрипторе есть 'STM'
        for port in com_ports.keys():
            if 'STM' in com_ports[port]['desc']:
                self.STM_Settings[List].setCurrentIndex(list(com_ports.keys()).index(port))

        self.STM_Settings[Help_Button].clicked.connect(
            lambda: message(get_ComPorts()[f'{self.STM_Settings[List].currentText()}']["desc"],
                            icon='Information')
        )

        self.STM_Settings[UpdateButton].clicked.connect(self.update_STM_ComPorts)
        self.STM_Settings[UpdateButton].setIcon(QIcon('../ui/update.jpg'))

    def update_STM_ComPorts(self):
        com_ports = get_ComPorts()
        self.STM_Settings[List].clear()
        self.STM_Settings[List].addItems(com_ports)

        # Зададим значение по умолчанию, если в дескрипторе есть 'STM'
        for port in com_ports.keys():
            if 'STM' in com_ports[port]['desc']:
                self.STM_Settings[List].setCurrentIndex(list(com_ports.keys()).index(port))

    ####### Функционал для self.GPS_Settings #######
    def init_GPS_Settings(self):
        com_ports = get_ComPorts()
        self.GPS_Settings[List].addItems(com_ports)

        # Зададим значение по умолчанию, если в дескрипторе есть 'GPS'
        for port in com_ports.keys():
            if 'GPS' in com_ports[port]['desc']:
                self.GPS_Settings[List].setCurrentIndex(list(com_ports.keys()).index(port))

        self.GPS_Settings[Help_Button].clicked.connect(
            lambda: message(get_ComPorts()[f'{self.GPS_Settings[List].currentText()}']["desc"],
                            icon='Information')
        )

        self.GPS_Settings[UpdateButton].clicked.connect(self.update_GPS_ComPorts)
        self.GPS_Settings[UpdateButton].setIcon(QIcon('../ui/update.jpg'))

    def update_GPS_ComPorts(self):
        com_ports = get_ComPorts()
        self.GPS_Settings[List].clear()
        self.GPS_Settings[List].addItems(com_ports)

    ####### Дополнительный функционал #######
    def end_of_initialSetting(self):
        self.STM_ComPort.stopInitialSettings()
        message(text='Завершена выставка датчиков', icon='i')
        self.unblockInputs()
        self.Command_Buttons[Start_InitialSetting].setEnabled(False)

    def end_of_getting_coordinates(self):
        self.Command_Buttons[Stop_Measuring].setEnabled(True)
        self.Command_Buttons[Start_Measuring].setEnabled(True)
        self.Command_Buttons[Get_Coordinates].setEnabled(True)

        message(text='Завершён сбор координат текущего местоположения', icon='i')
        self.printer.printing('Завершён сбор координат текущего местоположения')

        self.CoordinatesAreCollected = True
