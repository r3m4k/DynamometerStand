# def solve():
#     n_str, m_str = input().split()
#     n = int(n_str)
#     m = int(m_str)
#
#     a = input()
#     b = input()
#
#     min_dist = m
#     # Перебираем все возможные начала подстрок длины m
#     for i in range(n - m + 1):
#         # Считаем расстояние Хэмминга без создания промежуточной подстроки
#         dist = sum(a[i + j] != b[j] for j in range(m))
#         if dist < min_dist:
#             min_dist = dist
#             if min_dist == 0:          # Дальше искать не имеет смысла
#                 break
#
#     print(min_dist)


# def solve():
#     n = int(input())
#     stones = []
#     sumR = 0
#     sumB = 0
#
#     for _ in range(n):
#         color, weight = input().split()
#         weight = int(weight)
#         stones.append((color, weight))
#         if color == 'R':
#             sumR += weight
#         else:
#             sumB += weight
#
#     # Определяем доминирующий цвет и разницу
#     if sumR > sumB:
#         dominant = 'R'
#         diff = sumR - sumB
#         to_recolor = [w for c, w in stones if c == 'R']
#     else:
#         dominant = 'B'
#         diff = sumB - sumR
#         to_recolor = [w for c, w in stones if c == 'B']
#
#     to_recolor.sort()
#     target = diff / 2 + 1
#
#     if target <= 0:
#         print(0)
#         return
#
#     current = 0
#     total_weight = 0
#
#     for weight in to_recolor:
#         current += weight
#         total_weight += weight
#         if current > target:
#             print(total_weight)
#             return
#
#     print(-1)
#
# # Просто вызов функции
# # solve()
#
# import math
# def count_acute_triangles(n):
#     total = 0
#     for c in range(1, n + 1):
#         c2 = c * c
#         b_start = (c // 2) + 1
#         for b in range(b_start, c + 1):
#             a_min1 = c - b + 1
#             sq_diff = c2 - b * b
#             a_min2 = math.isqrt(sq_diff) + 1 if sq_diff >= 0 else 1
#             a_min = max(a_min1, a_min2)
#             if a_min <= b:
#                 total += b - a_min + 1
#     return total
#
# n = int(input())
# print(count_acute_triangles(n))



#
# # Считываем количество камней
# n = int(input())
#
# # Считываем данные о камнях: цвет и вес
# stones = []
# for _ in range(n):
#     color, weight = input().split()
#     weight = int(weight)
#     stones.append((color, weight))
#
# # Разделяем камни по цветам
# red_stones = [weight for color, weight in stones if color == 'R']
# blue_stones = [weight for color, weight in stones if color == 'B']
#
# # Считаем суммарный вес каждого цвета
# sum_red = sum(red_stones)
# sum_blue = sum(blue_stones)
#
# if sum_red > sum_blue:
#     red_stones.sort()
#     blue_stones.sort(reverse=True)
#     total_weight_to_change = 0
#     i = 0
#     while (sum_red >= sum_blue) and (i < len(red_stones)):
#         sum_red -= red_stones[i]
#         sum_blue += red_stones[i]
#         total_weight_to_change += red_stones[i]
#         i += 1
#
#     print(total_weight_to_change)
#
# # Если синий доминирует, то наоборот
# else:
#     blue_stones.sort()
#     red_stones.sort(reverse=True)
#     total_weight_to_change = 0
#     i = 0
#     while (sum_blue >= sum_red) and i < len(blue_stones):
#         sum_blue -= blue_stones[i]
#         sum_red += blue_stones[i]
#         total_weight_to_change += blue_stones[i]
#         i += 1
#
#     print(total_weight_to_change)
#
#
#
#
#
#






#
# if __name__ == "__main__":
#     solve()

# import numpy as np
# import matplotlib.pyplot as plt
#
# # Параметры сигнала
# fs = 1000 # Частота дискретизации, Гц
# t = np.arange(0, 1, 1/fs) # 1 секунда сигнала
#
# # Создаем сигнал с несколькими частотными компонентами
# components = [
#     (1.0, 5), # амплитуда 1.0, частота 5 Гц
#     (0.5, 50), # амплитуда 0.5, частота 50 Гц
#     (0.3, 120), # амплитуда 0.3, частота 120 Гц
# ]
#
# signal = np.zeros_like(t)
# for amplitude, freq in components:
#     signal += amplitude * np.sin(2 * np.pi * freq * t)
#
# # Добавляем шум
# signal += 0.2 * np.random.randn(len(t))
#
# # Выполняем БПФ
# spectrum = np.abs(np.fft.rfft(signal)) / len(signal)
# freqs = np.fft.rfftfreq(len(signal), 1/fs)
#
# # Визуализация
# plt.figure(figsize=(12, 8))
# plt.subplot(211)
# plt.plot(t, signal)
# plt.title('Временная область')
# plt.xlabel('Время (с)')
# plt.ylabel('Амплитуда')
#
# plt.subplot(212)
# plt.plot(freqs, spectrum)
# # plt.xlim([0, 150]) # Ограничиваем частотную ось для наглядности
# plt.title('Частотная область')
# plt.xlabel('Частота (Гц)')
# plt.ylabel('Амплитуда')
# plt.grid(True)
# plt.tight_layout()
# plt.show()
#
#
#
#
#
#
#
#
# # ---------------------------------------------------------------------
#
# # # Проверка реализации метода Уэлфорда для вычисления среднего и сигмы
# #
# # import numpy as np
# # import matplotlib.pyplot as plt
# #
# # file =  './results/2026-01-30/Записанные данные.csv'
# #
# # data = np.loadtxt(file, delimiter=' ', skiprows=1, dtype=str).T
# #
# # acc_z = np.char.replace(data[4], ',', '.').astype(float)
# #
# # counter = 0
# # mean_z = 0
# # sum_product = 0
# #
# # covariance_array = []
# #
# # def mean_std_Welford(val: float):
# #     global counter, mean_z, sum_product, covariance_array
# #
# #     counter += 1
# #     mean_z += (val - mean_z) / counter
# #     sum_product += (val - mean_z)**2
# #     covariance_array.append(sum_product / counter)
# #
# # for v in acc_z:
# #     mean_std_Welford(v)
# #
# # print(f'Истинное среднее значение:              {np.mean(acc_z)}\n'
# #       f'Среднее значение по методу Уэлфорда:    {mean_z}\n\n'
# #       f'Истинное значение дисперсии:    {np.std(acc_z)**2}\n'
# #       f'Дисперсия по методу Уэлфорда:   {sum_product/counter}')
# #
# # plt.plot(np.linspace(0, len(acc_z)-1, len(acc_z)), np.array(covariance_array) / np.abs(mean_z))
# # plt.show()










# Покажи 5 задание -- 8




# 6 номер? 3 нейронки дали 3 разных ответа)


# 31542










