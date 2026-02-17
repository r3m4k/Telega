/** ***************************************************************************
 * @file    Message.hpp
 * @author  Романовский Роман
 * @brief   Класс для работы с сообщениями фиксированной длины.
 * @details Предоставляет контейнер для хранения массива байт размером MessageLength.
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
 * @def     MessageLength
 * @brief   Максимальная длина сообщения в байтах (должна совпадать с размером
 *          буфера, используемого в hw_config.c).
 */
#define MessageLength      64

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------
namespace STM_CppLib{

    /**
     * @brief   Класс для описания сообщений длиной до MessageLength байт.
     * @details Содержит массив байт фиксированного размера, который инициализируется
     *          нулями при создании. Предоставляет конструкторы, оператор сравнения
     *          и метод очистки.
     */
    class Message{
    public:
        /**
         * @brief   Массив для хранения данных сообщения.
         */
        uint8_t bytes_msg[MessageLength] = {};

        /**
         * @brief   Конструктор по умолчанию.
         */
        Message() = default;

        /**
         * @brief   Конструктор, копирующий данные из внешнего буфера.
         * @param   buffer   Указатель на источник данных.
         * @param   size     Количество байт для копирования (не более MessageLength).
         *                   По умолчанию копируется MessageLength байт.
         * @warning Если size превышает MessageLength, произойдёт переполнение буфера.
         */
        Message(const uint8_t *buffer, uint8_t size = MessageLength){
            if (size > MessageLength) size = MessageLength;
            memcpy(bytes_msg, buffer, size);
        }

        /**
         * @brief   Деструктор.
         */
        ~Message() = default;

        /**
         * @brief   Оператор сравнения двух сообщений.
         * @param   other   Ссылка на другое сообщение.
         * @return  Результат memcmp: 0, если сообщения полностью идентичны;
         *          ненулевое значение в противном случае.
         */
        bool operator==(Message& other){
            return memcmp(bytes_msg, other.bytes_msg, MessageLength) == 0;
        }

        /**
         * @brief   Очистка сообщения – заполняет весь массив нулями.
         */
        void clear() {
            memset(bytes_msg, 0, MessageLength);
        }
    };

} // namespace STM_CppLib

#endif /*   MESSAGE_HPP   */