/** ****************************************************************************
 * @file    PackageImuData.hpp
 * @author  Романовский Роман
 * @brief   Формирование пакета данных с акселерометра и гироскопа.
 * @details Содержит класс PackageImuData, наследующий BasePackage, для упаковки
 *          данных с датчиков в бинарный формат, соответствующий протоколу.
 **************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef IMU_DATA_PACKAGE_HPP
#define IMU_DATA_PACKAGE_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>
#include "BasePackage.hpp"
#include "TriaxialData.hpp"

/* Defines -------------------------------------------------------------------*/

/* Global variables ----------------------------------------------------------*/
extern volatile uint32_t tick_counter;

// -----------------------------------------------------------------------------

namespace Packages{

    /**
     * @brief   Класс пакета данных с инерциальных датчиков.
     * @details Наследует BasePackage и формирует бинарный пакет фиксированной
     *          структуры. Использует внешние данные через указатели, переданные в конструктор.
     */
    class PackageImuData: public BasePackage{
    private:
        /**
         * @def     DataFormat
         * @brief   Байт формата пакета
         */
        static constexpr uint8_t DataFormat = 0x01;

        TriaxialData* acc_data_ptr;     ///< Указатель на внешние данные акселерометра
        TriaxialData* gyro_data_ptr;    ///< Указатель на внешние данные гироскопа

        /**
         * @brief   Внутренняя структура пакета.
         * @details Соответствует формату протокола путеизмерительной телеги. Поля:
         *          - header[4]:   фиксированный заголовок (первые три байта константы,
         *                         четвёртый байт – длина полезных данных);
         *          - package_num: 32-битный счётчик пакетов;
         *          - acc_data:    данные акселерометра (TriaxialData);
         *          - gyro_data:   данные гироскопа (TriaxialData);
         *          - control_sum: контрольная сумма.
         */
        #pragma pack(1)
        struct package_body_t
        {
            uint8_t header[4] = {BasePackage::HeaderFirstByte, 
                                 BasePackage::HeaderSecondByte, 
                                 DataFormat, 0};
            uint32_t package_num = 0;
            TriaxialData acc_data, gyro_data;
            uint8_t control_sum = 0;
        } package_body;
        #pragma pack()

        static_assert(sizeof(package_body_t) <= 64,
              "PackageImuData: structure package_body_t exceeds 64 bytes.\n"
              "Either increase the buffer size in hw_config.c or reduce the structure size.");

    public:
        /**
         * @brief   Конструктор по умолчанию запрещён (требуются указатели на данные).
         */
        PackageImuData() = delete;

        /**
         * @brief   Конструктор с указателями на внешние данные.
         * @param   _acc_data_ptr   Указатель на объект TriaxialData для акселерометра.
         * @param   _gyro_data_ptr  Указатель на объект TriaxialData для гироскопа.
         * @note    Переданные указатели должны оставаться валидными на всём
         *          протяжении использования объекта PackageImuData.
         */
        PackageImuData(TriaxialData* _acc_data_ptr, TriaxialData* _gyro_data_ptr):
            acc_data_ptr(_acc_data_ptr), gyro_data_ptr(_gyro_data_ptr){

            // Последним байтом заголовка необходимо задать длину полезных данных:
            package_body.header[3] = sizeof(package_body) - sizeof(package_body.header) - sizeof(package_body.control_sum);
            
            len = sizeof(package_body);                             ///< Общая длина пакета
            data_ptr = reinterpret_cast<uint8_t*>(&package_body);   ///< Указатель на начало пакета
        }

        /**
         * @brief   Обновить содержимое пакета актуальными данными.
         * @details Копирует текущие значения из внешних объектов во внутреннюю структуру.
         */
        void UpdateData() {
            package_body.package_num = tick_counter;
            package_body.acc_data = *acc_data_ptr;
            package_body.gyro_data = *gyro_data_ptr;
        }

        /**
         * @brief   Пересчитать и обновить контрольную сумму пакета.
         * @details Вызывает CountControlSum() и сохраняет результат в поле control_sum.
         */
        void UpdateControlSum(){
            package_body.control_sum = CountControlSum();
        }
        
    private:
        /**
         * @brief   Вычисление контрольной суммы пакета.
         * @return  uint8_t   Сумма всех байтов пакета, кроме байта самой контрольной суммы.
         * @details Проходит по всем байтам data_ptr,
         *          накапливает сумму в 16-битной переменной и возвращает младший байт.
         */
        uint8_t CountControlSum(){
            uint16_t crc = 0;
            // Исключаем последний байт (собственно контрольную сумму)
            for (uint8_t i = 0; i < len - 1; i++){
                crc += data_ptr[i];
            }
            return static_cast<uint8_t>(crc);
        }        
    };

} // namespace Packages

#endif /*   IMU_DATA_PACKAGE_HPP   */