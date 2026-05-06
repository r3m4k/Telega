/** ****************************************************************************
 * @file    UsbPort.hpp
 * @brief   Класс для работы с виртуальным COM-портом (VCP) через USB.
 * @details Содержит реализацию UsbPort, которая использует декодер для
 *          обработки входящих сообщений и предоставляет методы для отправки
 *          пакетов и сообщений.
 **************************************************************************** */

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
#include "Messages.hpp"
#include "DecoderTelega.hpp"

/* Defines -------------------------------------------------------------------*/

/* Usings --------------------------------------------------------------------*/
/**
 * @brief   Тип декодера, используемый для обработки принятых байтов.
 * @details По умолчанию используется DecoderTelega из пространства имён Decoder.
 *          Может быть заменён на другой тип, удовлетворяющий концепту
 *          HasVoidByteProcessing.
 */
using UsbDecoder = Decoder::DecoderTelega;

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------
namespace STM_CppLib{
    namespace UsbPort
    {
            
    // -----------------------------------------------------------------
    /**
     * @brief   Концепт, проверяющий наличие метода byte_processing(uint8_t).
     * @details Требует, чтобы тип декодера имел метод
     *          void byte_processing(uint8_t). Используется для статической
     *          проверки совместимости декодера с классом Usart.
     */
    template<typename T>
    concept HasVoidByteProcessing = requires(T decoder, uint8_t bt){
        { decoder.byte_processing(bt) } -> std::same_as<void>;
    };

    // -----------------------------------------------------------------
    /**
     * @brief   Класс для управления виртуальным COM-портом (VCP).
     * @details Предоставляет инициализацию порта, отправку пакетов и сообщений,
     *          а также обработку входящих данных через декодер.
     */
    class UsbPort{
    
        static_assert(HasVoidByteProcessing<UsbDecoder>,
            "\n=== DECODER INTERFACE ERROR ===\n"
            "UsartDecoder type must provide: void byte_processing(uint8_t)\n"
            "===============================\n");

    private:
        UsbDecoder decoder;    ///< Декодер для обработки входящих сообщений
    
    public:
        /**
         * @brief   Конструктор по умолчанию.
         */
        UsbPort() = default;

        /**
         * @brief   Деструктор.
         */
        ~UsbPort() = default;

        /**
         * @brief   Инициализация COM-порта.
         * @details Выполняет сброс порта (VCP_ResetPort) и инициализацию VCP (VCP_Init).
         */
        void Init(){
            VCP_Init();         // Инициализация VCP
            VCP_ResetPort();    // Подтягиваем ножку D+ к нулю для правильной идентификации
        }

        /**
         * @brief   Отправка пакета данных через COM-порт.
         * @param   package   Ссылка на базовый пакет (BasePackage), содержащий данные и длину.
         */
        void SendPackage(Packages::BasePackage& package){
            CDC_Send_DATA(package.data_ptr, package.len);
        }

        /**
         * @brief   Отправка сообщения фиксированной длины через COM-порт.
         * @param   message   Ссылка на объект Message, содержащий массив байт.
         */
        void SendMessage(Messages::Message& message){
            CDC_Send_DATA(message.bytes_msg, message.msg_size);
        }
        
        /**
         * @brief   Обработка входящего сообщения (вызывается из callback USB).
         * @param   message   Ссылка на принятое сообщение.
         * @details Передаёт сообщение декодеру для дальнейшей обработки.
         */
        void EP3_OUT_Callback(Messages::Message& message){
            for(uint8_t i = 0; i < message.msg_size; i++){
                uint8_t bt = message.bytes_msg[i];
                decoder.byte_processing(bt);
            }
        }
    };

    } // namespace UsbPort
} // namespace STM_CppLib

#endif /*   COM_PORT_HPP   */