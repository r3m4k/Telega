from dev.com_port.decoding.telega_decoder import TelegaDecoder
from dev.com_port.decoding.package_examples import package_1, package_2, package_3, package_4

#########################################

decoder = TelegaDecoder()


def static_telega_decoder_test(package: list[bytes]):
    # Статическая проверка декодера
    print(
        f'{decoder._bytes_to_telega_data(package)}\n'
        f'Полученное значение контрольной суммы:   {package[-1]}\n'
        f'Вычисленное значение контрольной суммы:  {decoder._count_control_sum(package)}\n'
        f'{"✅ Успешно" if package[-1] == decoder._count_control_sum(package) else "❌ Ошибка"}\n'
    )

# -------------------------------------

def dynamic_telega_decoder_test(package: list[bytes]):
    for bt in package:
        decoder.byte_processing(bt)

    for i in range(len(decoder.received_data)):
        print(decoder.received_data[i])

# -------------------------------------

if __name__ == '__main__':
    package_bytes = [package_1, package_2]

    for _package in package_bytes:
        print('############################\n'
              f'Статическая проверка пакета #{package_bytes.index(_package) + 1}\n'
              '# --------------------------')
        static_telega_decoder_test(_package)

        print('############################\n'
              f'Динамическая проверка пакета #{package_bytes.index(_package) + 1}\n'
              '# --------------------------')
        dynamic_telega_decoder_test(_package)

    print('############################\n')
    print(decoder)
    print('############################')
