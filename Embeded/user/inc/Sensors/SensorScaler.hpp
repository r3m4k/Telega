/** ****************************************************************************
 * @file SensorScaller.hpp
 * @brief Шаблонный класс для адаптивного масштабирования данных трёхосевых 
 * датчиков
 * @details Реализует алгоритм динамического усреднения зашумлённых данных
 * с автоматическим определением оптимального количества измерений
 * 
 * @version 1.0.0
 * @date Январь 2026
 * @author Романовский Роман
 **************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __SENSOR_SCALLER_HPP
#define __SENSOR_SCALLER_HPP

/* Includes ------------------------------------------------------------------*/
#include <concepts>
#include <stdint.h>
#include <math.h>

#include "TriaxialData.hpp"

/* Defines -------------------------------------------------------------------*/
#define BUFFER_SIZE     1000

/* Global variables ----------------------------------------------------------*/

/** ****************************************************************************
 * @brief Концепт проверки наличия метода ReadData() с возвращаемым типом void
 * @tparam S Тип датчика для проверки
 * @concept HasVoidReadData
 * @requires Метод S::ReadData() должен существовать и возвращать void
 **************************************************************************** */

template<typename S>
concept HasVoidReadData = requires(S s) {
    s.ReadData();
} && std::is_void_v<decltype(std::declval<S>().ReadData())>;


/** ****************************************************************************
 * @brief Шаблонный класс для адаптивного масштабирования данных трёхосевых датчиков
 * @tparam Sensor Тип датчика, должен удовлетворять концепту HasVoidReadData
 * 
 * @details Класс реализует алгоритм динамического усреднения, который:
 * 1. Собирает начальный буфер измерений для оценки уровня шума
 * 2. Вычисляет масштабирующий коэффициент на основе априорного значения
 * 
 * @note Все статистические вычисления выполняются методом Уэлфорда
 **************************************************************************** */

template<typename Sensor>
class SensorScaller{

    // -------------------------------------------------------------------------
    // Проверка при компиляции наличия метода ReadData() у Sensor
    // -------------------------------------------------------------------------

    static_assert(HasVoidReadData<Sensor>,
        "\n=== SENSOR INTERFACE ERROR ===\n"
        "Sensor type must provide: void ReadData()\n"
        "===============================\n");

    // -------------------------------------------------------------------------
    // Поля класса
    // -------------------------------------------------------------------------

private:
    Sensor* sensor_ptr;         // Указатель на используемый датчик
    TriaxialData* data_ptr;     // Указатель на 3-х осевые данные с датчиков
    float true_abs_value;       // Априорное абсолютное значение измеряемой датчиком величины

    uint32_t counter;           // Счётчик прочитанных величин
    TriaxialData mean_value;    // Среднее значение по координатам
    // TriaxialData variance;      // Дисперсия по координатам

public:

    float scale_rate = 1.0f;    // Значение нормировочного коэффициента

    // -------------------------------------------------------------------------
    // Методы класса
    // -------------------------------------------------------------------------

    SensorScaller() = delete;
    SensorScaller(Sensor* _sensor_ptr, TriaxialData* _data_ptr, float _abs_value):
        sensor_ptr(_sensor_ptr), data_ptr(_data_ptr), true_abs_value(_abs_value),
        counter{0}, mean_value{} {}

    void Init(){
        // Считаем BUFFER_SIZE значений
        while(counter < BUFFER_SIZE){
            sensor_ptr->ReadData();
            append_value(*data_ptr);
        }

        // // Считываем данные, пока не выполнится условие
        // float target_variance = TARGET_SIGMA_COEFF * TARGET_SIGMA_COEFF * abs_value(variance);
        // while (abs_value(variance) > target_variance){
        //     sensor_ptr->ReadData();
        //     append_value(*data_ptr);
        // }

        // Вычисляем scale_rate
        scale_rate = true_abs_value / abs_value(mean_value);        
    }

private:

    // Вычисление среднего значения и дисперсии по методу Уэлфорда 
    void append_value(const TriaxialData& val){
        mean_value += (val - mean_value) / (++counter);
        // variance += (val - mean_value) * (val - mean_value);
    }

    // Вычисление абсолютного значения TriaxialData
    float abs_value(const TriaxialData& val){
        return sqrtf(val.x_coord * val.x_coord + val.y_coord * val.y_coord + val.z_coord * val.z_coord);
    }
    
};

#endif /*   __SENSOR_SCALLER_HPP   */