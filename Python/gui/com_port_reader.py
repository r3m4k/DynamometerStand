# -*- coding: utf-8 -*-
"""Модуль для асинхронного чтения данных из COM-порта.

Содержит класс `ComPortReader`, который управляет фоновым потоком для
непрерывного чтения байтов из COM-порта, их декодирования с помощью
`HX711Decoder` и передачи полученных пакетов в главный поток через сигналы.
"""

# System imports
from typing import Optional

# External imports
from PyQt5.QtCore import QObject, QThread, pyqtSignal

# User imports
from byte_source.com_port import ComPort, ComPortReadError
from decoding import DecoderProtocol
from decoding.hx711_decoding import HX711Decoder, HX711Data

##########################################################

class ComPortReader(QObject):
    """Управляет фоновым чтением данных из COM-порта.

    Позволяет настроить порт, запустить и остановить чтение в отдельном потоке.
    Полученные пакеты данных передаются через сигнал `data_received`.
    Ошибки и завершение работы также транслируются сигналами.

    Сигналы:
        data_received(HX711Data): Испускается при получении нового пакета данных.
        error_occurred(str): Испускается при возникновении ошибки чтения или декодирования.
        finished(): Испускается после полной остановки потока и очистки ресурсов.
    """

    data_received = pyqtSignal(HX711Data)
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()

    # ------------------------------------------------------------------------------

    class _ComPortReaderWorker(QObject):
        """Внутренний класс, выполняющий чтение из порта в отдельном потоке.

        Сигналы:
            data_received(HX711Data): Пробрасывается наружу.
            error_occurred(str): Пробрасывается наружу.
            finished(): Испускается при завершении работы (всегда).
        """

        data_received = pyqtSignal(HX711Data)
        error_occurred = pyqtSignal(str)
        finished = pyqtSignal()

        def __init__(self, port: ComPort):
            """Инициализирует воркер с заданным объектом порта.

            Args:
                port (ComPort): Объект для работы с COM-портом (должен быть
                    создан заранее, открытие произойдёт в контекстном менеджере).
            """
            super().__init__()
            self._com_port: ComPort = port
            self._decoder: DecoderProtocol[dict[int, list[HX711Data]]] = HX711Decoder()
            self._reading_flag = False

        def run(self) -> None:
            """Основной метод, выполняемый в потоке.

            Открывает порт, читает байты, передаёт их декодеру и отправляет
            готовые пакеты через сигнал `data_received`. При ошибке испускает
            `error_occurred`. В любом случае по завершении испускает `finished`.
            """
            self._reading_flag = True
            try:
                with self._com_port as port:
                    while self._reading_flag:
                        self._decoder.byte_processing(port.read_byte())
                        # Итерируемся по копии ключей, чтобы избежать проблем при модификации словаря
                        for sensor_id in list(self._decoder.received_data.keys()):
                            sensor_data = self._decoder.received_data[sensor_id]
                            if sensor_data:
                                self.data_received.emit(sensor_data.pop())
            except ComPortReadError as e:
                self.error_occurred.emit(f"Ошибка порта: {e}")
            except Exception as e:
                self.error_occurred.emit(f"Неизвестная ошибка: {e}")
            finally:
                self.finished.emit()

        def stop(self) -> None:
            """Сигнализирует воркеру о необходимости завершить чтение."""
            self._reading_flag = False

    # ------------------------------------------------------------------------------

    def __init__(self) -> None:
        """Инициализирует объект `ComPortReader` без настройки порта."""
        super().__init__()
        self._worker_thread: Optional[QThread] = None
        self._worker: Optional[ComPortReader._ComPortReaderWorker] = None
        self._com_port: Optional[ComPort] = None

    def configure_port(self, port_name: str, baudrate: int) -> None:
        """Сохраняет параметры порта для последующего использования.

        Создаёт объект `ComPort` с указанными параметрами. Если чтение уже
        запущено, порт нельзя изменить (выбрасывается исключение).

        Args:
            port_name (str): Имя порта.
            baudrate (int): Скорость передачи (должна быть из списка допустимых).

        Raises:
            RuntimeError: Если чтение уже запущено.
        """
        if self._worker_thread is not None and self._worker_thread.isRunning():
            raise RuntimeError("Нельзя изменить порт во время чтения")
        self._com_port = ComPort(port_name, baudrate)

    def start_reading(self) -> None:
        """Запускает фоновое чтение данных из порта.

        Создаёт новый поток и воркер, перемещает воркер в поток, подключает сигналы
        и запускает поток. Если поток уже запущен, метод ничего не делает.

        Raises:
            RuntimeError: Если порт не был предварительно настроен через `configure_port`.
        """
        if self._com_port is None:
            raise RuntimeError('Перед запуском необходимо выполнить конфигурацию порта!')
        if self._worker_thread and self._worker_thread.isRunning():
            return

        self._worker_thread = QThread()
        self._worker = self._ComPortReaderWorker(self._com_port)
        self._worker.moveToThread(self._worker_thread)

        # Подключаем сигналы
        self._worker_thread.started.connect(self._worker.run)
        self._worker.data_received.connect(self.data_received)
        self._worker.error_occurred.connect(self.error_occurred)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)
        self._worker_thread.finished.connect(self._on_thread_finished)

        self._worker_thread.start()

    def stop_reading(self) -> None:
        """Запрашивает остановку чтения.

        Устанавливает флаг остановки в воркере. Поток завершится после текущей
        итерации цикла или блокирующего чтения (следующий байт).
        """
        if self._worker is not None:
            self._worker.stop()

    def _on_thread_finished(self) -> None:
        """Слот, вызываемый после завершения потока. Очищает ссылки и испускает сигнал."""
        self._worker_thread = None
        self._worker = None
        self.finished.emit()