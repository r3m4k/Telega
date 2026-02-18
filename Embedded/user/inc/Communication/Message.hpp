/** ***************************************************************************
 * @file    Message.hpp
 * @author  Романовский Роман
 * @brief   Класс для работы с сообщениями фиксированной длины.
 * @details Предоставляет контейнер для хранения массива байт размером MaxMessageLength.
 *          Поддерживает создание из буфера, сравнение и сброс.
 *************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef MESSAGE_HPP
#define MESSAGE_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>
#include <string.h>

/* Defines -------------------------------------------------------------------*/
/**
 * @def     MaxMessageLength
 * @brief   Максимальная длина сообщения в байтах (должна совпадать с размером
 *          буфера, используемого в hw_config.c).
 */
#define MaxMessageLength      64

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------
namespace STM_CppLib{

    /**
     * @brief   Класс для описания сообщений длиной до MaxMessageLength байт.
     * @details Содержит массив байт фиксированного размера, который инициализируется
     *          нулями при создании. Предоставляет конструкторы, оператор сравнения
     *          и метод очистки.
     */
    class Message{
    public:
        uint8_t bytes_msg[MaxMessageLength] = {};   ///< Массив для хранения данных сообщения
        uint8_t msg_size = 0;                       ///< Реальный размер данных в сообщении

        /**
         * @brief   Конструктор по умолчанию.
         */
        Message() = default;

        /**
         * @brief   Конструктор, копирующий данные из внешнего буфера.
         * @param   buffer   Указатель на источник данных.
         * @param   size     Количество байт для копирования (не более MaxMessageLength).
         *                   По умолчанию копируется MaxMessageLength байт.
         */
        Message(const uint8_t *buffer, uint8_t size = MaxMessageLength){
            if (size > MaxMessageLength) size = MaxMessageLength;
            msg_size = size;
            memcpy(bytes_msg, buffer, size);
        }

        /**
         * @brief   Деструктор по умолчанию.
         */
        ~Message() = default;

        /**
         * @brief   Оператор копирования.
         * @param   other   Ссылка на другое сообщение.
         */
        Message& operator=(const Message& other) const {
            if (this != &other) {
                msg_size = other.msg_size;
                memcpy(bytes_msg, other.bytes_msg, msg_size);
            }
            return *this;
        }

        /**
         * @brief   Оператор сравнения двух сообщений.
         * @param   other   Ссылка на другое сообщение.
         */
        bool operator==(const Message& other) const {
            if (msg_size != other.msg_size) return false;
            return memcmp(bytes_msg, other.bytes_msg, msg_size) == 0;
        }

        /**
         * @brief   Очистка сообщения – заполняет весь массив нулями.
         */
        void clear() {
            memset(bytes_msg, 0, MaxMessageLength);
            msg_size = 0;
        }
    };

} // namespace STM_CppLib

#endif /*   MESSAGE_HPP   */