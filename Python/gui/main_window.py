# System imports
from pathlib import Path

# External imports
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QTextEdit, QToolButton,
    QPushButton, QApplication, QMessageBox,
    QComboBox, QRadioButton, QLineEdit
)
from PyQt5.uic import loadUi
import pyqtgraph as pg

# User imports
from gui.saving_path_settings import SavingPathSetting
from gui.com_port_settings import ComPortSettings, RadioButtonsDict
from gui.plotting_widget import PlottingWidget


##########################################################

class MainWindow(QMainWindow):
    _main_window_path: Path = Path(__file__).parent / "ui" / "main_window.ui"

    def __init__(self):
        super().__init__(parent=None)

        # Загрузим разметку страницы
        loadUi(self._main_window_path, self)

        # Зададим название окна и устанавливаем полноэкранный режим
        self.setWindowTitle('Динамометрический стенд')
        self.setWindowState(Qt.WindowState(Qt.WindowMaximized))

        # ------------------------------
        self._start_button: QPushButton = self.findChild(QPushButton, "StartButton")
        self._stop_button: QPushButton = self.findChild(QPushButton, "StopButton")
        # ------------------------------
        self._msg_text_edit: QTextEdit = self.findChild(QTextEdit, "MessagesTextEdit")
        # ------------------------------
        self._saving_path_setting = SavingPathSetting(
            saving_path_edit = self.findChild(QLineEdit, "SavingPathEdit"),
            choose_saving_path_button = self.findChild(QToolButton, "ChooseSavingPathButton")
        )
        # ------------------------------
        self._com_port_settings = ComPortSettings(
            com_port_combo_box = self.findChild(QComboBox, "ComPortComboBox"),
            com_port_info_button = self.findChild(QPushButton, "ComPortInfoButton"),
            update_com_ports_button = self.findChild(QPushButton, "UpdateComPortsButton"),
            radio_buttons = RadioButtonsDict(
                rb_921600 = self.findChild(QRadioButton, "RadioButton_921600"),
                rb_460800 = self.findChild(QRadioButton, "RadioButton_460800"),
                rb_230400 = self.findChild(QRadioButton, "RadioButton_230400"),
                rb_115200 = self.findChild(QRadioButton, "RadioButton_115200"),
                rb_57600  = self.findChild(QRadioButton, "RadioButton_57600"),
                rb_9600   = self.findChild(QRadioButton, "RadioButton_9600"),
            )
        )
        # ------------------------------
        self._plotters: dict[int, PlottingWidget] = {
            1: PlottingWidget(self.findChild(pg.PlotWidget, "PlotterSensor_1")),
            2: PlottingWidget(self.findChild(pg.PlotWidget, "PlotterSensor_2"))
        }
        # ------------------------------

        # Настроим интерфейс
        if not self._check_UI():
            QMessageBox.critical(self, "Ошибка", "Неправильно настроен main_window")
            QApplication.quit()
            exit(10)

        self._init_UI()

    def closeEvent(self, event)-> None:
        """ Дополнительная логика перед закрытием окна """
        pass

    def _init_UI(self) -> None:
        # Подключим нажатие кнопок к соответствующим функциям-обработчикам
        self._start_button.clicked.connect(self._start_measuring)
        self._stop_button.clicked.connect(self._stop_measuring)

        # Настройка виджетов для графического отображения данных АЦП
        pen_params: dict[int, dict[str, ...]] = {
            1: {'color': "#ff003b",
                'width': 2.5},
            2: {'color': "#ff4400",
                'width': 2.5}
        }
        
        for sensor_id in self._plotters.keys():
            plotter = self._plotters[sensor_id]
            plotter.configure(
                title=f'Показания датчика #{sensor_id}',
                x_label='Время (с)',
                y_label='Крутящий момент (H * m)',
                background='w',
                pen=pg.mkPen(pen_params[sensor_id]),
                symbol='o',
                symbolSize=4
            )

    def _check_UI(self) -> bool:
        return (isinstance(self._start_button, QPushButton) and
                isinstance(self._stop_button, QPushButton) and
                isinstance(self._msg_text_edit, QTextEdit))


    def _start_measuring(self) -> None: ...

    def _stop_measuring(self) -> None: ...
