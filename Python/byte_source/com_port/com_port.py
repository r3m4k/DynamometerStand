# System imports
import serial

# External imports

# User imports
from byte_source.bytes_source import BytesSource
from utils import get_cache, save_cache, confirm_from_console
from .utils import get_ComPorts


#########################

# Класс для работы с com портом
class ComPort(BytesSource):
    _port: serial.Serial     # Используемый com порт

    def __init__(self, port_name: str, baudrate: int):
        self._port_name: str = port_name                # Название используемого com порта (например, COM1)
        self._baudrate: int = baudrate                  # Частота порта

    def setup(self):
        """ Настройка порта """
        print('\nПодключение к порту...')
        try:
            self._port = serial.Serial(port=self._port_name, baudrate=self._baudrate)
            print('✅ Успешно')
        except Exception as err:
            print('❌ Ошибка подключения. Подробная информация:')
            print(err)

    def cleanup(self):
        """ Завершение работы порта """
        try:
            self._port.close()
        except Exception:
            pass

    def read_byte(self) -> bytes:
        return self._port.read(1)


# Класс для настройки ComPort
class ComPortSetting:
    _port_name: str
    _baudrate: int

    def __init__(self):
        self._ports = get_ComPorts()        # Список подключённых портов
        self._cache_data = get_cache()      # Сохранённый кэш

        try:
            _cache_port = self._cache_data['ComPort']['port']

            print(f'Использовать {_cache_port['name']}?\n'
                  f'| desc = {_cache_port['desc']}\n'
                  f'| hwid = {_cache_port['hwid']}\n'
                  f'| baudrate = {_cache_port['baudrate']}')

            if confirm_from_console():
                self._port_name = _cache_port['name']
                self._baudrate = _cache_port['baudrate']
            else:
                self._load_comport_from_console()

        except KeyError:
            self._load_comport_from_console()

    def get_bytes_source(self) -> BytesSource:
        if self._port_name:
            save_cache(self._cache_data)
            return ComPort(self._port_name, self._baudrate)
        else:
            raise RuntimeError('Не выбран com порт!')

    def _load_comport_from_console(self):

        port_list = list(self._ports.keys())

        if len(port_list) == 0:
            print('# -----------------------------------------\n'
                  'Не найдено ни одного com порта!\n'
                  'Завершение программы...\n'
                  '# -----------------------------------------\n')
            exit(1)

        print('# -----------------------------------------\n'
              'Информация о подключённых портах:\n'
              '# -----------------------------------------\n')

        for port in port_list:
            print(f'#{port_list.index(port) + 1}: {port}\n'
                  f'desc: {self._ports[port]["desc"]}\n'
                  f'hwid: {self._ports[port]["hwid"]}\n')

        print('# -----------------------------------------')

        port_num = int(input('Выберите номер порта: '))
        port_name = port_list[port_num - 1]

        print('# -----------------------------------------')

        baudrate_list = [
            9600,
            57600,
            115200,
            230400,
            460800,
            921600
        ]

        print('Поддерживаемые скорости работы порта:')
        for i in range(len(baudrate_list)):
            print(f'| {i+1} -- {baudrate_list[i]}')

        port_baudrate = baudrate_list[int(input('\nВыберите скорость работы порта: ')) - 1]

        print('# -----------------------------------------\n')

        print(f'Выбран порт #{port_num}: {port_name}\n'
              f'Скорость работы порта: {port_baudrate}')

        self._port_name = port_name
        self._baudrate = port_baudrate

        self._cache_data['ComPort'] = {
            'port': {
                'name': self._port_name,
                'desc': self._ports[self._port_name]['desc'],
                'hwid': self._ports[self._port_name]['hwid'],
                'baudrate': port_baudrate
            }
        }
