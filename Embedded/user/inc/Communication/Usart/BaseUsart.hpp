/** ***************************************************************************
 * @file    BaseUsart.hpp
 * @author  Романовский Роман
 * @brief   Базовый класс для аппаратного управления USART на STM32F30x
 *
 * @details Содержит:
 *          - базовый класс BaseUsart, инкапсулирующий указатель на
 *            регистровую структуру USARTx и предоставляющий методы
 *            базовой инициализации, запуска, останова и отправки данных;
 *          - данный класс не зависит от шаблонных параметров, поэтому
 *            его код генерируется один раз для всего проекта (экономия flash).
 *          Не предназначен для прямого использования – служит основой
 *          для шаблонного класса-наследника Usart.
 *************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef BASE_USART_HPP
#define BASE_USART_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

#include "main.h"
#include "stm32f30x.h"
#include "stm32f30x_usart.h"

#include "Consts.hpp"
#include "BasePackage.hpp"
#include "Messages.hpp"
#include "UsartConfig.hpp"

/* Defines -------------------------------------------------------------------*/

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------

namespace STM_CppLib{
    namespace STM_Usart{

    // -------------------------------------------------------------------------
    /**
     * @brief   Базовый класс для аппаратного управления USART.
     * @details Инкапсулирует указатель на регистровую структуру USART_TypeDef
     *          и предоставляет методы инициализации регистров, запуска/останова
     *          модуля и отправки данных. Не предназначен для прямого
     *          использования – служит основой для класса-наследника Usart.
     */
    class BaseUsart{
    protected:
        /**
         * @brief   Указатель на регистровую структуру USART.
         */
        USART_TypeDef* USARTx;

    public:
        /**
         * @brief   Конструктор по умолчанию.
         * @details USARTx инициализируется в конструкторе класса-наследника
         *          значением, полученным из UsartDescriptor.
         */
        BaseUsart() = default;

        /**
         * @brief   Деструктор.
         * @details Вызывает Stop() для корректного завершения текущей передачи
         *          и выключения модуля.
         */
        ~BaseUsart(){
            Stop();
        };

        /**
         * @brief   Инициализация регистров USART заданными параметрами.
         * @param   usart_config   Указатель на структуру UsartConfig со всеми
         *                         параметрами модуля.
         * @details Передаёт содержимое UsartConfig в USART_InitTypeDef и вызывает
         *          USART_Init. Тактирование и настройка пинов выполняются
         *          в классе-наследнике, т.к. зависят от шаблонных параметров.
         */
        void InitBaseUsart(UsartConfig* usart_config){
            USART_InitTypeDef USART_InitStructure;
            USART_InitStructure.USART_BaudRate            = usart_config->BaudRate;
            USART_InitStructure.USART_WordLength          = usart_config->WordLength;
            USART_InitStructure.USART_StopBits            = usart_config->StopBits;
            USART_InitStructure.USART_Parity              = usart_config->Parity;
            USART_InitStructure.USART_Mode                = usart_config->Mode;
            USART_InitStructure.USART_HardwareFlowControl = usart_config->HardwareFlowControl;

            USART_Init(USARTx, &USART_InitStructure);
        }

        /**
         * @brief   Запуск модуля USART.
         * @details Включает USART (USART_Cmd(ENABLE)). Прерывания TXE/RXNE
         *          остаются отключёнными – они включаются отдельно при
         *          активации соответствующего направления передачи.
         */
        void Start(){
            USART_Cmd(USARTx, ENABLE);
        }

        /**
         * @brief   Останов модуля USART.
         * @details Дожидается опустошения сдвигового регистра передатчика (флаг TC),
         *          чтобы последний переданный байт не был обрезан, затем запрещает
         *          прерывания TXE/RXNE и выключает модуль.
         */
        void Stop(){
            // Дожидаемся завершения текущей передачи,
            // чтобы не оборвать последний байт на полусимволе
            while (USART_GetFlagStatus(USARTx, USART_FLAG_TC) == RESET){};

            USART_ITConfig(USARTx, USART_IT_TXE,  DISABLE);
            USART_ITConfig(USARTx, USART_IT_RXNE, DISABLE);
            USART_Cmd(USARTx, DISABLE);
        }

        // ---------------------------------------------------------------------
        // Отправка данных
        // ---------------------------------------------------------------------

        /**
         * @brief   Отправка одного байта (блокирующая).
         * @param   bt   Байт для отправки.
         * @details Ожидает освобождения регистра данных (TXE), затем записывает
         *          байт в регистр. Такой порядок (wait → write) позволяет
         *          аппаратному блоку USART использовать двойную буферизацию:
         *          следующий байт можно записать, пока предыдущий ещё
         *          передаётся сдвиговым регистром.
         */
        void SendByte(uint8_t bt){
            // Ждём освобождения регистра данных
            while (USART_GetFlagStatus(USARTx, USART_FLAG_TXE) == RESET){};

            USART_SendData(USARTx, static_cast<uint16_t>(bt));
        }

        /**
         * @brief   Отправка буфера произвольной длины (блокирующая).
         * @param   buffer   Указатель на массив данных.
         * @param   len      Количество байт для отправки.
         */
        void SendBuffer(const uint8_t* buffer, uint8_t len){
            for (uint8_t i = 0; i < len; i++){
                SendByte(buffer[i]);
            }
        }

        /**
         * @brief   Отправка пакета данных (BasePackage).
         * @param   package   Ссылка на базовый пакет, содержащий data_ptr и len.
         */
        void SendPackage(Packages::BasePackage& package){
            SendBuffer(package.data_ptr, package.len);
        }

        /**
         * @brief   Отправка сообщения фиксированной длины.
         * @param   message   Ссылка на объект Message.
         */
        void SendMessage(Messages::Message& message){
            SendBuffer(message.bytes_msg, message.msg_size);
        }
    };

    } // namespace STM_Usart
} // namespace STM_CppLib

#endif /*   BASE_USART_HPP   */