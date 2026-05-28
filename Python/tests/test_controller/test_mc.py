# System imports

# External imports

# User imports
from decoding import HX711Decoder
from byte_source import ReadError
from byte_source.com_port import ComPortSetting, ComPortHX711
from async_mc_controller.byte_source.com_port.packet_builders import PacketBuilderHX711Text


#############################################
# Утилиты тестирования
#############################################

def _wait_message(com_port: ComPortHX711, decoder: HX711Decoder) -> str | None:
    """Читает байты из COM-порта до прихода сообщения от МК и возвращает его.

    Извлекает (pop) сообщение из `decoder.received_messages`, чтобы
    последующие вызовы ждали действительно новое сообщение, а не хватали
    предыдущее. Прерывается при ошибке чтения (в т. ч. таймауте).

    Args:
        com_port (ComPortHX711): Открытый COM-порт.
        decoder (HX711Decoder):  Декодер, в который скармливаются байты.

    Returns:
        str | None: Принятое сообщение от МК или None при ошибке чтения.
    """
    try:
        while not decoder.received_messages:
            decoder.byte_processing(com_port.read_byte())
        return decoder.received_messages.pop(0)
    except ReadError as err:
        print(f'❌ Ошибка чтения: {err}')
        return None


#############################################
# Тесты
#############################################

def test_handshake(setting: ComPortSetting) -> bool:
    """Проверяет, что МК отвечает на handshake-команду строкой IMU_STM32_ACK."""
    print('\n# --- test_handshake ---')
    com_port = setting.get_bytes_source()
    decoder = HX711Decoder()

    with com_port:
        com_port.send_command(com_port._init_handshake_command)
        message = _wait_message(com_port, decoder)

    if message == decoder._handshake_ack:
        print(f'✅ Получен ожидаемый ACK: "{message}"')
        return True
    print(f'❌ Ожидалось "{decoder._handshake_ack}", получено "{message}"')
    return False

# ---------------------------------------------

def test_unknown_command(setting: ComPortSetting) -> bool:
    """Проверяет, что МК отвечает UNKNOWN_COMMAND на несуществующую команду."""
    print('\n# --- test_unknown_command ---')
    com_port = setting.get_bytes_source()
    decoder = HX711Decoder()

    garbage_command = PacketBuilderHX711Text.build_text_command('GARBAGE_REQ')

    with com_port:
        com_port.send_command(garbage_command)
        message = _wait_message(com_port, decoder)

    if message == decoder._command_rejected_msg:
        print(f'✅ Получен ожидаемый ответ: "{message}"')
        return True
    print(f'❌ Ожидалось "{decoder._command_rejected_msg}", получено "{message}"')
    return False

# ---------------------------------------------

def test_heartbeat(setting: ComPortSetting) -> bool:
    """Проверяет, что МК отвечает на heartbeat-команду строкой IMU_STM32_ALIVE."""
    print('\n# --- test_heartbeat ---')
    com_port = setting.get_bytes_source()
    decoder = HX711Decoder()

    with com_port:
        com_port.send_command(com_port._heartbeat_command)
        message = _wait_message(com_port, decoder)

    if message == decoder._heartbeat_ack:
        print(f'✅ Получен ожидаемый ACK: "{message}"')
        return True
    print(f'❌ Ожидалось "{decoder._heartbeat_ack}", получено "{message}"')
    return False

# ---------------------------------------------

def _wait_data(com_port: ComPortHX711, decoder: HX711Decoder, n: int) -> bool:
    """Читает байты из COM-порта, пока декодер не наберёт `n` IMU-пакетов.

    Args:
        com_port (ComPortHX711): Открытый COM-порт.
        decoder (HX711Decoder):  Декодер, в который скармливаются байты.
        n (int):               Требуемое количество корректно принятых пакетов.

    Returns:
        bool: True, если набрали `n` пакетов; False при ошибке чтения.
    """
    try:
        while decoder.data_len < n:
            decoder.byte_processing(com_port.read_byte())
        return True
    except ReadError as err:
        print(f'❌ Ошибка чтения данных (получено {decoder.data_len}/{n}): {err}')
        return False

# ---------------------------------------------



def test_measure_then_foo(setting: ComPortSetting) -> bool:
    """Проверяет полный цикл переключения режимов МК.

    Сценарий:
        1. set_measure → ждём CONFIRM_RECEIVED_COMMAND.
        2. Читаем поток до накопления N_PACKAGES IMU-пакетов.
        3. set_foo → ждём второй CONFIRM_RECEIVED_COMMAND.

    Тест считается пройденным, если все три шага успешны.
    """
    # Сколько IMU-пакетов считаем достаточным, чтобы признать поток запущенным
    N_PACKAGES = 500

    print('\n# --- test_measure_then_foo ---')
    com_port = setting.get_bytes_source()
    decoder = HX711Decoder()

    with com_port:
        # Шаг 1: запускаем измерение, ждём ACK
        com_port.send_command(com_port._set_measure_stage_command)
        ack1 = _wait_message(com_port, decoder)
        if ack1 != decoder._command_ack:
            print(f'❌ Шаг 1 (set_measure ACK): ожидалось "{decoder._command_ack}", получено "{ack1}"')
            return False
        print(f'✅ Шаг 1: получен ACK на set_measure')

        # Шаг 2: ждём поток данных
        if not _wait_data(com_port, decoder, N_PACKAGES):
            return False
        print(f'✅ Шаг 2: принято {decoder.data_len} IMU-пакетов')

        # Шаг 3: останавливаем измерение, ждём второй ACK
        com_port.send_command(com_port._set_foo_stage_command)
        ack2 = _wait_message(com_port, decoder)
        if ack2 != decoder._command_ack:
            print(f'❌ Шаг 3 (set_foo ACK): ожидалось "{decoder._command_ack}", получено "{ack2}"')
            return False
        print(f'✅ Шаг 3: получен ACK на set_foo')

    print(decoder)

    return True

# ---------------------------------------------

def test_full_cycle(setting: ComPortSetting) -> bool:
    """Полный цикл взаимодействия с МК.

    Сценарий:
        1. Handshake → IMU_STM32_ACK.
        2. set_measure → CONFIRM_RECEIVED_COMMAND.
        3. Чтение потока до 500 IMU-пакетов.
        4. heartbeat → IMU_STM32_ALIVE (ACK атомарно вклинивается между IMU-пакетами).
        5. Чтение потока до 1000 IMU-пакетов суммарно.
        6. set_foo → CONFIRM_RECEIVED_COMMAND.

    Тест считается пройденным, если все шаги отработали успешно.
    Битые IMU-пакеты (`_num_wrong_packages`) не учитываются — как в main.py.
    """
    print('\n# --- test_full_cycle ---')
    com_port = setting.get_bytes_source()
    decoder = HX711Decoder()

    with com_port:
        # Шаг 1: handshake
        com_port.send_command(com_port._init_handshake_command)
        ack = _wait_message(com_port, decoder)
        if ack != decoder._handshake_ack:
            print(f'❌ Шаг 1 (handshake): ожидалось "{decoder._handshake_ack}", получено "{ack}"')
            return False
        print(f'✅ Шаг 1: handshake подтверждён')

        # Шаг 2: запуск измерения
        com_port.send_command(com_port._set_measure_stage_command)
        ack = _wait_message(com_port, decoder)
        if ack != decoder._command_ack:
            print(f'❌ Шаг 2 (set_measure): ожидалось "{decoder._command_ack}", получено "{ack}"')
            return False
        print(f'✅ Шаг 2: получен ACK на set_measure')

        # Шаг 3: первая партия данных
        if not _wait_data(com_port, decoder, 500):
            return False
        print(f'✅ Шаг 3: принято {decoder.data_len} IMU-пакетов')

        # Шаг 4: heartbeat посреди потока
        com_port.send_command(com_port._heartbeat_command)
        ack = _wait_message(com_port, decoder)
        if ack != decoder._heartbeat_ack:
            print(f'❌ Шаг 4 (heartbeat): ожидалось "{decoder._heartbeat_ack}", получено "{ack}"')
            return False
        print(f'✅ Шаг 4: heartbeat подтверждён')

        # Шаг 5: вторая партия данных (общий счётчик до 1000)
        if not _wait_data(com_port, decoder, 1000):
            return False
        print(f'✅ Шаг 5: принято {decoder.data_len} IMU-пакетов суммарно')

        # Шаг 6: остановка измерения
        com_port.send_command(com_port._set_foo_stage_command)
        ack = _wait_message(com_port, decoder)
        if ack != decoder._command_ack:
            print(f'❌ Шаг 6 (set_foo): ожидалось "{decoder._command_ack}", получено "{ack}"')
            return False
        print(f'✅ Шаг 6: получен ACK на set_foo')

    return True

# ---------------------------------------------

def run_tests() -> None:
    setting = ComPortSetting()

    tests = [
        test_handshake,
        test_unknown_command,
        test_heartbeat,
        test_measure_then_foo,
        test_full_cycle,
    ]

    results: dict[str, bool] = {}
    for test in tests:
        results[test.__name__] = test(setting)

    # Итоговая сводка
    print('\n# =========================================')
    print('# Итоги тестирования')
    print('# =========================================')
    for name, ok in results.items():
        mark = '✅' if ok else '❌'
        print(f'| {mark} {name}')
    passed = sum(results.values())
    total = len(results)
    print(f'# -----------------------------------------')
    print(f'| Пройдено: {passed} из {total}')
    print('# =========================================')

# ---------------------------------------------

if __name__ == "__main__":
    run_tests()