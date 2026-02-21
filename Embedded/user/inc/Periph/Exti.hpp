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

    template <STM_GPIO::GPIO_Port port, uint8_t pin_source>
    class EXTI_Descriptor{
    public:
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
    
    // Класс для работы с EXTI
    template<uint8_t EXTI_PortSourceGPIOx, uint8_t EXTI_PinSourcex>
    class GPIO_EXTI{
    public:
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
    };

    } // namespace EXTI   
} // namespace STM_CppLib


#endif /*   __EXTI_HPP   */