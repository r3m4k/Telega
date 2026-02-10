/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __SENSOR_DATA_FILTER_HPP
#define __SENSOR_DATA_FILTER_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>
#include "TriaxialData.hpp"

/* Defines -------------------------------------------------------------------*/
#define FILTER_SIZE     

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------
// Базовый класс для работы с данными с датчиков
template <typename T>
class SensorDataFilter{
public:
    static constexpr uint8_t filter_size;   // Размер фильтра
    T data_array[filter_size];              // Массив для сохранения данных
    uint8_t data_len;                       // Количество сохранённых данных 

    virtual DataFilter() data_len(0) {};
    virtual ~DataFilter() = default;
    
    virtual T get_filtered_data() = 0;

    void append_data(T data){
        // TODO: наверное надо сделать проверку и при переполнении как-то отображать это
        data_array[data_len++] = data;
    }

    void reset(){   data_len = 0;   }
};

#endif /*   __SENSOR_DATA_FILTER_HPP   */