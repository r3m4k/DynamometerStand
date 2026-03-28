# System imports
from serial import Serial, SerialException, SerialTimeoutException

# External imports

# User imports
from utils import confirm_from_console
from byte_source.bytes_source import BytesSource
from byte_source.com_port.com_port_error import ComPortReadError


#########################

# Класс для работы с com портом
class ComPort(BytesSource):
    _port: Serial     # Используемый com порт

    def __init__(self, port_name: str, baudrate: int):
        self._port_name: str = port_name                # Название используемого com порта (например, COM1)
        self._baudrate: int = baudrate                  # Частота порта

    def setup(self):
        """ Настройка порта """
        print(f'\nПодключение к порту {self._port_name}...')
        try:
            self._port = Serial(port=self._port_name, baudrate=self._baudrate)
            print('✅ Успешно')
        except Exception as err:
            print('❌ Ошибка подключения. Подробная информация:')
            print(err)
            raise ComPortReadError(f"Ошибка последовательного порта: {err}", original_exception=err)

    def cleanup(self):
        """ Завершение работы порта """
        try:
            self._port.close()
        except Exception:
            pass

    def read_byte(self) -> bytes:
        try:
            data = self._port.read(1)
            if not data:  # таймаут, байт не прочитан
                raise ComPortReadError("Таймаут при чтении байта из COM-порта")
            return data
        except (SerialException, SerialTimeoutException) as err:
            raise ComPortReadError(f"Ошибка последовательного порта: {err}", original_exception=err)
