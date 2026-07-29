# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pyqtgraph as pg
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QToolButton,
)
from PyQt5.uic import loadUi

from ADCAnalysis import TorqueCalculation, TorqueCalculationError
from app_logger import app_logger
from config import config
from decoding.hx711_decoding import HX711Data
from gui.com_port_reader import ComPortReader, ComPortReaderException
from gui.com_port_settings import ComPortSettings, ComPortSettingsError, RadioButtonsDict
from gui.data_storage import DataStorage
from gui.plotting_widget import PlottingWidget
from gui.saving_path_settings import InvalidPathError, SavingPathSetting


class ProgramStage:
    def on_enter(self, window: "MainWindow") -> None:
        window._sync_controls()

    def on_start(self, window: "MainWindow") -> None:
        pass

    def on_stop(self, window: "MainWindow") -> None:
        pass


class SettingStage(ProgramStage):
    def on_enter(self, window: "MainWindow") -> None:
        window._unlock_input()
        super().on_enter(window)

    def on_start(self, window: "MainWindow") -> None:
        window._configure_and_connect()


class ConnectingStage(ProgramStage):
    def on_enter(self, window: "MainWindow") -> None:
        window._lock_input()
        super().on_enter(window)

    def on_stop(self, window: "MainWindow") -> None:
        window._disconnect_session()


class ReadyStage(ProgramStage):
    def on_enter(self, window: "MainWindow") -> None:
        window._lock_input()
        super().on_enter(window)

    def on_start(self, window: "MainWindow") -> None:
        window._start_measurement()

    def on_stop(self, window: "MainWindow") -> None:
        window._disconnect_session()


class MeasuringStage(ProgramStage):
    def on_enter(self, window: "MainWindow") -> None:
        window._lock_input()
        super().on_enter(window)

    def on_stop(self, window: "MainWindow") -> None:
        window._stop_measurement()


class MainWindow(QMainWindow):
    _main_window_path: Path = Path(__file__).parent / "ui" / "main_window.ui"

    def __init__(self) -> None:
        super().__init__(parent=None)
        loadUi(self._main_window_path, self)

        self.setWindowTitle("Динамометрический стенд")
        self.setWindowState(Qt.WindowMaximized)

        self._start_button: QPushButton = self.findChild(QPushButton, "StartButton")
        self._stop_button: QPushButton = self.findChild(QPushButton, "StopButton")
        self._msg_text_edit: QTextEdit = self.findChild(QTextEdit, "MessagesTextEdit")

        self._saving_path_setting = SavingPathSetting(
            saving_path_edit=self.findChild(QLineEdit, "SavingPathEdit"),
            choose_saving_path_button=self.findChild(QToolButton, "ChooseSavingPathButton"),
        )
        self._com_port_settings = ComPortSettings(
            com_port_combo_box=self.findChild(QComboBox, "ComPortComboBox"),
            com_port_info_button=self.findChild(QPushButton, "ComPortInfoButton"),
            update_com_ports_button=self.findChild(QPushButton, "UpdateComPortsButton"),
            radio_buttons=RadioButtonsDict(
                rb_921600=self.findChild(QRadioButton, "RadioButton_921600"),
                rb_460800=self.findChild(QRadioButton, "RadioButton_460800"),
                rb_230400=self.findChild(QRadioButton, "RadioButton_230400"),
                rb_115200=self.findChild(QRadioButton, "RadioButton_115200"),
                rb_57600=self.findChild(QRadioButton, "RadioButton_57600"),
                rb_9600=self.findChild(QRadioButton, "RadioButton_9600"),
            ),
        )
        self._plotters: dict[int, PlottingWidget] = {
            1: PlottingWidget(self.findChild(pg.PlotWidget, "PlotterSensor_1")),
            2: PlottingWidget(self.findChild(pg.PlotWidget, "PlotterSensor_2")),
        }

        self._com_port_reader = ComPortReader()
        self._torque_calculation = TorqueCalculation()
        self._data_storage = DataStorage()
        self._saving_path: Path | None = None
        self._measurement_index = 1
        self._start_after_handshake = False
        self._closing = False
        self._stage: ProgramStage = SettingStage()

        if not self._check_UI():
            app_logger.error("main_window.ui is configured incorrectly")
            QMessageBox.critical(self, "Ошибка", "main_window.ui настроен некорректно")
            QApplication.quit()
            raise RuntimeError("main_window.ui is configured incorrectly")

        self._init_UI()
        self._set_stage(SettingStage())

    def closeEvent(self, event) -> None:
        self._closing = True
        self.hide()
        event.accept()
        self._data_storage.close()
        self._com_port_reader.shutdown()
        app_logger.info("Завершение работы приложения")
        QApplication.quit()

    def _init_UI(self) -> None:
        self._start_button.clicked.connect(self._on_start_clicked)
        self._stop_button.clicked.connect(self._on_stop_clicked)

        self._com_port_reader.data_received.connect(self._data_received)
        self._com_port_reader.handshake_done.connect(self._on_handshake_done)
        self._com_port_reader.handshake_failed.connect(self._on_handshake_failed)
        self._com_port_reader.connection_failed.connect(self._on_connection_failed)
        self._com_port_reader.error_occurred.connect(self._error_handler)

        for sensor_id in config.calibration.sensor_id_list:
            plotter = self._plotters[sensor_id]
            plotter.configure(
                title=f"Показания датчика #{sensor_id}",
                x_label="Время (с)",
                y_label="Крутящий момент (H * m)",
                background="w",
                pen=pg.mkPen(config.main_window_config.pen_params[sensor_id]),
                symbol="o",
                symbolSize=4,
            )

    def _check_UI(self) -> bool:
        return (
            isinstance(self._start_button, QPushButton)
            and isinstance(self._stop_button, QPushButton)
            and isinstance(self._msg_text_edit, QTextEdit)
        )

    def _on_start_clicked(self) -> None:
        self._stage.on_start(self)

    def _on_stop_clicked(self) -> None:
        self._stage.on_stop(self)

    def _configure_and_connect(self) -> None:
        try:
            saving_path = self._get_confirmed_saving_path()
            port_name = self._com_port_settings.get_port_name()
            baudrate = self._com_port_settings.get_baudrate()

            self._saving_path = saving_path
            self._measurement_index = 1
            self._start_after_handshake = True
            self._clear_plots()

            self._com_port_settings.save_config()
            self._saving_path_setting.save_config()

            bin_file = self._next_file_path("hx711_stream", ".bin")
            self._set_stage(ConnectingStage())
            self._append_message(
                f"Подключение к МК: порт {port_name}, скорость {baudrate}"
            )
            self._com_port_reader.configure(
                logger_config=config.logger_config,
                com_port_name=port_name,
                baudrate=baudrate,
                bin_file=bin_file,
            )
        except (InvalidPathError, ComPortSettingsError, ComPortReaderException) as err:
            app_logger.error("Ошибка подготовки запуска: %s", err)
            QMessageBox.warning(self, "Ошибка запуска", str(err))
            self._set_stage(SettingStage())
        except Exception as err:
            app_logger.exception("Непредвиденная ошибка запуска")
            QMessageBox.critical(self, "Непредвиденная ошибка", str(err))
            self._set_stage(SettingStage())

    def _start_measurement(self) -> None:
        try:
            csv_file = self._next_file_path("measurement", ".csv")
            self._data_storage.set_file(csv_file)
            self._com_port_reader.start_measuring()
            self._set_stage(MeasuringStage())
            self._append_message(f"Начало измерения. CSV: {csv_file}")
        except ComPortReaderException as err:
            self._data_storage.close()
            app_logger.error("Ошибка старта измерения: %s", err)
            QMessageBox.warning(self, "Ошибка измерения", str(err))
        except Exception as err:
            self._data_storage.close()
            app_logger.exception("Непредвиденная ошибка старта измерения")
            QMessageBox.critical(self, "Непредвиденная ошибка", str(err))

    def _stop_measurement(self) -> None:
        try:
            self._com_port_reader.stop_measuring()
        except ComPortReaderException as err:
            app_logger.warning("Остановка измерения: %s", err)
        finally:
            saved_count = self._data_storage.count
            self._data_storage.close()
            self._measurement_index += 1
            if not self._closing:
                self._set_stage(ReadyStage())
                self._append_message(f"Измерение остановлено. Записано строк: {saved_count}")

    def _disconnect_session(self) -> None:
        self._start_after_handshake = False
        self._data_storage.close()
        self._com_port_reader.shutdown()
        if not self._closing:
            self._set_stage(SettingStage())
            self._append_message("Соединение с МК закрыто")

    def _on_handshake_done(self) -> None:
        self._append_message("МК подтвердил соединение")
        self._set_stage(ReadyStage())
        if self._start_after_handshake:
            self._start_after_handshake = False
            self._start_measurement()

    def _on_handshake_failed(self) -> None:
        self._handle_session_failure("МК не подтвердил соединение")

    def _on_connection_failed(self, message: str) -> None:
        self._handle_session_failure(f"Не удалось открыть COM-порт: {message}")

    def _error_handler(self, error_info: str) -> None:
        self._handle_session_failure(error_info)

    def _handle_session_failure(self, message: str) -> None:
        app_logger.error("Ошибка сессии МК: %s", message)
        self._data_storage.close()
        if not self._closing:
            QMessageBox.critical(self, "Ошибка выполнения", message)
            self._disconnect_session()

    def _data_received(self, adc_data: HX711Data) -> None:
        self._data_storage.add_package(adc_data)
        self._calc_torque(adc_data)

    def _calc_torque(self, adc_data: HX711Data) -> None:
        try:
            torque = self._torque_calculation.calc_torque(
                sensor_id=adc_data.id,
                adc_value=adc_data.adc_value * int(adc_data.gain),
            )
            self._plot_received_data(adc_data.id, adc_data.time, torque)
        except TorqueCalculationError:
            app_logger.exception("Ошибка расчёта крутящего момента")
            self._append_message("Ошибка расчёта крутящего момента по данным АЦП")
            self._stop_measurement()
            QMessageBox.warning(
                self,
                "Ошибка выполнения",
                "Ошибка расчёта крутящего момента по данным АЦП",
            )

    def _plot_received_data(self, plotter_id: int, x_value: float, y_value: float) -> None:
        self._plotters[plotter_id].append_data(x_value, y_value)

    def _get_confirmed_saving_path(self) -> Path:
        saving_path = self._saving_path_setting.get_saving_path()
        if any(saving_path.iterdir()):
            reply = QMessageBox.question(
                self,
                "Подтверждение",
                "Указанная директория не пустая.\n"
                "Новые файлы будут созданы с очередным номером.\n"
                "Использовать указанный путь?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                raise InvalidPathError("Пользователь отменил выбор директории")
        return saving_path

    def _next_file_path(self, stem: str, suffix: str) -> Path:
        if self._saving_path is None:
            raise InvalidPathError("Не указан путь сохранения")

        index = self._measurement_index
        while True:
            file_path = self._saving_path / f"{stem}_{index:03d}{suffix}"
            if not file_path.exists():
                return file_path
            index += 1

    def _clear_plots(self) -> None:
        for plotter in self._plotters.values():
            plotter.clear()

    def _lock_input(self) -> None:
        self._com_port_settings.lock_input()
        self._saving_path_setting.lock_input()

    def _unlock_input(self) -> None:
        self._com_port_settings.unlock_input()
        self._saving_path_setting.unlock_input()

    def _set_stage(self, stage: ProgramStage) -> None:
        self._stage = stage
        self._stage.on_enter(self)

    def _sync_controls(self) -> None:
        self._start_button.setEnabled(isinstance(self._stage, (SettingStage, ReadyStage)))
        self._stop_button.setEnabled(isinstance(self._stage, (ConnectingStage, ReadyStage, MeasuringStage)))

    def _append_message(self, message: str) -> None:
        app_logger.info(message)
        self._msg_text_edit.append(message)
