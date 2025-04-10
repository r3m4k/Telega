from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QIcon


def message(text, icon='NoIcon'):
    """
    Отправка пользователю сообщения
    """
    QtIcon: QMessageBox
    if icon == 'NoIcon':
        QtIcon = QMessageBox.NoIcon
    elif icon == ('Warning' or '!'):
        QtIcon = QMessageBox.Warning
    elif icon == ('Information' or 'Info' or 'i'):
        QtIcon = QMessageBox.Information
    elif icon == ('Question' or '?'):
        QtIcon = QMessageBox.Question
    elif icon == ('Critical' or 'error'):
        QtIcon = QMessageBox.Critical
    else:
        raise RuntimeError('Неправильно передан параметр icon')

    msg = QMessageBox()
    msg.setWindowIcon(QIcon('../ui/Telega.ico'))
    msg.setWindowTitle('Уведомление')
    msg.setIcon(QtIcon)
    msg.setText(text)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.show()
    msg.exec()
