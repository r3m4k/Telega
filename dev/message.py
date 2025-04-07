from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QIcon


def message(text, icon=QMessageBox.NoIcon):
    """
    Отправка пользователю сообщения
    """
    msg = QMessageBox()
    msg.setWindowIcon(QIcon('../ui/Telega.ico'))
    msg.setWindowTitle('Уведомление')
    msg.setIcon(icon)
    msg.setText(text)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.show()
    msg.exec()
