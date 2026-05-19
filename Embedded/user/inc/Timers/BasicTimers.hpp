/** ***************************************************************************
 * @file    BasicTimers.hpp
 * @author  Романовский Роман
 * @brief   Базовые таймеры (TIM6, TIM7) для STM32F30x
 * 
 * @details Предоставляет шаблонный класс BasicTimer, объединяющий управление
 *          аппаратным таймером (BaseTimer) и настройку прерываний (BaseIRQDevice)
 *          с возможностью задания пользовательского обработчика на этапе
 *          компиляции. Для удобства использования определены псевдонимы
 *          Timer6, Timer7.
 *************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef BASIC_TIMERS_HPP
#define BASIC_TIMERS_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

#include "main.h"
#include "stm32f30x.h"
#include "stm32f30x_rcc.h"
#include "stm32f30x_misc.h"
#include "stm32f30x_tim.h"

#include "Consts.hpp"
#include "BaseTimer.hpp"
#include "BaseIRQDevice.hpp"
#include "TimerDescriptor.hpp"

/* Defines -------------------------------------------------------------------*/

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------

namespace STM_CppLib{
    namespace STM_Timer{
        
        // ---------------------------------------------------------------------
        /**
         * @brief   Шаблонный класс для работы с базовыми таймерами.
         * 
         * @tparam  timer_type   Тип таймера.
         * @tparam  external_irq_handler   Пользовательский обработчик прерывания.
         *          Может быть указателем на функцию или лямбда-выражением без захвата.
         * 
         * @details Объединяет инициализацию аппаратного таймера (BaseTimer)
         *          и привязку прерывания через механизм CRTP (BaseIRQDevice).
         *          Благодаря передаче обработчика через шаблонный параметр,
         *          вызов выполняется напрямую без виртуальных функций.
         */
        template<TimerTypes timer_type, auto external_irq_handler>
        class BasicTimer: public BaseTimer, public BaseIRQDevice<BasicTimer<timer_type, external_irq_handler>, 
                                                                 TimerDescriptor<timer_type>::IRQn>{

            static_assert(
                timer_type == TimerTypes::Timer6 || 
                timer_type == TimerTypes::Timer7,
                "timer_type not is basic timer"
            );

        public:
            /**
             * @brief   Конструктор объекта BasicTimer.
             * 
             * @details Инициализирует указатель на собственный экземпляр как
             *          обработчик прерывания (irq_device_ptr) и сохраняет
             *          указатель на регистровую структуру таймера TIMx,
             *          полученный через TimerDescriptor.
             */
            BasicTimer(){
                this->irq_device_ptr = this;
                this->TIMx = TimerDescriptor<timer_type>::get_TIMx();
            }

            /**
             * @brief   Инициализация таймера и настройка его прерывания.
             * 
             * @param   tim_period   Период счёта таймера.
             * @param   prescaler   Делитель тактовой частоты таймера.
             * @param   timer_config_ptr   Указатель на пользовательскую конфигурацию таймера.
             *                      Если передан nullptr, используется конфигурация по умолчанию
             *                      с заданными периодом и предделителем.
             * @param   NVIC_IRQChannelPreemptionPriority   Приоритет вытеснения для прерывания таймера.
             * @param   NVIC_IRQChannelSubPriority          Подприоритет прерывания.
             * 
             * @details Метод предоставляет два способа инициализации:
             *          - Через готовую структуру TimerConfig (если указатель не nullptr).
             *          - Автоматически: используется RCC_APB1PeriphClockCmd,
             *            RCC_Periph из TimerDescriptor, заданные prescaler и tim_period.
             *          После инициализации таймера настраивается прерывание
             *          с указанными приоритетами.
             */
            void Init(
                uint32_t tim_period = 1000,
                uint16_t prescaler = Prescaler_10kHz,
                TimerConfig* timer_config_ptr = nullptr,
                uint8_t NVIC_IRQChannelPreemptionPriority = DefaultIRQChannelPreemptionPriority,
                uint8_t NVIC_IRQChannelSubPriority = DefaultIRQChannelSubPriority
            ){
                if (!timer_config_ptr){
                    TimerConfig timer_config = {
                        .PeriphClockCmd = RCC_APB1PeriphClockCmd,
                        .RCC_PeriphClock = TimerDescriptor<timer_type>::RCC_Periph,
                        .TimPrescaler = prescaler,
                        .TimPeriod = tim_period
                    };

                    this->InitBaseTimer(&timer_config);
                }
                else{   this->InitBaseTimer(timer_config_ptr);   }
                
                NVIC_InitTypeDef NVIC_InitStructure;
                NVIC_InitStructure.NVIC_IRQChannel = TimerDescriptor<timer_type>::IRQn;
                NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority = NVIC_IRQChannelPreemptionPriority;
                NVIC_InitStructure.NVIC_IRQChannelSubPriority = NVIC_IRQChannelSubPriority;
                NVIC_InitStructure.NVIC_IRQChannelCmd = ENABLE;

                this->InitInterrupt(&NVIC_InitStructure);
            }

            /**
             * @brief   Обработчик прерывания таймера.
             * 
             * @details Вызывает пользовательский обработчик, переданный через
             *          шаблонный параметр external_irq_handler, после чего
             *          сбрасывает флаг прерывания по событию обновления (TIM_IT_Update).
             *          Очистка флага обязательна для повторного возникновения прерывания.
             */
            void irq_handler(){
                external_irq_handler();
                TIM_ClearITPendingBit(TIMx, TIM_IT_Update);
            }

        };

        // ---------------------------------------------------------------------

        /**
         * @brief   Псевдоним BasicTimer для таймера TIM6.
         * @tparam  external_irq_handler   Пользовательский обработчик прерывания.
         */
        template<auto external_irq_handler>
        using Timer6 = BasicTimer<TimerTypes::Timer6, external_irq_handler>;

        /**
         * @brief   Псевдоним BasicTimer для таймера TIM7.
         * @tparam  external_irq_handler   Пользовательский обработчик прерывания.
         */
        template<auto external_irq_handler>
        using Timer7 = BasicTimer<TimerTypes::Timer7, external_irq_handler>;

        // ---------------------------------------------------------------------

    } // namespace STM_Timer
} // namespace STM_CppLib


#endif /*   BASIC_TIMERS_HPP   */