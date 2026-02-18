/**
 * @file    ComPort.hpp
 * @brief   Класс для работы с виртуальным COM-портом (VCP) через USB.
 * @details Содержит реализацию ComPort, которая использует декодер для
 *          обработки входящих сообщений и предоставляет методы для отправки
 *          пакетов и сообщений.
 */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef COM_PORT_HPP
#define COM_PORT_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>
#include <string.h>
#include <concepts>

#include "VCP_F3.h"
#include "hw_config.h"
#include "BasePackage.hpp"
#include "Message.hpp"
#include "DecoderTelega.hpp"

/* Defines -------------------------------------------------------------------*/

/* Usings --------------------------------------------------------------------*/
/**
 * @brief   Тип декодера, используемый для обработки входящих сообщений.
 * @details По умолчанию используется DecoderTelega. Может быть заменён
 *          на другой тип, удовлетворяющий концепту HasVoidMessageProcessing.
 */
using Decoder = DecoderTelega;

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------
namespace STM_CppLib{
    namespace ComPort
    {
            
    /**
     * @brief   Концепт, проверяющий наличие метода message_processing(Message&).
     * @details Требует, чтобы тип Decoder имел метод
     *          void message_processing(STM_CppLib::Message&).
     *          Используется для статической проверки совместимости декодера
     *          с классом ComPort.
     */
    template<typename T>
    concept HasVoidMessageProcessing = requires(T decoder, STM_CppLib::Message& msg) {
        { decoder.message_processing(msg) } -> std::same_as<void>;
    };

    /**
     * @brief   Класс для управления виртуальным COM-портом (VCP).
     * @details Предоставляет инициализацию порта, отправку пакетов и сообщений,
     *          а также обработку входящих данных через декодер.
     */
    class ComPort{

        static_assert(HasVoidMessageProcessing<Decoder>,
            "\n=== DECODER INTERFACE ERROR ===\n"
            "Decoder type must provide: void message_processing(STM_CppLib::Message&)\n"
            "===============================\n");

    private:
        Decoder decoder;    ///< Декодер для обработки входящих сообщений

    public:
        /**
         * @brief   Конструктор по умолчанию.
         */
        ComPort() = default;

        /**
         * @brief   Деструктор.
         */
        ~ComPort() = default;

        /**
         * @brief   Инициализация COM-порта.
         * @details Выполняет сброс порта (VCP_ResetPort) и инициализацию VCP (VCP_Init).
         */
        void Init(){
            VCP_ResetPort();    // Подтягиваем ножку D+ к нулю для правильной идентификации
            VCP_Init();         // Инициализация VCP
        }

        /**
         * @brief   Отправка пакета данных через COM-порт.
         * @param   package   Ссылка на базовый пакет (BasePackage), содержащий данные и длину.
         */
        void SendPackage(STM_Packages::BasePackage& package){
            CDC_Send_DATA(package.data_ptr, package.len);
        }

        /**
         * @brief   Отправка сообщения фиксированной длины через COM-порт.
         * @param   message   Ссылка на объект Message, содержащий массив байт.
         */
        void SendMessage(Message& message){
            CDC_Send_DATA(message.bytes_msg, message.msg_size);
        }

        /**
         * @brief   Обработка входящего сообщения (вызывается из callback USB).
         * @param   message   Ссылка на принятое сообщение.
         * @details Передаёт сообщение декодеру для дальнейшей обработки.
         */
        void EP3_OUT_Callback(STM_CppLib::Message& message){
            decoder.message_processing(message);
        }
    };

    } // namespace ComPort
} // namespace STM_CppLib

#endif /*   COM_PORT_HPP   */