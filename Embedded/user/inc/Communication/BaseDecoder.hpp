/** ***************************************************************************
 * @file    BaseDecoder.hpp
 * @author  Романовский Роман
 * @brief   Базовый CRTP-класс декодера байтового потока для STM32F30x
 *
 * @details Содержит шаблонный класс BaseDecoder<Derived>, реализующий
 *          универсальный конечный автомат разбора пакетов формата:
 *          - 2 байта заголовка (HeaderFirstByte, HeaderSecondByte)
 *          - 1 байт формата пакета
 *          - 1 байт длины поля данных
 *          - N байт данных
 *          - 1 байт контрольной суммы
 *
 *          Поведение, зависящее от конкретного протокола, вынесено в
 *          наследника через CRTP:
 *          - static constexpr HeaderFirstByte / HeaderSecondByte – маркеры;
 *          - get_decode_func(fmt) – выбор функции разбора по байту формата;
 *          - count_control_sum(len) – алгоритм контрольной суммы
 *            (имеется реализация по умолчанию – модульная сумма).
 *
 *          В сборке с макросом DEBUG дополнительно ведётся учёт
 *          количества корректных, некорректных и неизвестных пакетов.
 *************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef BASE_DECODER_HPP
#define BASE_DECODER_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

#include "main.h"
#include "Messages.hpp"

/* Defines -------------------------------------------------------------------*/

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------

namespace Decoder{

    /**
     * @brief   Тип функции декодирования полученного пакета.
     * @details Принимает ссылку на собранное сообщение и выполняет
     *          специфичные для формата действия (передача в менеджер команд,
     *          обработку телеметрии и т.п.). Возвращаемое значение не требуется.
     */
    using DecodeFunc = void (*)(const Messages::Message&);

    /**
     * @brief   Состояния конечного автомата разбора пакета.
     */
    enum class DecoderStages{
        WantHeader,             ///< Ожидание заголовка (скользящее окно из последних 2 байт)
        WantFormat,             ///< Ожидание байта формата пакета
        WantLength,             ///< Ожидание байта длины поля данных
        WantData,               ///< Ожидание заданного количества байт данных
        WantControlSum          ///< Ожидание байта контрольной суммы
    };

    // -------------------------------------------------------------------------

    /**
     * @brief   Шаблонный базовый класс декодера (CRTP).
     * @tparam  Derived   Класс-наследник, конкретизирующий протокол.
     *
     * @details Наследник должен предоставить:
     *          - static constexpr uint8_t HeaderFirstByte – первый байт заголовка;
     *          - static constexpr uint8_t HeaderSecondByte – второй байт заголовка;
     *          - DecodeFunc get_decode_func(uint8_t fmt) – выбор функции
     *            разбора по байту формата. Возвращает nullptr, если формат
     *            неизвестен.
     *          Наследник может переопределить:
     *          - uint8_t count_control_sum() const – алгоритм контрольной суммы.
     *            Вызывается в стадии WantControlSum, когда CRC-байт уже
     *            записан в current_message последним. Реализация по умолчанию –
     *            младший байт модульной суммы всех байт пакета, кроме
     *            последнего (CRC).
     *
     * @note    Метод byte_processing(uint8_t) предполагается вызывать
     *          из обработчика прерывания USART, синхронно с приходом каждого
     *          байта. Внутри не выполняется блокирующих операций.
     */
    template<class Derived>
    class BaseDecoder{

    protected:
        Messages::SizedMessage<VCP_BUFFER_SIZE> current_message;   ///< Текущее собираемое сообщение
        DecoderStages decode_stage = DecoderStages::WantHeader;     ///< Текущее состояние автомата
        
        DecodeFunc decode_func  = nullptr;      ///< Функция декодирования текущего пакета
        uint8_t byte_index = 0;                 ///< Индекс следующего байта в current_message

        /// Скользящее окно из двух последних принятых байт в стадии WantHeader.
        /// Старший байт – предыдущий принятый, младший – самый свежий.
        uint16_t last_header_bytes = 0;

        uint8_t data_len   = 0;     ///< Ожидаемая длина поля данных
        uint8_t data_index = 0;     ///< Текущий индекс в поле данных

    #ifdef DEBUG
        /// Счётчик пакетов, принятых с корректной контрольной суммой
        uint16_t num_correct_packages = 0;
        /// Счётчик пакетов с ошибкой контрольной суммы
        uint16_t num_wrong_packages   = 0;
        /// Счётчик обнаруженных неизвестных форматов
        uint16_t num_unknown_formats = 0;
    #endif  /* DEBUG */

    public:
        /**
         * @brief   Конструктор по умолчанию.
         */
        BaseDecoder() = default;

        /**
         * @brief   Деструктор по умолчанию.
         */
        ~BaseDecoder() = default;

        /**
         * @brief   Обработка одного байта входящего потока.
         * @param   bt   Очередной принятый байт.
         * @details Реализует общий для всех декодеров конечный автомат.
         *          Поведение, зависящее от протокола, делегируется
         *          наследнику через CRTP.
         */
        void byte_processing(uint8_t bt){
            // Сохраняем каждый принятый байт в current_message до разбора.
            store_byte(bt);

            switch (decode_stage)
            {
            case DecoderStages::WantHeader: {
                // Сдвигаем скользящее окно последних 2 байт
                last_header_bytes = static_cast<uint16_t>((last_header_bytes << 8) | bt);

                constexpr uint16_t expected_header = 
                    (static_cast<uint16_t>(Derived::HeaderFirstByte) << 8) | Derived::HeaderSecondByte;

                if (last_header_bytes == expected_header){
                    // Заголовок собран – стартуем новый пакет с обоих байт, отбрасывая накопленный буфер
                    reset_message();
                    store_byte(Derived::HeaderFirstByte);
                    store_byte(Derived::HeaderSecondByte);
                    decode_stage = DecoderStages::WantFormat;
                    last_header_bytes = 0;
                }
                else{
                    // Сбрасываем буфер, чтобы мусорные байты не накапливались в current_message.
                    reset_message();
                }
                break;
            }

            case DecoderStages::WantFormat:
                decode_func = static_cast<Derived*>(this)->get_decode_func(bt);
                if (decode_func != nullptr){
                    decode_stage = DecoderStages::WantLength;
                }
                else{
                    decode_stage = DecoderStages::WantHeader;
                    last_header_bytes = 0;
                #ifdef DEBUG
                    num_unknown_formats++;
                #endif  /* DEBUG */
                }
                break;

            case DecoderStages::WantLength:
                data_len = bt;
                data_index = 0;

                // Если длина данных равна нулю, сразу переходим к контрольной сумме
                if (data_len == 0){
                    decode_stage = DecoderStages::WantControlSum;
                }
                else{   decode_stage = DecoderStages::WantData;   }
                break;

            case DecoderStages::WantData:
                data_index++;

                if (data_index == data_len){
                    decode_stage = DecoderStages::WantControlSum;
                }
                break;

            case DecoderStages::WantControlSum:
                if (bt == static_cast<Derived*>(this)->count_control_sum()){
                    decode_func(current_message);
                #ifdef DEBUG
                    num_correct_packages++;
                #endif  /* DEBUG */
                }
                else{
                #ifdef DEBUG
                    num_wrong_packages++;
                #endif  /* DEBUG */
                }

                decode_stage = DecoderStages::WantHeader;
                last_header_bytes = 0;
                break;
            }
        }

        /**
         * @brief   Вычисляет контрольную сумму пакета (реализация по умолчанию).
         * @return  uint8_t   Младший байт суммы всех байт current_message,
         *                    кроме последнего (самого CRC-байта).
         * @details Предполагается вызов в стадии WantControlSum, когда
         *          CRC-байт уже записан в current_message последним
         *          (msg_size включает CRC). Наследник может скрыть этот
         *          метод собственной реализацией с другим алгоритмом,
         *          сохранив сигнатуру.
         */
        uint8_t count_control_sum() const {
            uint16_t sum = 0;
            // При вычислении контрольной суммы не учитываем последний байт сообщения,
            // в котором сохранена полученная контрольная сумма
            for (uint8_t i = 0; i < current_message.msg_size - 1; i++){
                sum += current_message.bytes_msg[i];
            }
            return static_cast<uint8_t>(sum);
        }

    protected:
        /**
         * @brief   Сохраняет байт в текущее сообщение.
         * @param   bt   Сохраняемый байт.
         * @details Добавляет байт во внутренний буфер current_message
         *          по индексу byte_index, инкрементирует индекс и
         *          обновляет фактический размер сообщения.
         */
        void store_byte(uint8_t bt){
            if (byte_index < VCP_BUFFER_SIZE){
                current_message.bytes_msg[byte_index++] = bt;
                current_message.msg_size = byte_index;
            }
        }

        /**
         * @brief   Сброс текущего сообщения.
         */
        void reset_message(){
            current_message.reset();
            byte_index = 0;
        }
    };

} // namespace Decoder

#endif /*   BASE_DECODER_HPP   */