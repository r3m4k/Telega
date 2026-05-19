/** ***************************************************************************
 * @file    BaseTimer.hpp
 * @author  Романовский Роман
 * @brief   Базовые классы для работы с таймерами STM32F30x
 * @details Содержит:
 *          - предопределённые значения предделителей для частот 1, 10, 100 кГц;
 *          - базовый класс BaseTimer для аппаратного управления таймером;
 *************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef BASE_TIMER_HPP
#define BASE_TIMER_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

#include "stm32f30x.h"
#include "stm32f30x_rcc.h"
#include "stm32f30x_misc.h"
#include "stm32f30x_tim.h"

#include "TimerConfig.hpp"

/* Defines -------------------------------------------------------------------*/
/**
 * @def     Prescaler_1kHz
 * @brief   Предделитель для получения частоты счёта 1 кГц
 */
#define     Prescaler_1kHz         72000 - 1

/**
 * @def     Prescaler_10kHz
 * @brief   Предделитель для частоты счёта 10 кГц
 */
#define     Prescaler_10kHz        7200 - 1

/**
 * @def     Prescaler_100kHz
 * @brief   Предделитель для частоты счёта 100 кГц
 */
#define     Prescaler_100kHz       720 - 1

/**
 * @def     Prescaler_1MHz
 * @brief   Предделитель для частоты счёта 1 МГц
 */
#define     Prescaler_1MHz          72 - 1

/**
 * @def     Prescaler_2MHz
 * @brief   Предделитель для частоты счёта 2 МГц
 */
#define     Prescaler_2MHz          36 - 1

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------

namespace STM_CppLib{
    namespace STM_Timer{
    
    // -------------------------------------------------------------------------
    /**
     * @brief   Базовый класс для аппаратного управления таймером.
     * @details Инкапсулирует указатель на структуру TIM_TypeDef и предоставляет
     *          методы инициализации, пуска, останова и сброса счётчика.
     *          Не предназначен для прямого использования – служит основой
     *          для классов-наследников.
     */
    class BaseTimer{
    protected:
        /**
         * @brief   Указатель на регистровую структуру таймера
         */
        TIM_TypeDef* TIMx;

    public:
        /**
         * @brief   Конструктор по умолчанию.
         * @details Инициализирует TIMx = nullptr.
         */
        BaseTimer(): TIMx(nullptr) {}

        /**
         * @brief   Деструктор.
         * @details Отключает прерывание по обновлению и выключает таймер.
         */
        ~BaseTimer(){
            if (TIMx) {
                TIM_ITConfig(TIMx, TIM_IT_Update, DISABLE);
                TIM_Cmd(TIMx, DISABLE);
            }
        };

        /**
         * @brief   Инициализация базовых параметров таймера.
         * @param   timer_config   Указатель на структуру TimerConfig, содержащую:
         *                         - функцию включения тактирования (PeriphClockCmd);
         *                         - константу RCC (RCC_PeriphClock);
         *                         - значение предделителя (TimPrescaler);
         *                         - период счёта (TimPeriod).
         * @details Включает тактирование таймера, инициализирует регистры
         *          предделителя и автоперезагрузки через TIM_TimeBaseInit.
         */
        void InitBaseTimer(TimerConfig* timer_config){
            TIM_TimeBaseInitTypeDef TIM_TimeBaseStructure;

            timer_config->PeriphClockCmd(timer_config->RCC_PeriphClock, ENABLE);

            TIM_TimeBaseStructInit(&TIM_TimeBaseStructure);
            TIM_TimeBaseStructure.TIM_Period = timer_config->TimPeriod;
            TIM_TimeBaseStructure.TIM_Prescaler = timer_config->TimPrescaler;
            TIM_TimeBaseInit(TIMx, &TIM_TimeBaseStructure);
        }
        
        /**
         * @brief   Запуск таймера.
         * @details Разрешает прерывание по событию обновления (Update) и
         *          включает счёт таймера (TIM_Cmd(ENABLE)).
         */
        void Start() {
            if (!TIMx) return;
            TIM_ITConfig(TIMx, TIM_IT_Update, ENABLE);
            TIM_Cmd(TIMx, ENABLE);
        }

        /**
         * @brief   Останов таймера.
         * @details Запрещает прерывание по событию обновления и выключает счёт таймера.
         */
        void Stop() {
            if (!TIMx) return;
            TIM_ITConfig(TIMx, TIM_IT_Update, DISABLE);
            TIM_Cmd(TIMx, DISABLE);
        }

        /**
         * @brief   Сброс счётчика таймера.
         * @details Устанавливает регистр CNT в 0.
         */
        void ResetCounter() {
            if (TIMx) TIMx->CNT = 0;
        }
    };

    } // namespace STM_Timer
} // namespace STM_CppLib


#endif /*   BASE_TIMER_HPP   */