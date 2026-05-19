/** ****************************************************************************
 * @file    Exti.hpp
 * @author  Романовский Роман
 * @brief   Шаблонные классы для работы с внешними прерываниями (EXTI) STM32F30x
 *
 * @details Предоставляет:
 *          - шаблонный дескриптор EXTI_Descriptor, обеспечивающий на этапе
 *            компиляции статический доступ к параметрам линии EXTI
 *            (номер прерывания IRQn и идентификатор источника порта);
 *          - шаблонный класс GPIO_EXTI для настройки линии EXTI и
 *            программного инициирования прерывания.
 *          Оба класса параметризованы портом и номером вывода,
 *          что обеспечивает типобезопасность и минимальные накладные расходы.
 **************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __EXTI_HPP
#define __EXTI_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

#include "stm32f30x.h"
#include "stm32f30x_gpio.h"
#include "stm32f30x_exti.h"
#include "stm32f30x_syscfg.h"

#include "GpioPort.hpp"

/* Defines -------------------------------------------------------------------*/

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------
namespace STM_CppLib{
    namespace STM_EXTI{ 

    /**
     * @brief   Шаблонный дескриптор для получения статической информации о линии EXTI.
     * @tparam  port        Порт GPIO (значение перечисления GPIO_Port).
     * @tparam  pin_source  Номер вывода (0..15).
     *
     * @details Позволяет на этапе компиляции получить:
     *          - номер прерывания IRQn, соответствующий линии EXTI;
     *          - идентификатор источника порта PortSource для функции
     *            SYSCFG_EXTILineConfig.
     *          На STM32F30x линии EXTI 0..4 имеют собственные векторы прерываний
     *          (EXTI0_IRQn..EXTI4_IRQn), линии 5..9 объединены в один вектор
     *          EXTI9_5_IRQn, линии 10..15 – в EXTI15_10_IRQn.
     * @note    Линия EXTI2 на STM32F30x объединена с прерыванием Touch Sensing
     *          (EXTI2_TS_IRQn).
     */
    template <STM_GPIO::GPIO_Port port, uint8_t pin_source>
    class EXTI_Descriptor{
    public:
        /**
         * @brief   Номер прерывания, соответствующий линии EXTI.
         * @details Вычисляется по шаблонному параметру pin_source:
         *          - 0..4   – индивидуальные векторы EXTI0_IRQn..EXTI4_IRQn;
         *          - 5..9   – общий вектор EXTI9_5_IRQn;
         *          - 10..15 – общий вектор EXTI15_10_IRQn.
         */
        static constexpr IRQn_Type IRQn = [](){
        switch (pin_source) {
            case GPIO_PinSource0: return EXTI0_IRQn;
            case GPIO_PinSource1: return EXTI1_IRQn;
            case GPIO_PinSource2: return EXTI2_TS_IRQn;
            case GPIO_PinSource3: return EXTI3_IRQn;
            case GPIO_PinSource4: return EXTI4_IRQn;

            case GPIO_PinSource5: case GPIO_PinSource6:
            case GPIO_PinSource7: case GPIO_PinSource8:
            case GPIO_PinSource9:
                return EXTI9_5_IRQn;

            case GPIO_PinSource10: case GPIO_PinSource11:
            case GPIO_PinSource12: case GPIO_PinSource13:
            case GPIO_PinSource14: case GPIO_PinSource15:
                return EXTI15_10_IRQn;
            }
        }();

        /**
         * @brief   Идентификатор источника порта для SYSCFG_EXTILineConfig.
         * @details Возвращает значение EXTI_PortSourceGPIOA..GPIOF в зависимости
         *          от шаблонного параметра port.
         */
        static constexpr uint8_t PortSource = [](){
            switch(port) {
                case STM_GPIO::GPIO_Port::PortA: return EXTI_PortSourceGPIOA;
                case STM_GPIO::GPIO_Port::PortB: return EXTI_PortSourceGPIOB;
                case STM_GPIO::GPIO_Port::PortC: return EXTI_PortSourceGPIOC;
                case STM_GPIO::GPIO_Port::PortD: return EXTI_PortSourceGPIOD;
                case STM_GPIO::GPIO_Port::PortE: return EXTI_PortSourceGPIOE;
                case STM_GPIO::GPIO_Port::PortF: return EXTI_PortSourceGPIOF;
            }
        }();
    };
    
    /**
     * @brief   Шаблонный класс для настройки линии EXTI.
     * @tparam  EXTI_PortSourceGPIOx   Идентификатор источника порта
     *                                 (EXTI_PortSourceGPIOA..GPIOF).
     * @tparam  EXTI_PinSourcex        Номер вывода, соответствующий линии EXTI (0..15).
     *
     * @details Предоставляет методы настройки одной линии EXTI и программного
     *          инициирования прерывания. Используется как базовый класс в
     *          GPIO_Pin_EXTI, но может применяться и самостоятельно.
     * @note    Для корректной работы перед вызовом InitExti необходимо включить
     *          тактирование SYSCFG (обычно выполняется в инициализации GPIO
     *          через RCC_AHBPeriphClockCmd).
     */
    template<uint8_t EXTI_PortSourceGPIOx, uint8_t EXTI_PinSourcex>
    class GPIO_EXTI{
    public:
        /**
         * @brief   Инициализация линии EXTI.
         * @param   EXTI_InitStructure_ptr   Указатель на пользовательскую
         *                                   структуру настройки EXTI. Если nullptr,
         *                                   используется конфигурация по умолчанию:
         *                                   режим прерывания, срабатывание по
         *                                   нарастающему фронту, линия разрешена.
         * @details Сначала вызывает SYSCFG_EXTILineConfig для связывания
         *          выбранного порта с линией EXTI, затем вызывает EXTI_Init
         *          с переданной или сгенерированной структурой настройки.
         */
        void InitExti(EXTI_InitTypeDef* EXTI_InitStructure_ptr = nullptr){
            
            // Select the input source pin for the EXTI line
            SYSCFG_EXTILineConfig(EXTI_PortSourceGPIOx, EXTI_PinSourcex);

            if (!EXTI_InitStructure_ptr){
                EXTI_InitTypeDef EXTI_InitStructure;

                EXTI_InitStructure.EXTI_Line = static_cast<uint32_t>(EXTI_PinSourcex);
                EXTI_InitStructure.EXTI_Mode = EXTI_Mode_Interrupt;
                EXTI_InitStructure.EXTI_Trigger = EXTI_Trigger_Rising;
                EXTI_InitStructure.EXTI_LineCmd = ENABLE;
                EXTI_Init(&EXTI_InitStructure);
            }
            else{   EXTI_Init(EXTI_InitStructure_ptr);    }
        }

        /**
         * @brief   Программное инициирование прерывания EXTI.
         * @details Устанавливает соответствующий бит в регистре EXTI->SWIER,
         *          что вызывает срабатывание прерывания EXTI на данной линии
         *          так, как будто произошло аппаратное событие. Номер линии
         *          соответствует шаблонному параметру EXTI_PinSourcex.
         * @note    Линия EXTI должна быть предварительно настроена (InitExti)
         *          и разрешена, иначе прерывание не сработает.
         */
        void GenerateSWInterrupt(){
            EXTI_GenerateSWInterrupt(static_cast<uint32_t>(EXTI_PinSourcex));
        }
    };

    } // namespace STM_EXTI
} // namespace STM_CppLib


#endif /*   __EXTI_HPP   */