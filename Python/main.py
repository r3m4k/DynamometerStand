# System imports
import os
from datetime import datetime
from pathlib import Path

# External imports

# User imports
from decoding import DecoderProtocol, HX711Decoder, HX711Data
from byte_source import BytesSource, ReadError, ComPortSetting, FileSourceSetting
from plotting import Plotter, CanvasConfig, color_scheme
from frequency_analysis import FrequencyAnalyser
from utils import confirm_from_console

#############################################
# Константы для работы программы
#############################################

# Количество пакетов данных, по которым будет построен график
N = 5000

# Директория для сохранения полученных графиков
save_dir = Path(__file__).resolve().parent / 'results' / str(datetime.now().date())
save_dir.mkdir(parents=True, exist_ok=True)


#############################################
# Перенаправление данных в декодер
#############################################

print('# -----------------------------------------')

bytes_source: BytesSource
bytes_source_num = int(input('Выберите тип источника данных:\n'
                             '| 1. COM-порт\n'
                             '| 2. Записанный log файл\n'
                             '--> '))
print()
if bytes_source_num == 1:
    bytes_source = ComPortSetting().get_bytes_source()
elif bytes_source_num == 2:
    bytes_source = FileSourceSetting().get_bytes_source()
else:
    print('❌ Ошибка ввода')
    exit(1)


decoder: DecoderProtocol[dict[int, list[HX711Data]]] = HX711Decoder()

with bytes_source as bt_src:
    try:
        while decoder.data_len != N:
            decoder.byte_processing(bt_src.read_byte())
            print(f'\r⏳ Чтение данных...    #{decoder.data_len}/{N}', end="", flush=True)
        print()
        print('✅ Чтение данных завершено\n')

    except ReadError as err:
        print(f'Ошибка чтения пакета #{decoder.data_len}\n'
              f'Описание ошибки:\n {err}')
        print(f'Проводить анализ прочитанных данных?')

        if not confirm_from_console():
            exit(1)

print(decoder)

#############################################
# Сохранение данных в csv файл
#############################################

print('📥 Сохранение данных в csv файл')

csv_file = save_dir / 'Записанные данные.csv'
decoder.save_received_data(csv_file)

#############################################
# Завершение программы
#############################################

print('🎯 Успешное завершение программы')

# Откроем директорию сохранения в проводнике
os.startfile(save_dir)