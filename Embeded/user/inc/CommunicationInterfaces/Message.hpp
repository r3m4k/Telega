/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MESSAGE_HPP
#define __MESSAGE_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>
#include <string.h>

/* Defines -------------------------------------------------------------------*/
#define MessageLength      64      // Максимальная длина сообщения в байтах     // hw_config.c --> len(buffer) = 64

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------
// Класс для описания сообщений длиной до MessageLength байт
class Message{
public:
    // Массив для хранения полученного сообщения
    uint8_t bytes_msg[MessageLength];

    // Конструктор по умолчанию
    Message() {}

    // Конструктор с указателем на буфер длиной size
    Message(uint8_t *buffer, uint8_t size=MessageLength){
        memcpy(bytes_msg, buffer, size);
    }

    // Деструктор
    ~Message(){}

    // Оператор сравнения
    bool operator==(Message& other){
        return memcmp(bytes_msg, other.bytes_msg, MessageLength);
    }
};

#endif /*   __MESSAGE_HPP   */