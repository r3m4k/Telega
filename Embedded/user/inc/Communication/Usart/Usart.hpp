/** ***************************************************************************
 * @file    Usart.hpp
 * @author  Романовский Роман
 * @brief   Шаблонный класс USART/UART для STM32F30x
 *
 * @details Предоставляет шаблонный класс Usart, объединяющий управление
 *          аппаратным модулем (BaseUsart) и настройку прерываний
 *          (BaseIRQDevice). Тип модуля и пины TX/RX фиксируются на этапе
 *          компиляции. Для удобства использования определены псевдонимы
 *          Usart1, Usart2, Usart3, Uart4, Uart5.
 *************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef USART_HPP
#define USART_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>
#include <concepts>

#include "main.h"
#include "stm32f30x.h"
#include "stm32f30x_rcc.h"
#include "stm32f30x_misc.h"
#include "stm32f30x_gpio.h"
#include "stm32f30x_usart.h"

#include "Consts.hpp"
#include "GpioPort.hpp"
#include "GpioPin.hpp"
#include "BaseIRQDevice.hpp"
#include "BaseUsart.hpp"
#include "UsartConfig.hpp"
#include "UsartDescriptor.hpp"
#include "DecoderImu.hpp"

/* Defines -------------------------------------------------------------------*/

/* Usings --------------------------------------------------------------------*/
/**
 * @brief   Тип декодера, используемый для обработки принятых байтов.
 * @details По умолчанию используется DecoderTelega из пространства имён Decoder.
 *          Может быть заменён на другой тип, удовлетворяющий концепту
 *          HasVoidByteProcessing.
 */
using UsartDecoder = Decoder::DecoderTelega;

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------

namespace STM_CppLib{
    namespace STM_Usart{

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
         * @brief   Шаблонный класс для работы с USART/UART.
         *
         * @tparam  usart_type   Тип модуля (Usart1, Usart2, Usart3, Uart4, Uart5).
         * @tparam  PinTX        Тип пина передачи (должен удовлетворять GpioPinConcept).
         * @tparam  PinRX        Тип пина приёма (должен удовлетворять GpioPinConcept).
         *
         * @details Объединяет инициализацию аппаратного модуля (BaseUsart)
         *          и привязку прерывания через механизм CRTP (BaseIRQDevice).
         *          Тип альтернативной функции (AF) извлекается автоматически
         *          из UsartDescriptor. Каждый принятый по RX байт передаётся
         *          в объект декодера (тип задан глобальным псевдонимом UsartDecoder).
         */
        template<UsartTypes usart_type,
                 STM_GPIO::GpioPinConcept PinTX,
                 STM_GPIO::GpioPinConcept PinRX>
        class Usart: public BaseUsart,
                     public BaseIRQDevice<Usart<usart_type, PinTX, PinRX>,
                                          UsartDescriptor<usart_type>::IRQn>{

            static_assert(HasVoidByteProcessing<UsartDecoder>,
                "\n=== DECODER INTERFACE ERROR ===\n"
                "UsartDecoder type must provide: void byte_processing(uint8_t)\n"
                "===============================\n");

        private:
            PinTX pin_tx;       ///< Объект пина TX
            PinRX pin_rx;       ///< Объект пина RX
            UsartDecoder decoder;   ///< Декодер принятых байтов

        public:
            /**
             * @brief   Конструктор объекта Usart.
             *
             * @details Инициализирует указатель на собственный экземпляр как
             *          обработчик прерывания (irq_device_ptr) и сохраняет
             *          указатель на регистровую структуру USARTx,
             *          полученный через UsartDescriptor.
             */
            Usart(){
                this->irq_device_ptr = this;
                this->USARTx = UsartDescriptor<usart_type>::get_USARTx();
            }

            /**
             * @brief   Инициализация модуля и настройка пинов.
             *
             * @param   baudrate   Скорость передачи (бит/с).
             * @param   usart_config_ptr   Указатель на пользовательскую конфигурацию.
             *                             Если nullptr, используются настройки по умолчанию:
             *                             8 бит данных, 1 стоп-бит, без проверки чётности,
             *                             без аппаратного управления потоком, режим Tx | Rx.
             * @param   NVIC_IRQChannelPreemptionPriority   Приоритет вытеснения прерывания.
             * @param   NVIC_IRQChannelSubPriority          Подприоритет прерывания.
             *
             * @details Последовательно выполняет:
             *          - включение тактирования USART через UsartDescriptor;
             *          - настройку пинов TX и RX с нужной альтернативной функцией;
             *          - базовую инициализацию регистров (InitBaseUsart);
             *          - включение модуля (Start);
             *          - регистрацию обработчика прерывания в NVIC.
             *          После инициализации прерывания TXE/RXNE остаются
             *          отключёнными – они включаются отдельно при необходимости.
             */
            void Init(
                uint32_t baudrate,
                UsartConfig* usart_config_ptr = nullptr,
                uint8_t NVIC_IRQChannelPreemptionPriority = DefaultIRQChannelPreemptionPriority,
                uint8_t NVIC_IRQChannelSubPriority        = DefaultIRQChannelSubPriority
            ){
                // Включение тактирования USART --------------------------------
                UsartDescriptor<usart_type>::PeriphClockCmd(
                    UsartDescriptor<usart_type>::RCC_Periph, ENABLE);

                // Настройка пинов TX/RX ---------------------------------------
                init_pins();

                // Базовая инициализация регистров -----------------------------
                if (!usart_config_ptr){
                    UsartConfig usart_config = {
                        .BaudRate            = baudrate,
                        .WordLength          = USART_WordLength_8b,
                        .StopBits            = USART_StopBits_1,
                        .Parity              = USART_Parity_No,
                        .Mode                = USART_Mode_Tx | USART_Mode_Rx,
                        .HardwareFlowControl = USART_HardwareFlowControl_None
                    };
                    this->InitBaseUsart(&usart_config);
                }
                else{   this->InitBaseUsart(usart_config_ptr);   }

                // Запуск модуля -----------------------------------------------
                this->Start();

                // Настройка NVIC ----------------------------------------------
                NVIC_InitTypeDef NVIC_InitStructure;
                NVIC_InitStructure.NVIC_IRQChannel = UsartDescriptor<usart_type>::IRQn;
                NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority = NVIC_IRQChannelPreemptionPriority;
                NVIC_InitStructure.NVIC_IRQChannelSubPriority        = NVIC_IRQChannelSubPriority;
                NVIC_InitStructure.NVIC_IRQChannelCmd = ENABLE;

                this->InitInterrupt(&NVIC_InitStructure);
            }

            /**
             * @brief   Разрешает прерывание по приёму (RXNE).
             * @details После вызова при каждом принятом байте в регистре данных
             *          будет вызван обработчик прерывания USART (irq_handler),
             *          который передаст байт в декодер. Вызывается отдельно
             *          от Init(), поскольку не все сценарии требуют приёма.
             */
            void EnableRxInterrupt(){
                USART_ITConfig(this->USARTx, USART_IT_RXNE, ENABLE);
            }

            /**
             * @brief   Запрещает прерывание по приёму (RXNE).
             */
            void DisableRxInterrupt(){
                USART_ITConfig(this->USARTx, USART_IT_RXNE, DISABLE);
            }

            /**
             * @brief   Обработчик прерывания USART.
             *
             * @details Проверяет флаг RXNE; при его установке читает принятый
             *          байт из регистра данных (чтение DR автоматически сбрасывает
             *          RXNE) и передаёт его в декодер для пошагового разбора пакета.
             *          Также очищает флаг переполнения приёмника (ORE), который
             *          может появиться при пропуске байтов между обработками.
             */
            void irq_handler(){
                if (USART_GetITStatus(this->USARTx, USART_IT_RXNE) == SET){
                    uint8_t bt = static_cast<uint8_t>(USART_ReceiveData(this->USARTx));
                    decoder.byte_processing(bt);
                }

                // Сбрасываем флаг переполнения приёмника на случай его появления
                USART_ClearITPendingBit(this->USARTx, USART_IT_ORE);
            }

        private:
            /**
             * @brief   Настройка пинов TX и RX в режим альтернативной функции.
             *
             * @details Извлекает порт и номер вывода из типов пинов через
             *          static-методы get_port() / get_pin_source() и вызывает
             *          GPIO_PinAFConfig с нужной альтернативной функцией,
             *          полученной из UsartDescriptor. Перед вызовом пины
             *          переводятся в режим Mode_AF методом InitPin() базового класса.
             */
            void init_pins(){
                // Настроим пин TX: Mode_AF, с подтяжкой к питанию (IDLE=1)
                pin_tx.InitPin(GPIO_Mode_AF, GPIO_PuPd_UP);

                // Настроим пин RX: Mode_AF, с подтяжкой к питанию (IDLE=1)
                pin_rx.InitPin(GPIO_Mode_AF, GPIO_PuPd_UP);

                // Подключим альтернативную функцию
                GPIO_PinAFConfig(
                    STM_GPIO::GPIO_PortDescriptor<PinTX::get_port()>::get_GPIO_Type(),
                    PinTX::get_pin_source(),
                    UsartDescriptor<usart_type>::AF);

                GPIO_PinAFConfig(
                    STM_GPIO::GPIO_PortDescriptor<PinRX::get_port()>::get_GPIO_Type(),
                    PinRX::get_pin_source(),
                    UsartDescriptor<usart_type>::AF);
            }
        };

        // ---------------------------------------------------------------------

        /**
         * @brief   Псевдоним Usart для модуля USART1.
         * @tparam  PinTX   Тип пина передачи.
         * @tparam  PinRX   Тип пина приёма.
         */
        template<STM_GPIO::GpioPinConcept PinTX, STM_GPIO::GpioPinConcept PinRX>
        using Usart1 = Usart<UsartTypes::Usart1, PinTX, PinRX>;

        /**
         * @brief   Псевдоним Usart для модуля USART2.
         */
        template<STM_GPIO::GpioPinConcept PinTX, STM_GPIO::GpioPinConcept PinRX>
        using Usart2 = Usart<UsartTypes::Usart2, PinTX, PinRX>;

        /**
         * @brief   Псевдоним Usart для модуля USART3.
         */
        template<STM_GPIO::GpioPinConcept PinTX, STM_GPIO::GpioPinConcept PinRX>
        using Usart3 = Usart<UsartTypes::Usart3, PinTX, PinRX>;

        /**
         * @brief   Псевдоним Usart для модуля UART4.
         */
        template<STM_GPIO::GpioPinConcept PinTX, STM_GPIO::GpioPinConcept PinRX>
        using Uart4  = Usart<UsartTypes::Uart4, PinTX, PinRX>;

        /**
         * @brief   Псевдоним Usart для модуля UART5.
         */
        template<STM_GPIO::GpioPinConcept PinTX, STM_GPIO::GpioPinConcept PinRX>
        using Uart5  = Usart<UsartTypes::Uart5, PinTX, PinRX>;

        // ---------------------------------------------------------------------

    } // namespace STM_Usart
} // namespace STM_CppLib

#endif /*   USART_HPP   */