/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __BASE_IRQ_DEVICE_HPP
#define __BASE_IRQ_DEVICE_HPP

/* Includes ------------------------------------------------------------------*/
#include "stm32f30x.h"
#include "stm32f30x_misc.h"

#include "Consts.hpp"

/* Defines -------------------------------------------------------------------*/
#define PeriphIRQnBase          16      // Смещение начала прерываний периферии
#define DefaultIRQChannelPreemptionPriority     0
#define DefaultIRQChannelSubPriority            0

/* Global variables ----------------------------------------------------------*/
extern __user_pHandler __user_vector_table[];

// -----------------------------------------------------------------------------

namespace STM_CppLib{
    
    // Базовый класс для работы с настройками прерывания
    template <typename IRQDevice, IRQn_Type IRQn>
    class BaseIRQDevice{
    protected:
        // Указатель на класс, реализующий отработку прерывания по каналу IRQn
        inline static IRQDevice* irq_device_ptr = nullptr;

        void InitInterrupt(NVIC_InitTypeDef* NVIC_InitStructure_ptr = nullptr){

            if (!NVIC_InitStructure_ptr){
                NVIC_InitTypeDef NVIC_InitStructure;

                /* Enable the Interrupt */
                NVIC_InitStructure.NVIC_IRQChannel = IRQn;
                NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority = DefaultIRQChannelPreemptionPriority;
                NVIC_InitStructure.NVIC_IRQChannelSubPriority = DefaultIRQChannelSubPriority;
                NVIC_InitStructure.NVIC_IRQChannelCmd = ENABLE;
                NVIC_Init(&NVIC_InitStructure);
            }
            else{   NVIC_Init(NVIC_InitStructure_ptr);  }

            register_interrupt();
        }
    
    private:
        void register_interrupt(){
            __user_vector_table[PeriphIRQnBase + IRQn] = static_irq_handler;
        }
        
        static void static_irq_handler(){
            irq_device_ptr->irq_handler();
        }
        
    };
}

#endif /*   __BASE_IRQ_DEVICE_HPP   */