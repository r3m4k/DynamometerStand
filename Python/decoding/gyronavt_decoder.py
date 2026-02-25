# System imports
from enum import Enum

# External imports
import numpy as np

# User imports
from utils import float_to_csv_format
from .data_description import GyronavtData, GyronavtDataIndexes
from .package_examples import package_1, package_2, package_3, package_4
from .utils import bytes_to_float, bytes_to_uint32, bytes_to_triaxial

#############################################

# Стадии обработки данных из порта
class Stage(Enum):
    WantHeader = 1          # Ожидание заголовка посылки
    WantData = 2            # Ожидание данных посылки
    WantControlSum = 3      # Ожидание контрольной суммы

# -------------------------------------------

# Декодер посылок формата Гиронавт
class GyronavtDecoder:
    def __init__(self):
        self._stage: Stage = Stage.WantHeader
        self._header = [b'\xfb', b'\x01', b'\xff', b'\x0c']

        self.received_data: list[GyronavtData] = []     # Список данных, полученных от платы
        self._received_bytes: list[bytes] = []          # Список поступивших байтов

        self._data_bt_index = 0                         # Индекс байта данных в посылке
        self._package_size = 48                         # Количество байт данных в посылке

        self._num_correct_packages = 0                  # Количество пакетов, полученных без ошибок
        self._num_wrong_packages = 0                    # Количество пакетов, полученных с ошибками

    @property
    def data_len(self) -> int:
        return self._num_correct_packages

    def __str__(self):
        return (
            f'🔍 Информация о GyronavtDecoder:\n'
            f'| Количество корректно принятых пакетов данных:     {self._num_correct_packages} из {self._num_correct_packages + self._num_wrong_packages}\n'
            f'| Количество пакетов данных, полученных с ошибкой:  {self._num_wrong_packages} из {self._num_correct_packages + self._num_wrong_packages}\n'
            f'| Среднее абсолютное значение ускорения:                  {np.mean([np.sqrt(values.acc.x_coord**2 + values.acc.y_coord**2 + values.acc.z_coord**2) for values in self.received_data]):.8f} м/с**2\n'
            f'| Среднее абсолютное значение угловой скорости:           {np.mean([np.sqrt(values.gyro.x_coord**2 + values.gyro.y_coord**2 + values.gyro.z_coord**2) for values in self.received_data]):.9f} градус/с\n'
            f'| Среднее абсолютное значение магнитной напряженности:    {np.mean([np.sqrt(values.mag.x_coord**2 + values.mag.y_coord**2 + values.mag.z_coord**2) for values in self.received_data]):.9f} нТл\n'
        )

    def save_received_data(self, filename: str) -> None:
        with open(filename, 'w') as file:
            # Запишем заголовки в файл
            file.write('Index Time Acc_X Acc_Y Acc_Z Gyro_X Gyro_Y Gyro_Z Mag_X Mag_Y Mag_Z\n')

            # Запишем данные в файл
            for i in range(self.data_len):
                file.write(
                    f'{i+1} '
                    f'{self.received_data[i].time} '
                    f'{float_to_csv_format(self.received_data[i].acc.x_coord)} '
                    f'{float_to_csv_format(self.received_data[i].acc.y_coord)} '
                    f'{float_to_csv_format(self.received_data[i].acc.z_coord)} '
                    f'{float_to_csv_format(self.received_data[i].gyro.x_coord)} '
                    f'{float_to_csv_format(self.received_data[i].gyro.y_coord)} '
                    f'{float_to_csv_format(self.received_data[i].gyro.z_coord)} '
                    f'{float_to_csv_format(self.received_data[i].mag.x_coord)} '
                    f'{float_to_csv_format(self.received_data[i].mag.y_coord)} '
                    f'{float_to_csv_format(self.received_data[i].mag.z_coord)}\n'
                )


    def byte_processing(self, bt: bytes) -> None:
        """ Обработка поступившего байта """

        self._received_bytes.append(bt)
        # print(f'stage = {self._stage}       bt = {bt}')

        match self._stage:
            case Stage.WantHeader:
                if self._received_bytes[-4::] == self._header:
                    self._stage = Stage.WantData
                    # Отчистим self._received_bytes от возможных прошлых записанных байтов
                    self._received_bytes = self._header.copy()

            case Stage.WantData:
                # Добавим в self._received_bytes все байты данных
                if self._data_bt_index < self._package_size - 1:
                    self._data_bt_index += 1
                else:
                    self._stage = Stage.WantControlSum
                    self._data_bt_index = 0

            case Stage.WantControlSum:
                # Проверка контрольной суммы
                if bt == self._crc8(self._received_bytes):
                    self.received_data.append(self._bytes_to_gyronavt_data(self._received_bytes))
                    self._num_correct_packages += 1
                else:
                    self._num_wrong_packages += 1

                self._stage = Stage.WantHeader
                self._received_bytes = []

    @staticmethod
    def _crc8(data_bytes: list[bytes]) -> bytes:
        """ Вычисление контрольной суммы согласно документации """
        crc = 0xFF
        length = len(data_bytes)
        # Условие length-1 необходимо, чтобы не учитывать в расчёте контрольной суммы
        # не учитывать старое значение контрольной суммы
        for i in range(length - 1):
            crc ^= ord(data_bytes[i])
            for j in range(8):
                if crc & 0x80:  # crc & 0x80 ? (crc << 1) ^ 0x31 : crc << 1
                    crc = ((crc << 1) & 0xFF) ^ 0x31  # Обрезаем до 8 бит
                else:
                    crc = (crc << 1) & 0xFF  # Обрезаем до 8 бит

        return bytes([crc])

    @staticmethod
    def _bytes_to_gyronavt_data(byte_list: list[bytes]) -> GyronavtData:

        time = bytes_to_uint32(byte_list[GyronavtDataIndexes.time_index: GyronavtDataIndexes.time_index + 4])
        acc  = bytes_to_triaxial(byte_list[GyronavtDataIndexes.acc_index : GyronavtDataIndexes.acc_index + 12])
        gyro = bytes_to_triaxial(byte_list[GyronavtDataIndexes.gyro_index : GyronavtDataIndexes.gyro_index + 12])
        mag  = bytes_to_triaxial(byte_list[GyronavtDataIndexes.mag_index : GyronavtDataIndexes.mag_index + 12])
        bar  = bytes_to_float(byte_list[GyronavtDataIndexes.bar_index : GyronavtDataIndexes.bar_index + 4])

        return GyronavtData(time, acc, gyro, mag, bar)


#############################################

decoder = GyronavtDecoder()


def static_gyronavt_decoder_test(package: list[bytes]):
    # Статическая проверка декодера
    print(
        f'{GyronavtDecoder._bytes_to_gyronavt_data(package)}\n'
        f'Полученное значение контрольной суммы:   {package[-1]}\n'
        f'Вычисленное значение контрольной суммы:  {GyronavtDecoder._crc8(package)}\n'
        f'{"✅ Успешно" if package[-1] == GyronavtDecoder._crc8(package) else "❌ Ошибка"}\n'
    )

# -------------------------------------

def dynamic_gyronavt_decoder_test(package: list[bytes]):
    global decoder

    for bt in package:
        decoder.byte_processing(bt)

    for i in range(len(decoder.received_data)):
        print(decoder.received_data[i])

# -------------------------------------

if __name__ == '__main__':
    package_bytes = [package_1, package_2, package_3, package_4]

    for _package in package_bytes:
        print('############################\n'
              f'Статическая проверка пакета #{package_bytes.index(_package) + 1}\n'
              '# --------------------------')
        static_gyronavt_decoder_test(_package)

        print('############################\n'
              f'Динамическая проверка пакета #{package_bytes.index(_package) + 1}\n'
              '# --------------------------')
        dynamic_gyronavt_decoder_test(_package)

    print('############################\n')
    print(decoder)
    print('############################')
