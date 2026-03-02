# System imports
import os
from datetime import datetime

# External imports
import numpy as np
from serial import SerialException

# User imports
from decoding import DecoderProtocol, GyronavtDecoder, GyronavtData
from byte_source import BytesSource, ComPortSetting, FileSourceSetting
from plotting import Plotter, CanvasConfig, color_scheme
from frequency_analysis import FrequencyAnalyser
from utils import float_to_csv_format, confirm_from_console

#############################################
# Константы для работы программы
#############################################

# Количество пакетов данных, по которым будет построен график
N = 5000

# Директория для сохранения полученных графиков
save_dir = './results'

try:
    os.mkdir(f'{save_dir}')
except FileExistsError:
    pass

try:
    os.mkdir(f'{save_dir}/{str(datetime.now().date())}')
except FileExistsError:
    pass
except Exception as err:
    print(err)
    exit(1)

save_dir += f'/{str(datetime.now().date())}'
save_dir = os.path.normpath(save_dir)


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


decoder: DecoderProtocol[GyronavtData] = GyronavtDecoder()

with bytes_source as bt_src:
    try:
        while decoder.data_len != N:
            decoder.byte_processing(bt_src.read_byte())
            print(f'\r⏳ Чтение данных...    #{len(decoder.received_data)}/{N}', end="", flush=True)
        print()
        print('✅ Чтение данных завершено\n')

    except (EOFError, SerialException) as err:
        print(f'Ошибка чтения пакета #{decoder.data_len}\n'
              f'Описание ошибки:\n {err}')
        print(f'Проводить анализ прочитанных данных?')

        if not confirm_from_console():
            exit(1)

print(decoder)


#############################################
# Построение графиков величин и их распределение
#############################################

canvas_config = CanvasConfig()

canvas_config.n_rows = 3; canvas_config.n_cols = 2
canvas_config.ax_kwargs['width_ratios'] = [3, 1]

data_len = decoder.data_len
canvas_config.x_data = (np.array([decoder.received_data[i].time for i in range(data_len)]) - decoder.received_data[0].time) / 400

# -------------------------------------
# Построение графиков ускорений
canvas_config.y_data = [
    np.array([decoder.received_data[i].acc.x_coord for i in range(data_len)]),
    np.array([decoder.received_data[i].acc.y_coord for i in range(data_len)]),
    np.array([decoder.received_data[i].acc.z_coord for i in range(data_len)])
]

canvas_config.suptitle = f'Анализ ускорений по осям'
canvas_config.color_names = [color_scheme['RGB_classic']['X'],
                             color_scheme['RGB_classic']['Y'],
                             color_scheme['RGB_classic']['Z']]

canvas_config.dark_color_names = [color_scheme['RGB_dark']['X'],
                                  color_scheme['RGB_dark']['Y'],
                                  color_scheme['RGB_dark']['Z']]

canvas_config.y_label = [f'Acc_{coord}, м/с**2' for coord in ['X', 'Y', 'Z']]

canvas_config.annotation = [
    f'Mean Acc_X = {np.mean(canvas_config.y_data[0]).round(6)}',
    f'Mean Acc_Y = {np.mean(canvas_config.y_data[1]).round(6)}',
    f'Mean Acc_Z = {np.mean(canvas_config.y_data[2]).round(6)}'
]

plotter_Acc = Plotter(canvas_config)
plotter_Acc.plotting_3d_static()

# -------------------------------------
# Построение графиков угловых скоростей
canvas_config.y_data = [
    np.array([decoder.received_data[i].gyro.x_coord for i in range(data_len)]),
    np.array([decoder.received_data[i].gyro.y_coord for i in range(data_len)]),
    np.array([decoder.received_data[i].gyro.z_coord for i in range(data_len)])
]

canvas_config.suptitle = f'Анализ угловых скоростей'

canvas_config.color_names = [color_scheme['COP_classic']['X'],
                             color_scheme['COP_classic']['Y'],
                             color_scheme['COP_classic']['Z']]

canvas_config.dark_color_names = [color_scheme['COP_dark']['X'],
                                  color_scheme['COP_dark']['Y'],
                                  color_scheme['COP_dark']['Z']]

canvas_config.y_label = [f'Gyro_{coord}, градус/с' for coord in ['X', 'Y', 'Z']]

canvas_config.annotation = [
    f'Mean Gyro_X = {np.mean(canvas_config.y_data[0]).round(6)}',
    f'Mean Gyro_Y = {np.mean(canvas_config.y_data[1]).round(6)}',
    f'Mean Gyro_Z = {np.mean(canvas_config.y_data[2]).round(6)}'
]

plotter_Gyro = Plotter(canvas_config)
plotter_Gyro.plotting_3d_static()


# -------------------------------------
# Построение графиков магнитной напряжённости

canvas_config.y_data = [
    np.array([decoder.received_data[i].mag.x_coord for i in range(data_len)]),
    np.array([decoder.received_data[i].mag.y_coord for i in range(data_len)]),
    np.array([decoder.received_data[i].mag.z_coord for i in range(data_len)])
]

canvas_config.suptitle = f'Анализ напряжённости магнитного поля'

canvas_config.color_names = [color_scheme['RGB_light']['X'],
                             color_scheme['RGB_light']['Y'],
                             color_scheme['RGB_light']['Z']]

canvas_config.dark_color_names = [color_scheme['COP_light']['X'],
                                  color_scheme['COP_light']['Y'],
                                  color_scheme['COP_light']['Z']]

canvas_config.y_label = [f'Mag_{coord}, нТл' for coord in ['X', 'Y', 'Z']]

canvas_config.annotation = [
    f'Mean Mag_X = {np.mean(canvas_config.y_data[0]).round(6)}',
    f'Mean Mag_Y = {np.mean(canvas_config.y_data[1]).round(6)}',
    f'Mean Mag_Z = {np.mean(canvas_config.y_data[2]).round(6)}'
]

plotter_Mag = Plotter(canvas_config)
plotter_Mag.plotting_3d_static()

# -------------------------------------

print('💾 Сохранение графиков...')

plotter_Acc.save(f'{save_dir}/acc.png')
plotter_Gyro.save(f'{save_dir}/gyro.png')
plotter_Mag.save(f'{save_dir}/mag.png')


#############################################
# Анализ спектральной плотности
#############################################

print('🤖 Проведение спектрального анализа')

sample_rate = 400   # Используемая частота дискретизации для частотного анализа
data_rate = 400     # Частота поступления данных (априорная информация)

# Массив данных времени (в секундах)
time_array = (np.array([decoder.received_data[i].time for i in range(data_len)]) - decoder.received_data[0].time) / data_rate

# Построим спектральную плотность для данных с акселерометра
abs_acc = np.array([np.sqrt(decoder.received_data[i].acc.x_coord**2 +
                            decoder.received_data[i].acc.y_coord**2 +
                            decoder.received_data[i].acc.z_coord**2) for i in range(data_len)])

analyser = FrequencyAnalyser(abs_acc, time_array, sample_rate)
analyser.visualisation(suptitle='Частотный анализ данных акселерометра',
                       time_color=color_scheme['ABS_values_classic']['Acc'],
                       freq_color=color_scheme['ABS_values_dark']['Acc'])
analyser.canvas.save_figure(f'{save_dir}/acc_freq_analysis.png')

# Построим спектральную плотность для данных с гироскопа
abs_gyro = np.array([np.sqrt(decoder.received_data[i].gyro.x_coord**2 +
                             decoder.received_data[i].gyro.y_coord**2 +
                             decoder.received_data[i].gyro.z_coord**2) for i in range(data_len)])

analyser = FrequencyAnalyser(abs_gyro, time_array, sample_rate)
analyser.visualisation(suptitle='Частотный анализ данных гироскопа',
                       time_color=color_scheme['ABS_values_classic']['Gyro'],
                       freq_color=color_scheme['ABS_values_dark']['Gyro'])
analyser.canvas.save_figure(f'{save_dir}/gyro_freq_analysis.png')

# Построим спектральную плотность для данных с магнитометра
abs_mag = np.array([np.sqrt(decoder.received_data[i].mag.x_coord**2 +
                            decoder.received_data[i].mag.y_coord**2 +
                            decoder.received_data[i].mag.z_coord**2) for i in range(data_len)])

analyser = FrequencyAnalyser(abs_mag, time_array, sample_rate)
analyser.visualisation(suptitle='Частотный анализ данных магнитометра',
                       time_color=color_scheme['ABS_values_classic']['Mag'],
                       freq_color=color_scheme['ABS_values_dark']['Mag'])
analyser.canvas.save_figure(f'{save_dir}/mag_freq_analysis.png')


#############################################
# Сохранение данных в csv файл
#############################################

print('📥 Сохранение данных в csv файл')

csv_file = f'{save_dir}/Записанные данные.csv'
decoder.save_received_data(csv_file)

#############################################
# Завершение программы
#############################################

print('🎯 Успешное завершение программы')

# Откроем директорию сохранения в проводнике
os.startfile(save_dir)