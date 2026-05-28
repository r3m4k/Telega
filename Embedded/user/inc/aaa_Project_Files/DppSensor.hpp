/** ****************************************************************************
 * @file    DppSensor.hpp
 * @author  Романовский Роман
 * @brief   Драйвер датчика пройденного пути.
 * @details Содержит шаблонный класс DppSensor для подсчета импульсов ДПП.
 *          Передний фронт входа импульсов обрабатывается внешним прерыванием,
 *          направление движения определяется по уровню второго входа.
 **************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef DPP_SENSOR_HPP
#define DPP_SENSOR_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

#include "GpioPin.hpp"

/* Defines -------------------------------------------------------------------*/

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------

namespace Dpp
{
    /**
     * @brief   Шаблонный класс датчика пройденного пути.
     * @tparam  PinPulse      Тип пина входа импульсов ДПП.
     * @tparam  PinDirection  Тип пина входа направления движения.
     * @details PinPulse настраивается как вход с EXTI по переднему фронту.
     *          PinDirection настраивается как обычный вход. При обработке фронта:
     *          - PinDirection == 0: dpp_code увеличивается;
     *          - PinDirection == 1: dpp_code уменьшается.
     */
    template <STM_CppLib::STM_GPIO::GpioPinExtiConcept PinPulse,
              STM_CppLib::STM_GPIO::GpioPinConcept PinDirection>
    class DppSensor{
    private:
        PinPulse pin_pulse;            ///< Вход импульсов ДПП
        PinDirection pin_direction;    ///< Вход направления движения
        uint8_t prev_state = Bit_SET;   // Прошлое состояние pin_pulse

    public:
        int32_t dpp_code;              ///< Текущий код пройденного пути

        /**
         * @brief   Конструктор по умолчанию.
         */
        DppSensor(): dpp_code(0) {}

        /**
         * @brief   Деструктор по умолчанию.
         */
        ~DppSensor() = default;

        /**
         * @brief   Инициализация входов датчика.
         * @details Вход импульсов настраивается как EXTI по переднему фронту,
         *          вход направления - как обычный GPIO-вход.
         */
        void Init(){
            pin_pulse.InitPinExti(GPIO_Mode_IN, GPIO_PuPd_UP);
            pin_direction.InitPin(GPIO_Mode_IN, GPIO_PuPd_UP);
            prev_state = pin_pulse.ReadPin();  // Запоминаем начальное состояние
        }

        /**
         * @brief   Обработка переднего фронта входа импульсов.
         * @details Метод должен вызываться из обработчика EXTI входа PinPulse.
         */
        void process_front(){
            uint8_t current_state = pin_pulse.ReadPin();
            bool state_changed = (current_state != prev_state);
            prev_state = current_state;

            if (state_changed && (current_state == Bit_SET)){
                if (pin_direction.ReadPin() == Bit_RESET){
                    dpp_code++;
                }
                else{
                    dpp_code--;
                }
            }
        }

        /**
         * @brief   Сброс кода пройденного пути.
         */
        void reset(){
            dpp_code = 0;
        }
    };

} // namespace Dpp

#endif /*   DPP_SENSOR_HPP   */
