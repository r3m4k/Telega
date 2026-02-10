/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __BASE_TIMER_HPP
#define __BASE_TIMER_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

#include "main.h"
#include "stm32f30x.h"
#include "stm32f30x_rcc.h"
#include "stm32f30x_misc.h"
#include "stm32f30x_tim.h"

#include "Periphery.hpp"
#include "TimerConfig.hpp"

/* Defines -------------------------------------------------------------------*/
#define     Prescaller_1kHz         72000
#define     Prescaller_10kHz        7200
#define     Prescaller_100kHz       720

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------

namespace STM_CppLib{
    namespace STM_Timer{
    
    // -------------------------------------------------------------------------
    // Базовый таймер
    class BaseTimer{
    protected:
        TIM_TypeDef* TIMx;      // Структура инициализации таймера. Она используется почти во всех
                                // функциях таймеров, так что сохраним ей, как поле базового таймера
        
    public:

        BaseTimer(){}
        ~BaseTimer(){
            TIM_ITConfig(TIMx, TIM_IT_Update, DISABLE);
            TIM_Cmd(TIMx, DISABLE);
        };

        void InitBaseTimer(TimerConfig* timer_config){
            /* Init structures */
            TIM_TimeBaseInitTypeDef TIM_TimeBaseStructure;

            /* Enable TIM clock */
            timer_config->PeriphClockCmd(timer_config->RCC_PeriphClock, ENABLE);

            /* Set the timer configuration */
            TIM_TimeBaseStructInit(&TIM_TimeBaseStructure);
            TIM_TimeBaseStructure.TIM_Period = timer_config->TimPeriod;
            TIM_TimeBaseStructure.TIM_Prescaler = timer_config->TimPrescaler;
            TIM_TimeBaseInit(TIMx, &TIM_TimeBaseStructure);

        }
        
        void Start() {
            TIM_ITConfig(TIMx, TIM_IT_Update, ENABLE);
            TIM_Cmd(TIMx, ENABLE);
        }
    };

    // -------------------------------------------------------------------------

    enum class TimerTypes {Timer1, Timer2, Timer3, Timer4};

    template<TimerTypes timer_type>
    class TimerDescriptor{
    public:
        static constexpr TIM_TypeDef* get_TIMx(){
            switch (timer_type){
                case TimerTypes::Timer2: return TIM2;
                case TimerTypes::Timer3: return TIM3;
                case TimerTypes::Timer4: return TIM4;
                default: return nullptr;
            }
        };

        static constexpr IRQn_Type IRQn = []() -> IRQn_Type {
            switch (timer_type){
                case TimerTypes::Timer2: return TIM2_IRQn;
                case TimerTypes::Timer3: return TIM3_IRQn;
                case TimerTypes::Timer4: return TIM4_IRQn;
            }
        }();

        static constexpr uint32_t RCC_Periph = []() -> uint32_t {
            switch (timer_type){
                case TimerTypes::Timer2: return RCC_APB1Periph_TIM2;
                case TimerTypes::Timer3: return RCC_APB1Periph_TIM3;
                case TimerTypes::Timer4: return RCC_APB1Periph_TIM4;
            }
        }();
    };

    }
}


#endif /*   __BASE_TIMER_HPP   */