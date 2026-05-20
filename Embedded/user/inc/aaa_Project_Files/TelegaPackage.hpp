/**
 * @file    TelegaPackage.hpp
 * @author  Романовский Роман
 * @brief   Формирование пакета данных с путеизмерительной телеги.
 * @details Содержит класс TelegaPackage, наследующий BasePackage, для упаковки
 *          данных с датчиков в бинарный формат, соответствующий протоколу.
 */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef TELEGA_PACKAGE_HPP
#define TELEGA_PACKAGE_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

#include "BasePackage.hpp"
#include "TriaxialData.hpp"

/* Defines -------------------------------------------------------------------*/

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------

namespace Packages{

    /**
     * @brief   Класс пакета данных для протокола "Гиронавт".
     * @details Наследует BasePackage и формирует бинарный пакет фиксированной
     *          структуры. Использует внешние данные через указатели, переданные в конструктор.
     */
    class TelegaPackage: public BasePackage{
    private:
        /**
         * @def     DataFormat
         * @brief   Байт формата пакета
         */
        static constexpr uint8_t DataFormat = 0xC8;

        uint32_t* time_ptr;             ///< Указатель на внешний счётчик таймера
        TriaxialData* acc_data_ptr;     ///< Указатель на внешние данные акселерометра
        TriaxialData* gyro_data_ptr;    ///< Указатель на внешние данные гироскопа
        float* temp_data_ptr;           ///< Указатель на внешнее значение температуры
        int32_t* dpp_code_ptr;          ///< Указатель на внешнее значение кода ДПП

        /**
         * @brief   Внутренняя структура пакета (упакована без выравнивания).
         * @details Соответствует формату протокола путеизмерительной телеги. Поля:
         *          - header[4]:  фиксированный заголовок (первые три байта константы,
         *                        четвёртый байт – длина полезных данных);
         *          - time:       32-битный счётчик пакетов;
         *          - acc_data:   данные акселерометра (TriaxialData);
         *          - gyro_data:  данные гироскопа (TriaxialData);
         *          - temp:       температура (float);
         *          - control_sum: контрольная сумма (8 бит).
         */
        #pragma pack(1)
        struct package_body_t
        {
            uint8_t header[4] = {BasePackage::HeaderFirstByte, 
                                 BasePackage::HeaderSecondByte, 
                                 DataFormat, 0};
            uint32_t time = 0;
            TriaxialData acc_data, gyro_data;
            float temp;
            int32_t dpp_code;
            uint8_t control_sum = 0;
        } package_body;
        #pragma pack()

        static_assert(sizeof(package_body_t) <= 64,
            "TelegaPackage: structure package_body_t exceeds 64 bytes.\n"
            "Either increase the buffer size in hw_config.c or reduce the structure size.");

    public:
        /**
         * @brief   Конструктор по умолчанию запрещён (требуются указатели на данные).
         */
        TelegaPackage() = delete;

        /**
         * @brief   Конструктор с указателями на внешние данные.
         * @param   _acc_data_ptr   Указатель на объект uint32_t для времени.
         * @param   _acc_data_ptr   Указатель на объект TriaxialData для акселерометра.
         * @param   _gyro_data_ptr  Указатель на объект TriaxialData для гироскопа.
         * @param   _temp_data_ptr  Указатель на float для температуры.
         * @param   _dpp_code_ptr   Указатель на int32_t для кода ДПП.
         * @note    Переданные указатели должны оставаться валидными на всём
         *          протяжении использования объекта TelegaPackage.
         */
        TelegaPackage(
            uint32_t* _time_ptr, TriaxialData* _acc_data_ptr, 
            TriaxialData* _gyro_data_ptr, float* _temp_data_ptr, int32_t* _dpp_code_ptr
        ):
            time_ptr(_time_ptr), acc_data_ptr(_acc_data_ptr), 
            gyro_data_ptr(_gyro_data_ptr), temp_data_ptr(_temp_data_ptr), dpp_code_ptr(_dpp_code_ptr)
        {
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
            package_body.time = *time_ptr;
            package_body.acc_data = *acc_data_ptr;
            package_body.gyro_data = *gyro_data_ptr;
            package_body.temp = *temp_data_ptr;
            package_body.dpp_code = *dpp_code_ptr;
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

#endif /*   TELEGA_PACKAGE_HPP   */