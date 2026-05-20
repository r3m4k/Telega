/** ****************************************************************************
 * @file    TimerDescriptor.hpp
 * @brief   Дескриптор таймеров для STM32F30x (compile-time информация)
 * @author  Романовский Роман
 * @date    Февраль 2026
 * 
 * @details Предоставляет шаблонный класс TimerDescriptor, обеспечивающий
 *          на этапе компиляции статический доступ к аппаратным параметрам
 *          таймеров:
 *          - указатель на структуру TIMx
 *          - номер прерывания IRQn
 *          - константа тактирования RCC_Periph.
 *          Используется для конфигурации шаблонных классов-таймеров.
 **************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef TIMER_DESCRIPTOR_HPP
#define TIMER_DESCRIPTOR_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

#include "stm32f30x.h"
#include "stm32f30x_rcc.h"
#include "stm32f30x_misc.h"
#include "stm32f30x_tim.h"

#include "TimerConfig.hpp"

/* Defines -------------------------------------------------------------------*/

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------

namespace STM_CppLib{
    namespace STM_Timer{
    // -------------------------------------------------------------------------

    /**
     * @brief   Перечисление доступных таймеров.
     * @details Timer1 – расширенный таймер (advanced), Timer2–Timer4 – общего назначения.
     */
    enum class TimerTypes {Timer1, Timer2, Timer3, Timer4, Timer6, Timer7};

    /**
     * @brief   Шаблонный дескриптор для получения статической информации о таймере.
     * @tparam timer_type   Тип таймера (значение из TimerTypes).
     * 
     * @details Позволяет на этапе компиляции получить:
     *          - указатель на регистровую структуру TIMx;
     *          - номер прерывания IRQn (для Timer2–Timer4);
     *          - константу RCC для включения тактирования.
     * 
     * @note    Для Timer1 номер прерывания не определён; при необходимости его
     *          следует добавить отдельно.
     */
    template<TimerTypes timer_type>
    class TimerDescriptor{
    public:
        /**
         * @brief   Возвращает указатель на регистровую структуру соответствующего таймера.
         * @return  TIM_TypeDef*  Указатель на TIM1, TIM2, TIM3 или TIM4.
         * @retval  nullptr       Для некорректного типа (default-ветка).
         */
        static constexpr TIM_TypeDef* get_TIMx(){
            switch (timer_type){
                case TimerTypes::Timer1: return TIM1;
                case TimerTypes::Timer2: return TIM2;
                case TimerTypes::Timer3: return TIM3;
                case TimerTypes::Timer4: return TIM4;
                case TimerTypes::Timer6: return TIM6;
                case TimerTypes::Timer7: return TIM7;
                default: return nullptr;
            }
        };

        /**
         * @brief   Номер прерывания, соответствующего таймеру.
         * @details Определён только для Timer2–Timer4.
         * @warning Для Timer1 использование приведёт к неопределённому поведению.
         */
        static constexpr IRQn_Type IRQn = []() -> IRQn_Type {
            switch (timer_type){
                case TimerTypes::Timer2: return TIM2_IRQn;
                case TimerTypes::Timer3: return TIM3_IRQn;
                case TimerTypes::Timer4: return TIM4_IRQn;
                case TimerTypes::Timer6: return TIM6_DAC_IRQn;
                case TimerTypes::Timer7: return TIM7_IRQn;
            }
        }();

        /**
         * @brief   Константа RCC для включения тактирования таймера.
         * @details Возвращает:
         *          - RCC_APB2Periph_TIM1 для Timer1;
         *          - RCC_APB1Periph_TIMx для Timer2–Timer4.
         */
        static constexpr uint32_t RCC_Periph = []() -> uint32_t {
            switch (timer_type){
                case TimerTypes::Timer1: return RCC_APB2Periph_TIM1;
                case TimerTypes::Timer2: return RCC_APB1Periph_TIM2;
                case TimerTypes::Timer3: return RCC_APB1Periph_TIM3;
                case TimerTypes::Timer4: return RCC_APB1Periph_TIM4;
                case TimerTypes::Timer6: return RCC_APB1Periph_TIM6;
                case TimerTypes::Timer7: return RCC_APB1Periph_TIM7;
            }
        }();
    };

    }
}


#endif /*   TIMER_DESCRIPTOR_HPP   */