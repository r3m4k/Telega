/** ****************************************************************************
 * @file    MessagePackage.hpp
 * @author  Романовский Роман
 * @brief   Формирование текстового пакета сообщения
 * @details Содержит класс MessagePackage, наследующий BasePackage, для упаковки
 *          строковых сообщений (подтверждения, ack, ошибки) в бинарный формат,
 *          соответствующий протоколу.
 **************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef MESSAGE_PACKAGE_HPP
#define MESSAGE_PACKAGE_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>
#include <string.h>

#include "BasePackage.hpp"

/* Defines -------------------------------------------------------------------*/

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------

namespace Packages{

    /**
     * @brief   Класс текстового пакета сообщения.
     * @details Наследует BasePackage. Хранит буфер фиксированной максимальной
     *          длины (MaxMsgLen) как поле объекта — время жизни буфера совпадает
     *          с временем жизни MessagePackage.
     *
     *          Формат пакета (все байты лежат в одном непрерывном буфере):
     *          - header[0..1]:  фиксированные байты HeaderFirstByte/HeaderSecondByte;
     *          - header[2]:     байт формата MessageFormat (0xCD);
     *          - header[3]:     длина data-секции (msg_size), записанная в конструкторе;
     *          - msg_text:      скопированный текст длиной msg_size;
     *          - control_sum:   младший байт модульной суммы всех предыдущих байт,
     *                           располагается СРАЗУ за msg_text по смещению
     *                           4 + msg_size. Остаток буфера до MaxMsgLen включительно
     *                           не используется и по UART не отправляется.
     *
     *          Поле len из BasePackage содержит фактическую длину пакета
     *          (4 + msg_size + 1), а не sizeof(внутреннего буфера).
     *
     * @note    Если переданный msg_size превышает MaxMsgLen, сообщение
     *          усекается до MaxMsgLen (truncate). Предварительная проверка
     *          длины — ответственность вызывающего кода, если важна точность.
     */
    class MessagePackage: public BasePackage{
        /**
         * @brief   Байт формата пакета.
         */
        static constexpr uint8_t MessageFormat = 0xCD;

        /**
         * @brief   Максимальная длина текста сообщения в байтах.
         */
        static constexpr uint8_t MaxMsgLen = 32;

        /**
         * @brief   Внутренний буфер пакета.
         * @details Суммарный размер: 4 (header) + MaxMsgLen + 1 (control_sum).
         *          Поле control_sum здесь — это "хвостовой слот" для самого
         *          длинного возможного сообщения; при более коротком msg_size
         *          реальная control_sum записывается не в это поле, а по
         *          смещению 4 + msg_size внутри буфера (см. описание класса).
         *          Формальное поле control_sum сохранено для корректного
         *          подсчёта размера буфера через sizeof(package_body_t).
         */
        #pragma pack(1)
        struct package_body_t
        {
            uint8_t header[4] = {HeaderFirstByte, HeaderSecondByte, MessageFormat, 0};
            uint8_t msg_text[MaxMsgLen] = {};
            uint8_t control_sum = 0;
        } package_body;
        #pragma pack()

    public:
        /**
         * @brief   Конструктор по умолчанию запрещён (требуются данные сообщения).
         */
        MessagePackage() = delete;

        /**
         * @brief   Конструктор с текстом сообщения.
         * @param   text        Указатель на содержимое сообщения (может указывать
         *                      на строковый литерал, const char*).
         * @param   msg_size    Длина сообщения в байтах (без учёта '\0').
         * @details Копирует текст в собственный буфер, заполняет header[3]
         *          длиной данных, рассчитывает контрольную сумму и располагает
         *          её сразу за скопированным текстом.
         *          Если msg_size > MaxMsgLen, сообщение усекается до MaxMsgLen.
         */
        MessagePackage(const char* text, size_t msg_size){

            // Ограничим длину сообщения максимально допустимой.
            if (msg_size > MaxMsgLen){
                msg_size = MaxMsgLen;
            }

            // Заголовочные поля 0..2 уже установлены при default-инициализации
            // структуры; заполним длину data-секции.
            package_body.header[3] = static_cast<uint8_t>(msg_size);

            // Скопируем текст сообщения в буфер.
            memcpy(package_body.msg_text, text, msg_size);

            // Установим поля базового класса. Фактическая длина пакета:
            // 4 байта header + msg_size байт текста + 1 байт control_sum.
            data_ptr = reinterpret_cast<uint8_t*>(&package_body);
            len      = static_cast<uint8_t>(4 + msg_size + 1);

            // Позиция контрольной суммы внутри буфера — сразу за текстом.
            // Предварительно обнулим этот слот, чтобы он корректно учёлся
            // в сумме (CountControlSum суммирует len-1 байт, и до его вызова
            // в слоте control_sum должен лежать 0).
            data_ptr[len - 1] = 0;
            data_ptr[len - 1] = CountControlSum();
        }

    private:
        /**
         * @brief   Вычисление контрольной суммы пакета.
         * @return  uint8_t   Младший байт суммы всех байт пакета,
         *                    кроме самого байта control_sum.
         * @details Проходит по первым (len - 1) байтам data_ptr,
         *          накапливает сумму в 16-битной переменной и возвращает
         *          младший байт.
         */
        uint8_t CountControlSum(){
            uint16_t crc = 0;
            // Исключаем последний байт (сам байт контрольной суммы)
            for (uint8_t i = 0; i < len - 1; i++){
                crc += data_ptr[i];
            }
            return static_cast<uint8_t>(crc);
        }
    };

} // namespace Packages

#endif /*   MESSAGE_PACKAGE_HPP   */