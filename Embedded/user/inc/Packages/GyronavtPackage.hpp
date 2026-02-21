/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __GYRONAVT_PACKAGE_HPP
#define __GYRONAVT_PACKAGE_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

#include "BasePackage.hpp"
#include "TriaxialData.hpp"

/* Defines -------------------------------------------------------------------*/
#define Preamble            0xFB
#define DevAdr              0x01
#define RegAdr              0xFF

#define BarConst            3.14159f
#define DefaultStatus       0x32

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------

namespace STM_CppLib{
    namespace STM_Packages{

    // ------------------------------------    
    // Посылка, согласно протоколу Гиронавт
    class GyronavtPackage: public BasePackage{
    private:
        TriaxialData* acc_data_ptr;
        TriaxialData* gyro_data_ptr;
        TriaxialData* mag_data_ptr;

        #pragma pack(1)
        struct package_body_t
        {
            uint8_t header[4] = {Preamble, DevAdr, RegAdr, 0};
            uint32_t time = 0;
            uint8_t status = DefaultStatus;
            uint8_t hole[3] = {0};
            TriaxialData acc_data, gyro_data, mag_data;            
            float bar = BarConst;
            uint8_t control_sum = 0;
        } package_body;
        #pragma pack()

        static_assert(
            (sizeof(package_body) - sizeof(package_body.header) - sizeof(package_body.control_sum)) == 48,
            "Incorrect length of data inside the Gyronavt package"
        );

    public:
        GyronavtPackage() = delete;
        GyronavtPackage(TriaxialData* _acc_data_ptr, TriaxialData* _gyro_data_ptr, TriaxialData* _mag_data_ptr):
            acc_data_ptr(_acc_data_ptr), gyro_data_ptr(_gyro_data_ptr), mag_data_ptr(_mag_data_ptr){
            // Последним байтом заголовка необходимо задать длину данных внутри посылки
            package_body.header[3] = 12;   // На стороне приёмника len = (bt & 0x7f) * 4;;
            
            len = sizeof(package_body);
            data_ptr = reinterpret_cast<uint8_t*>(&package_body);
        }

        void UpdateData() {
            package_body.acc_data = *acc_data_ptr;
            package_body.gyro_data = *gyro_data_ptr;
            package_body.mag_data = *mag_data_ptr;
        }

        void UpdateTime(uint32_t new_time){
            package_body.time = new_time;
        }

        void UpdateControlSum(){
            package_body.control_sum = CountControlSum();
        }
        
    private:

        // Вычисление контрольной суммы согласно документации
        uint8_t CountControlSum(){

            uint8_t crc = 0xFF;
           
            // Условие len-1 необходимо, чтобы не учитывать в расчёте контрольной суммы
            // не учитывать старое значение контрольной суммы
            for (uint8_t i = 0; i < len - 1; i++){
                crc ^= data_ptr[i];
                for(uint8_t j = 0; j < 8; j++)
                    crc = crc & 0x80 ? (crc << 1) ^ 0x31 : crc << 1;
            }
            return crc;
        }        
    };

    } // namespace STM_Packages
} // namespace STM_CppLib

#endif /*   __GYRONAVT_PACKAGE_HPP   */