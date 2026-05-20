/** ****************************************************************************
 * @file    UsartDescriptor.hpp
 * @author  Романовский Роман
 * @brief   Дескриптор USART для STM32F30x (compile-time информация)
 * @date    Апрель 2026
 *
 * @details Предоставляет шаблонный класс UsartDescriptor, обеспечивающий
 *          на этапе компиляции статический доступ к аппаратным параметрам
 *          модулей USART/UART:
 *          - указатель на структуру USARTx;
 *          - номер прерывания IRQn;
 *          - константа тактирования RCC_Periph;
 *          - функция включения тактирования PeriphClockCmd (APB1 или APB2);
 *          - альтернативная функция AF для пинов TX/RX.
 *          Используется для конфигурации шаблонного класса Usart.
 **************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef USART_DESCRIPTOR_HPP
#define USART_DESCRIPTOR_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

#include "stm32f30x.h"
#include "stm32f30x_rcc.h"
#include "stm32f30x_misc.h"
#include "stm32f30x_gpio.h"
#include "stm32f30x_usart.h"

#include "Consts.hpp"

/* Defines -------------------------------------------------------------------*/

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------

namespace STM_CppLib{
    namespace STM_Usart{

    /**
     * @brief   Перечисление доступных USART/UART модулей.
     * @details USART1-3 находятся на шине APB2/APB1 и используют AF7,
     *          UART4-5 на APB1 и используют AF5.
     */
    enum class UsartTypes {Usart1, Usart2, Usart3, Uart4, Uart5};

    /**
     * @brief   Шаблонный дескриптор для получения статической информации о USART.
     * @tparam  usart_type   Тип модуля (значение из UsartTypes).
     *
     * @details Позволяет на этапе компиляции получить:
     *          - указатель на регистровую структуру USARTx;
     *          - номер прерывания IRQn;
     *          - константу RCC для включения тактирования;
     *          - функцию включения тактирования (APB2 для USART1, APB1 для остальных);
     *          - номер альтернативной функции AF для пинов TX/RX.
     */
    template<UsartTypes usart_type>
    class UsartDescriptor{
    public:
        /**
         * @brief   Возвращает указатель на регистровую структуру соответствующего модуля.
         * @return  USART_TypeDef*  Указатель на USART1, USART2, USART3, UART4 или UART5.
         * @retval  nullptr         Для некорректного типа (default-ветка).
         */
        static constexpr USART_TypeDef* get_USARTx(){
            switch (usart_type){
                case UsartTypes::Usart1: return USART1;
                case UsartTypes::Usart2: return USART2;
                case UsartTypes::Usart3: return USART3;
                case UsartTypes::Uart4:  return UART4;
                case UsartTypes::Uart5:  return UART5;
                default: return nullptr;
            }
        };

        /**
         * @brief   Номер прерывания, соответствующего модулю.
         */
        static constexpr IRQn_Type IRQn = []() -> IRQn_Type {
            switch (usart_type){
                case UsartTypes::Usart1: return USART1_IRQn;
                case UsartTypes::Usart2: return USART2_IRQn;
                case UsartTypes::Usart3: return USART3_IRQn;
                case UsartTypes::Uart4:  return UART4_IRQn;
                case UsartTypes::Uart5:  return UART5_IRQn;
            }
        }();

        /**
         * @brief   Константа RCC для включения тактирования USART/UART.
         * @details Возвращает:
         *          - RCC_APB2Periph_USART1 для Usart1;
         *          - RCC_APB1Periph_USART2..UART5 для остальных.
         */
        static constexpr uint32_t RCC_Periph = []() -> uint32_t {
            switch (usart_type){
                case UsartTypes::Usart1: return RCC_APB2Periph_USART1;
                case UsartTypes::Usart2: return RCC_APB1Periph_USART2;
                case UsartTypes::Usart3: return RCC_APB1Periph_USART3;
                case UsartTypes::Uart4:  return RCC_APB1Periph_UART4;
                case UsartTypes::Uart5:  return RCC_APB1Periph_UART5;
            }
        }();

        /**
         * @brief   Указатель на функцию включения тактирования периферии.
         * @details Для Usart1 это RCC_APB2PeriphClockCmd, для остальных
         *          RCC_APB1PeriphClockCmd. Позволяет единообразно обращаться
         *          к тактированию без дополнительных условных операторов.
         */
        static constexpr RCC_PeriphClockCmd_Type PeriphClockCmd = []() -> RCC_PeriphClockCmd_Type {
            switch (usart_type){
                case UsartTypes::Usart1: return RCC_APB2PeriphClockCmd;
                case UsartTypes::Usart2: return RCC_APB1PeriphClockCmd;
                case UsartTypes::Usart3: return RCC_APB1PeriphClockCmd;
                case UsartTypes::Uart4:  return RCC_APB1PeriphClockCmd;
                case UsartTypes::Uart5:  return RCC_APB1PeriphClockCmd;
            }
        }();

        /**
         * @brief   Альтернативная функция GPIO для пинов TX/RX.
         * @details Согласно datasheet STM32F303:
         *          - USART1-3 — AF7;
         *          - UART4-5  — AF5.
         */
        static constexpr uint8_t AF = []() -> uint8_t {
            switch (usart_type){
                case UsartTypes::Usart1: return GPIO_AF_7;
                case UsartTypes::Usart2: return GPIO_AF_7;
                case UsartTypes::Usart3: return GPIO_AF_7;
                case UsartTypes::Uart4:  return GPIO_AF_5;
                case UsartTypes::Uart5:  return GPIO_AF_5;
            }
        }();
    };

    } // namespace STM_Usart
} // namespace STM_CppLib

#endif /*   USART_DESCRIPTOR_HPP   */
