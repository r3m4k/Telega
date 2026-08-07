/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __L3GD20_HPP
#define __L3GD20_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

#include "stm32f30x.h"
#include "stm32f3_discovery_l3gd20.h"
#include "TriaxialData.hpp"
#include "SensorScaler.hpp"
#include "GpioPin.hpp"

/* Defines -------------------------------------------------------------------*/
#define INDICATE_L3GD20_READING
#define TrueAbsGyroVal  4.178074

// -----------------------------------------------------------------------------
namespace STM_CppLib{

    // -------------------------------------------------------------------------
    // Класс для работы с гироскопом L3GD20
    class L3GD20{

    public:

        /* --------------------------------------------
        * В соответствии с документацией на L3GD20:
        * OX = ox
        * OY = oy
        * OZ = oz
        * ------------------------------------------ */
        TriaxialData gyro_data;     // [миллиградус/сек]

    private:
        float gyro_multiplier;          // [mdps/digit]
        float gyro_scale_rate = 1.0f;    // Масштабирующий коэффициент

    #ifdef INDICATE_L3GD20_READING
        
        // Пин для индикации чтения данных гироскопа
        using PinIndicator_GyroReading_t = STM_CppLib::STM_GPIO::GPIO_Pin
            <STM_CppLib::STM_GPIO::GPIO_Port::PortB, GPIO_PinSource10>;
        PinIndicator_GyroReading_t gyro_reading_indicator_pin;

    #endif  /*  INDICATE_L3GD20_READING   */
    
        // ---------------------------------------------------------------------
        // Методы класса
        // ---------------------------------------------------------------------

    public:
        void Init(){
            // ----------------------------------------------------------------
            // Структуры для конфигурации
            L3GD20_InitTypeDef InitStruct;
            L3GD20_FilterConfigTypeDef FilterStruct;

            // ----------------------------------------------------------------
            // Сконфигурируем параметры гироскопа
            InitStruct.Power_Mode = L3GD20_MODE_ACTIVE;                     /* Power-down/Sleep/Normal Mode */
            InitStruct.Output_DataRate = L3GD20_OUTPUT_DATARATE_3;          /* OUT data rate */
            InitStruct.Band_Width = L3GD20_BANDWIDTH_3;                     /* Bandwidth selection */
            InitStruct.Axes_Enable = L3GD20_AXES_ENABLE;                    /* Axes enable */
            InitStruct.BlockData_Update = L3GD20_BlockDataUpdate_Continous; /* Block Data Update */
            InitStruct.Endianness = L3GD20_BLE_LSB;                         /* Endian Data selection */
            InitStruct.Full_Scale = L3GD20_FULLSCALE_250;                   /* Full Scale selection */

            L3GD20_Init(&InitStruct);

            // Выбранные Output_DataRate и Band_Width соответствуют частоте обновления данных в 760 Гц

            // ----------------------------------------------------------------
            // Сконфигурируем параметры встроенного фильтра гироскопа
            FilterStruct.HighPassFilter_Mode_Selection = L3GD20_HPM_NORMAL_MODE; /* Internal filter mode */
            FilterStruct.HighPassFilter_CutOff_Frequency = L3GD20_HPFCF_5;       /* High pass filter cut-off frequency */

            L3GD20_FilterConfig(&FilterStruct);

            // ----------------------------------------------------------------
            // Зададим множитель для гироскопа в соответствии с документацией
            // (см. документацию для L3GD20, таблица 3 "Mechanical characteristics", стр. 9)
            switch (InitStruct.Full_Scale)
            {
            case L3GD20_FULLSCALE_250:
                gyro_multiplier = 8.75;      // [mdps/digit] -> [dps/digit]
                break;

            case L3GD20_FULLSCALE_500:
                gyro_multiplier = 17.5;      // [mdps/digit] -> [dps/digit]
                break;    

            case L3GD20_FULLSCALE_2000:
                gyro_multiplier = 70.0;      // [mdps/digit] -> [dps/digit]
                break; 
            }

        #ifdef INDICATE_L3GD20_READING
            // Проинициализируем пин-индикатор и принудительно сбросим его
            gyro_reading_indicator_pin.InitPin();
            gyro_reading_indicator_pin.ResetPin();
        #endif  /*  INDICATE_L3GD20_READING   */
        }

        void InitGyroScaller(){
            // Вычислим масштабирующий коэффициент для угловой скорости
            SensorScaller<L3GD20> gyro_scaller{this, &gyro_data, TrueAbsGyroVal};
            gyro_scaller.Init();
            gyro_scale_rate = gyro_scaller.scale_rate;
        }

        // Метод необходим для использования L3GD20 в качестве шаблонного параметра
        void ReadData(){
            ReadGyro();
        }

        void ReadGyro(){
        #ifdef INDICATE_L3GD20_READING
            gyro_reading_indicator_pin.SetPin();
        #endif  /*  INDICATE_L3GD20_READING   */

            uint8_t high_bit = 0;
            uint8_t low_bit = 0;
            
            // x_coord
            L3GD20_Read(&high_bit, L3GD20_OUT_X_H_ADDR, 1);
            L3GD20_Read(&low_bit,  L3GD20_OUT_X_L_ADDR, 1);
            gyro_data.x_coord = static_cast<float>(static_cast<int16_t>(high_bit << 8) + low_bit) * gyro_multiplier;
            
            // y_coord
            L3GD20_Read(&high_bit, L3GD20_OUT_Y_H_ADDR, 1);
            L3GD20_Read(&low_bit,  L3GD20_OUT_Y_L_ADDR, 1);
            gyro_data.y_coord = static_cast<float>(static_cast<int16_t>(high_bit << 8) + low_bit) * gyro_multiplier;
            
            // z_coord
            L3GD20_Read(&high_bit, L3GD20_OUT_Z_H_ADDR, 1);
            L3GD20_Read(&low_bit,  L3GD20_OUT_Z_L_ADDR, 1);
            gyro_data.z_coord = static_cast<float>(static_cast<int16_t>(high_bit << 8) + low_bit) * gyro_multiplier;

            gyro_data *= gyro_scale_rate;

        #ifdef INDICATE_L3GD20_READING
            gyro_reading_indicator_pin.ResetPin();
        #endif  /*  INDICATE_L3GD20_READING   */
        }
    };

}

#endif /*   __L3GD20_HPP   */