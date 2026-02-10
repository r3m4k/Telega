/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __GPIO_PIN_HPP
#define __GPIO_PIN_HPP

/* Includes ------------------------------------------------------------------*/
#include "stm32f30x.h"
#include "stm32f30x_rcc.h"
#include "stm32f30x_gpio.h"

#include "Consts.hpp"
#include "Exti.hpp"
#include "GpioPort.hpp"
#include "BaseIRQDevice.hpp"

/* Defines -------------------------------------------------------------------*/
#define USE_EXTI        true
#define NOT_USE_EXTI    false

/* Global variables ----------------------------------------------------------*/
extern STM_CppLib::Leds leds;

// -----------------------------------------------------------------------------
namespace STM_CppLib{
    namespace STM_GPIO{

        // Базовый класс для работы с пином GPIO
        template <GPIO_Port port, uint8_t pin_source>
        class GPIO_Pin{

        public:
            void InitPin(
                GPIOMode_TypeDef GPIO_Mode = GPIO_Mode_OUT,
                GPIOPuPd_TypeDef GPIO_PuPd = GPIO_PuPd_NOPULL,
                GPIO_InitTypeDef* GPIO_InitStructure_ptr = nullptr
            ){
                
                RCC_AHBPeriphClockCmd(GPIO_PortDescriptor<port>::RCC_Periph, ENABLE);
                
                if (!GPIO_InitStructure_ptr){                
                    GPIO_InitTypeDef GPIO_InitStructure;
            
                    /* Configure the GPIOx pin */
                    GPIO_InitStructure.GPIO_Pin = (1U << pin_source);
                    GPIO_InitStructure.GPIO_Mode = GPIO_Mode;
                    GPIO_InitStructure.GPIO_OType = GPIO_OType_PP;
                    GPIO_InitStructure.GPIO_PuPd = GPIO_PuPd;
                    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
                    GPIO_Init(GPIO_PortDescriptor<port>::get_GPIO_Type(), &GPIO_InitStructure);
                }
                else{   GPIO_Init(GPIO_PortDescriptor<port>::get_GPIO_Type(), GPIO_InitStructure_ptr);   }
            }

            void SetPin(){
                GPIO_SetBits(GPIO_PortDescriptor<port>::get_GPIO_Type(), (1U << pin_source));
            }

            void ResetPin(){
                GPIO_ResetBits(GPIO_PortDescriptor<port>::get_GPIO_Type(), (1U << pin_source));
            }

        };

        // Класс для работы с пином GPIO с поддержкой EXTI
        template <GPIO_Port port, uint8_t pin_source, handler_t external_irq_handler>
        class GPIO_Pin_EXTI: 
            public GPIO_Pin<port, pin_source>,

            public STM_EXTI::GPIO_EXTI<
                        STM_EXTI::EXTI_Descriptor<port, pin_source>::PortSource, pin_source>, 

            public BaseIRQDevice<GPIO_Pin_EXTI<port, pin_source, external_irq_handler>, 
                                    STM_EXTI::EXTI_Descriptor<port, pin_source>::IRQn>
        {

        public:
            GPIO_Pin_EXTI(){
                this->irq_device_ptr = this;
            }

            void InitPinExti(
                GPIOMode_TypeDef GPIO_Mode = GPIO_Mode_IN,
                GPIOPuPd_TypeDef GPIO_PuPd = GPIO_PuPd_DOWN,
                GPIO_InitTypeDef* GPIO_InitStructure_ptr = nullptr,
                EXTI_InitTypeDef* EXTI_InitStructure_ptr = nullptr,
                NVIC_InitTypeDef* NVIC_InitStructure_ptr = nullptr
            ){
                
                this->InitPin(GPIO_Mode, GPIO_PuPd, GPIO_InitStructure_ptr);
                this->InitExti(EXTI_InitStructure_ptr);
                this->InitInterrupt(NVIC_InitStructure_ptr);
            }
            
            void irq_handler(){
                /*  Код для отработки прерывания  */
                external_irq_handler();

                EXTI_ClearFlag(static_cast<uint32_t>(pin_source));
            }
        };
    
    } // namespace STM_GPIO
} // namespace STM_CppLib

#endif /*   __GPIO_PIN_HPP   */