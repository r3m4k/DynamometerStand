from pprint import pformat
from decoding import HX711Decoder

from tests.test_hx711_decoder.package_example import package_1, package_2, package_3, package_4

def static_decoder_testing(decoder: HX711Decoder, package: list[bytes]):
    decoder._bytes_to_hx711_data(package)
    print(
        f'{pformat(decoder.received_data)}\n'
        f'Полученное значение контрольной суммы:   {package[-1]}\n'
        f'Вычисленное значение контрольной суммы:  {decoder._count_control_sum(package)}\n'
        f'{"✅ Успешно" if package[-1] == decoder._count_control_sum(package) else "❌ Ошибка"}\n'
    )

# -------------------------------------

def dynamic_decoder_testing(decoder: HX711Decoder, package: list[bytes]):
    for bt in package:
        decoder.byte_processing(bt)
    print(pformat(decoder.received_data))
    print()

# -------------------------------------

if __name__ == "__main__":
    package_bytes = [package_1, package_2, package_3, package_4]
    static_decoder = HX711Decoder()
    dynamic_decoder = HX711Decoder()

    for p in package_bytes:
        print('############################\n'
              f'Статическая проверка пакета #{package_bytes.index(p) + 1}\n'
              '# --------------------------')
        static_decoder_testing(static_decoder, p)

    for p in package_bytes:
        print('############################\n'
              f'Динамическая проверка пакета #{package_bytes.index(p) + 1}\n'
              '# --------------------------')
        dynamic_decoder_testing(dynamic_decoder, p)

    print(f'static_decoder:\n{static_decoder}')
    print(f'dynamic_decoder:\n{dynamic_decoder}')
    dynamic_decoder.save_received_data('./results/test_saving.csv')
