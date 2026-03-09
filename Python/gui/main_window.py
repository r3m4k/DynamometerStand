# System imports
from pathlib import Path

# External imports
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QListWidget, QToolButton,
    QPushButton, QVBoxLayout, QWidget,
    QComboBox, QRadioButton, QLineEdit
)
from PyQt5.uic import loadUi
from PyQt5.QtGui import QPixmap

# User imports


##########################################################

class MainWindow(QMainWindow):
    _main_window_path: Path = Path(__file__).parent / "ui" / "main_window.ui"

    def __init__(self):
        super(QMainWindow, self).__init__(parent=None)

        self._ui = loadUi(self._main_window_path, self)     # Загрузим разметку страницы
        self.setWindowTitle('Динамометрический стенд')      # Зададим название окна
        self.setWindowState(Qt.WindowState(Qt.WindowMaximized))             # Устанавливаем полноэкранный режим

        # ------------------------------

        self._start_button: QPushButton = self.findChild(QPushButton, "StartButton")
        self._stop_button: QPushButton = self.findChild(QPushButton, "StopButton")

        # ------------------------------

        self._msg_text_edit: QListWidget = self.findChild(QListWidget, "MessagesTextEdit")

        # ------------------------------

        self._com_port_combo_box: QComboBox = self.findChild(QComboBox, "ComPortComboBox")
        self._com_port_info_button: QPushButton = self.findChild(QPushButton, "ComPortInfoButton")

        # ------------------------------

        self._saving_path_edit: QLineEdit = self.findChild(QLineEdit, "SavingPathEdit")
        self._choose_saving_path_button: QToolButton = self.findChild(QToolButton, "ChooseSavingPathButton")

        # ------------------------------

        self._radio_button_921600: QRadioButton = self.findChild(QRadioButton, "RadioButton_921600")
        self._radio_button_460800: QRadioButton = self.findChild(QRadioButton, "RadioButton_460800")
        self._radio_button_230400: QRadioButton = self.findChild(QRadioButton, "RadioButton_230400")
        self._radio_button_115200: QRadioButton = self.findChild(QRadioButton, "RadioButton_115200")
        self._radio_button_57600: QRadioButton  = self.findChild(QRadioButton, "RadioButton_57600")
        self._radio_button_9600: QRadioButton   = self.findChild(QRadioButton, "RadioButton_9600")

        # ------------------------------

        # Настроим интерфейс
        if not self._check_UI():
            print('Неправильно настроен main_window. Завершение программы...')
            exit(10)
        self._init_UI()

        # Добавим по умолчанию виджет для отправки товаров
        self._add_sending_widget()

    def _init_UI(self) -> None:
        """ Настройка UI """
        pass

    def _check_UI(self) -> bool:
        """Проверка корректности инициализации элементов интерфейса"""
        pass

    def closeEvent(self, event)-> None:
        """ Дополнительная логика перед закрытием окна """
        pass

