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
    concept HasVoidMessageProcessing = requires(Decoder decoder, STM_CppLib::Message& msg) {
        { decoder.message_processing(msg) } -> std::same_as<void>;
    };

    /**
     * @brief   Класс для управления виртуальным COM-портом (VCP).
     * @details Предоставляет инициализацию порта, отправку пакетов и сообщений,
     *          а также обработку входящих данных через декодер.
     */
    class ComPort{

        static_assert(HasVoidMessageProcessing,
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
        void SendPackage(const STM_Packages::BasePackage& package){
            CDC_Send_DATA(package.data_ptr, package.len);
        }

        /**
         * @brief   Отправка сообщения фиксированной длины через COM-порт.
         * @param   message   Ссылка на объект Message, содержащий массив байт.
         */
        void SendMessage(const Message& message){
            CDC_Send_DATA(message.bytes_msg, MessageLength);
        }

        /**
         * @brief   Обработка входящего сообщения (вызывается из callback USB).
         * @param   message   Ссылка на принятое сообщение.
         * @details Передаёт сообщение декодеру для дальнейшей обработки.
         */
        void EP3_OUT_Callback(STM_CppLib::Message& message){
            decoder.message_processing(message);
        }

        /**
         * @brief   Отправка предопределённого сообщения об ошибке.
         * @details Формирует сообщение с кодом ошибки и отправляет его через SendMessage.
         */
        void SendErrorMessage(){
            constexpr uint8_t ErrorMessage[MessageLength] = {0x7e, 0xe7, 0xff, 0xff, 0xff, 0x62, 0};
            SendMessage(Message(ErrorMessage));
        }

        /**
         * @brief   Отправка подтверждающего сообщения.
         * @details Формирует сообщение с кодом подтверждения и отправляет его через SendMessage.
         */
        void SendConfirmMessage(){
            constexpr uint8_t ConfirmMessage[MessageLength] = {0x7e, 0xe7, 0xff, 0xaa, 0xaa, 0xb8, 0};
            SendMessage(Message(ConfirmMessage));
        }
    };

    } // namespace ComPort
} // namespace STM_CppLib

#endif /*   COM_PORT_HPP   */