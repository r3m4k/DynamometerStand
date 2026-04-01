# Примеры заранее записанных пакетов данных

package_1 = [
    b'\xc8',
    b'\x8c',
    b'\x01',
    b'\x0a',
    b'\xe6',
    b'\x01',
    b'\x00',
    b'\x00',
    b'\x01',
    b'\x70',
    b'\x00',
    b'\x00',
    b'\x00',
    b'\x01',
    b'\xb8'
]

package_2 = [
    b'\xc8',
    b'\x8c',
    b'\x01',
    b'\x0a',
    b'\xe6',
    b'\x01',
    b'\x00',
    b'\x00',
    b'\x02',
    b'\x70',
    b'\x00',
    b'\x00',
    b'\x00',
    b'\x01',
    b'\xb9'
]

package_3 = [
    b'\xc8',
    b'\x8c',
    b'\x01',
    b'\x0a',
    b'\xf8',
    b'\x01',
    b'\x00',
    b'\x00',
    b'\x01',
    b'\x70',
    b'\x00',
    b'\x00',
    b'\x00',
    b'\x01',
    b'\xca'
]

package_4 = [
    b'\xc8',
    b'\x8c',
    b'\x01',
    b'\x0a',
    b'\xf8',
    b'\x01',
    b'\x00',
    b'\x00',
    b'\x02',
    b'\x70',
    b'\x00',
    b'\x00',
    b'\x00',
    b'\x01',
    b'\xcb'
]


# Функция для вывода в консоль пакета данных из строки
def str_to_package(package_string: str):
    str_bytes_list = package_string.split()

    for i in range(len(str_bytes_list)):
        if str_bytes_list[i] == '20':
            str_bytes_list[i] = '00'

        print(r"b'\x" + f"{str_bytes_list[i]}'", end='')

        if i != len(str_bytes_list) - 1:
            print(',')


# --------------------------------------------


if __name__ == '__main__':
    str_bytes = "fb 01 ff 0c 7e 28 20 20 32 20 20 20 43 90 75 3e 43 90 f5 bd 8c 3b 1f 41 93 ec 13 bc 88 4e 0e 3b b8 c6 24 3a 10 54 ce 3e 60 8d 69 40 cc cc 9c c0 d0 0f 49 40 a2  "
    str_to_package(str_bytes)
