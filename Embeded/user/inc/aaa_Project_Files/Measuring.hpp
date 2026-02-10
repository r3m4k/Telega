/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MEASURING_HPP
#define __MEASURING_HPP

/* Includes ------------------------------------------------------------------*/
#include "Leds.hpp"
#include "L3GD20.hpp"
#include "LSM303DLHC.hpp"

#include "DataFilter.hpp"
#include "TwoSigmaFIlter.hpp"
#include "TemperatureFilter.hpp"

#include "TriaxialData.hpp"

/* Defines -------------------------------------------------------------------*/

/* Usings  -------------------------------------------------------------------*/
using Filter = TwoSigmaFIlter;

/* Global variables ----------------------------------------------------------*/
extern STM_CppLib::Leds leds;
extern STM_CppLib::L3GD20 gyro_sensor;
extern STM_CppLib::LSM303DLHC acc_sensor;


// -----------------------------------------------------------------------------
// Класс для реализации чтения и обработки данных с датчиков 
class Measuring{

    // ########################################################################

    Filter acc_filter;              // Фильтр для данных акселерометра
    TriaxialData acc_filtered;      // Отфильтрованные данные акселерометра

    Filter gyro_filter;             // Фильтр для данных гироскопа
    TriaxialData gyro_filtered;     // Отфильтрованные данные гироскопа
   
#ifdef USE_MAGNETIC_SENSOR
    Filter mag_filter;              // Фильтр для данных магнитометра
    TriaxialData mag_filtered;      // Отфильтрованные данные магнитометра
#endif /*   USE_MAGNETIC_SENSOR   */

#ifdef USE_TEMPERATURE_SENSOR
    TemperatureFilter temp_filter;  // Фильтр для данных температурного датчика
    float temp_filtered;            // Отфильтрованные данные температурного датчика
#endif /*    USE_TEMPERATURE_SENSOR   */

    // ########################################################################

public:

    // ########################################################################

    Measuring(){}
    ~Measuring(){}

    // ########################################################################
    void collect_data(){
        // --------------------------------------------------------------------
        // Сбросим все фильтры перед началом сбора данных
        acc_filter.reset();
        gyro_filter.reset();
    
    #ifdef USE_MAGNETIC_SENSOR
        mag_filter.reset();
    #endif /*   USE_MAGNETIC_SENSOR   */

    #ifdef USE_TEMPERATURE_SENSOR
        temp_filter.reset();
    #endif /*    USE_TEMPERATURE_SENSOR   */

        // --------------------------------------------------------------------
        // Прочитаем данные датчиков
        while(acc_filter.data_len != acc_filter.filter_size){

            acc_sensor.ReadData();
            gyro_sensor.ReadData();

            // Добавим данные в соответствующие фильтры
            acc_filter.append_data(acc_sensor.acc_data);
            gyro_filter.append_data(gyro_sensor.gyro_data);

        #ifdef USE_MAGNETIC_SENSOR
            mag_filter.append_data(acc_sensor.mag_data);
        #endif /*   USE_MAGNETIC_SENSOR   */

        #ifdef USE_TEMPERATURE_SENSOR
            temp_filter.append_data(acc_sensor.temperature);
        #endif /*    USE_TEMPERATURE_SENSOR   */

        }

        // --------------------------------------------------------------------
        // Сохраним отфильтрованные значения
        acc_filtered = acc_filter.get_filtered_data();
        gyro_filtered = gyro_filter.get_filtered_data();

    #ifdef USE_MAGNETIC_SENSOR
        mag_filtered = mag_filter.get_filtered_data();
    #endif /*   USE_MAGNETIC_SENSOR   */

    #ifdef USE_TEMPERATURE_SENSOR
        temp_filtered = temp_filter.get_filtered_data();
    #endif /*    USE_TEMPERATURE_SENSOR   */

    }

    // ########################################################################
    void send_data(){

    }


};

#endif /*   __MEASURING_HPP   */