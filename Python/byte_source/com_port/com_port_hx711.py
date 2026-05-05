# System imports
from typing import Callable, Any
from serial import Serial, SerialException, SerialTimeoutException

# External imports

# User imports
from app_logger import app_logger
from byte_source.com_port.com_port import ComPort
from byte_source.com_port.com_port_error import ComPortReadError


#########################

# Класс для работы с com портом
class ComPortHX711(ComPort):
    _set_foo_stage_command = bytes([0xc8, 0x8c, 0xff, 0xaa, 0x01, 0x00])
    _set_measure_stage_command = bytes([0xc8, 0x8c, 0xff, 0xaa, 0x02, 0x00])

    def __init__(self, port_name: str, baudrate: int, printing_func: Callable[..., None] = print):
        super().__init__(port_name, baudrate, printing_func)

    def setup(self):
        """ Настройка порта для работы с платой МК с АЦП HX711 """
        super().setup()

        app_logger.debug(f'Выполнение рукопожатия по порту {self._port.port}')
        self._handshake()

        self._send_command(self._set_measure_stage_command)

    def cleanup(self):
        """ Завершение работы порта """
        self._send_command(self._set_foo_stage_command)
        super().cleanup()

    def _send_command(self, command: bytes):
        """ Отправка команды по com-порту """
        app_logger.debug(f'Отправка команды {command}')
        self._port.write(command)

    def _handshake(self):
        """ Проверка корректности подключения порта """
        pass