/** ****************************************************************************
 * @file    GpioPort.hpp
 * @author  Романовский Роман
 * @brief   Дескриптор порта GPIO
 * @details Предоставляет шаблонный класс GPIO_PortDescriptor для получения
 *          информации о конкретном порте GPIO на этапе компиляции:
 *          указатель на структуру GPIO_TypeDef и константа для тактирования RCC.
 **************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef GPIO_PORT_HPP
#define GPIO_PORT_HPP

/* Includes ------------------------------------------------------------------*/
#include "stm32f30x.h"
#include "stm32f30x_rcc.h"
#include "stm32f30x_gpio.h"

#include "Consts.hpp"

/* Defines -------------------------------------------------------------------*/

// -----------------------------------------------------------------------------
namespace STM_CppLib{
    namespace STM_GPIO{

        /**
         * @brief   Перечисление доступных портов GPIO.
         */
        enum class GPIO_Port{ PortA, PortB, PortC, PortD, PortE, PortF };

        /**
         * @brief   Шаблонный дескриптор порта GPIO.
         * @tparam  port  Порт GPIO (значение перечисления GPIO_Port).
         * @details Позволяет получить на этапе компиляции указатель на структуру
         *          GPIOx и соответствующую константу RCC для включения тактирования.
         * @note    Используется в классе GPIO_Pin для доступа к аппаратным ресурсам.
         */
        template<GPIO_Port port>
        class GPIO_PortDescriptor{
        public:
            /**
             * @brief   Возвращает указатель на структуру GPIO_TypeDef для заданного порта.
             * @return  Указатель на структуру GPIOx (например, GPIOA, GPIOB и т.д.).
             * @note    Если порт не распознан, возвращает nullptr.
             */
            static constexpr GPIO_TypeDef* get_GPIO_Type() {
                switch(port) {
                    case GPIO_Port::PortA: return GPIOA;
                    case GPIO_Port::PortB: return GPIOB;
                    case GPIO_Port::PortC: return GPIOC;
                    case GPIO_Port::PortD: return GPIOD;
                    case GPIO_Port::PortE: return GPIOE;
                    case GPIO_Port::PortF: return GPIOF;
                    default: return nullptr;
                }
            };
            
            /**
             * @brief   Константа для включения тактирования соответствующего порта.
             * @details Значение предназначено для передачи в функцию RCC_AHBPeriphClockCmd.
             * @note    Определяется через лямбда-выражение на этапе компиляции.
             */
            static constexpr uint32_t RCC_Periph = []() -> uint32_t {
                switch (port) {
                    case GPIO_Port::PortA: return RCC_AHBPeriph_GPIOA;
                    case GPIO_Port::PortB: return RCC_AHBPeriph_GPIOB;
                    case GPIO_Port::PortC: return RCC_AHBPeriph_GPIOC;
                    case GPIO_Port::PortD: return RCC_AHBPeriph_GPIOD;
                    case GPIO_Port::PortE: return RCC_AHBPeriph_GPIOE;
                    case GPIO_Port::PortF: return RCC_AHBPeriph_GPIOF;
                    default: return 0xFFFF;
                }
            }();
        

        };

    } // namespace STM_GPIO
} // namespace STM_CppLib
#endif /*   GPIO_PORT_HPP   */