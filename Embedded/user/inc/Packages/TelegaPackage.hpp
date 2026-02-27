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
/**
 * @def     HeaderFirstByte
 * @brief   Первый байт заголовка пакета
 */
#define HeaderFirstByte     0x7E

/**
 * @def     HeaderSecondByte
 * @brief   Второй байт заголовка пакета
 */
#define HeaderSecondByte    0xE7

/**
 * @def     Format
 * @brief   Байт формата пакета
 */
#define Format              0xC8

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------

namespace STM_CppLib{
    namespace STM_Packages{

    /**
     * @brief   Класс пакета данных для протокола "Гиронавт".
     * @details Наследует BasePackage и формирует бинарный пакет фиксированной
     *          структуры. Использует внешние данные через указатели, переданные в конструктор.
     */
    class TelegaPackage: public BasePackage{
    private:
        TriaxialData* acc_data_ptr;     ///< Указатель на внешние данные акселерометра
        TriaxialData* gyro_data_ptr;    ///< Указатель на внешние данные гироскопа
        float* temp_data_ptr;           ///< Указатель на внешнее значение температуры

        /**
         * @brief   Внутренняя структура пакета (упакована без выравнивания).
         * @details Соответствует формату протокола путеизмерительной телеги. Поля:
         *          - header[4]:  фиксированный заголовок (первые три байта константы,
         *                        четвёртый байт – длина полезных данных);
         *          - time:       16-битная временная метка;
         *          - acc_data:   данные акселерометра (TriaxialData);
         *          - gyro_data:  данные гироскопа (TriaxialData);
         *          - temp:       температура (float);
         *          - control_sum: контрольная сумма (8 бит).
         */
        #pragma pack(1)
        struct package_body_t
        {
            uint8_t header[4] = {HeaderFirstByte, HeaderSecondByte, Format, 0};
            uint32_t time = 0;
            TriaxialData acc_data, gyro_data;
            float temp;
            uint8_t control_sum = 0;
        } package_body;
        #pragma pack()

    public:
        /**
         * @brief   Конструктор по умолчанию запрещён (требуются указатели на данные).
         */
        TelegaPackage() = delete;

        /**
         * @brief   Конструктор с указателями на внешние данные.
         * @param   _acc_data_ptr   Указатель на объект TriaxialData для акселерометра.
         * @param   _gyro_data_ptr  Указатель на объект TriaxialData для гироскопа.
         * @param   _temp_data_ptr  Указатель на float для температуры.
         * @note    Переданные указатели должны оставаться валидными на всём
         *          протяжении использования объекта TelegaPackage.
         */
        TelegaPackage(TriaxialData* _acc_data_ptr, TriaxialData* _gyro_data_ptr, float* _temp_data_ptr):
            acc_data_ptr(_acc_data_ptr), gyro_data_ptr(_gyro_data_ptr), temp_data_ptr(_temp_data_ptr){

            // Последним байтом заголовка необходимо задать длину полезных данных:
            // sizeof(time) + 2*sizeof(TriaxialData) + sizeof(float)
            package_body.header[3] = sizeof(package_body) - sizeof(package_body.header) - sizeof(package_body.control_sum);
            
            len = sizeof(package_body);                             ///< Общая длина пакета
            data_ptr = reinterpret_cast<uint8_t*>(&package_body);   ///< Указатель на начало пакета
        }

        /**
         * @brief   Обновить содержимое пакета актуальными данными.
         * @details Копирует текущие значения из внешних объектов во внутреннюю структуру.
         */
        void UpdateData() {
            package_body.acc_data = *acc_data_ptr;
            package_body.gyro_data = *gyro_data_ptr;
            package_body.temp = *temp_data_ptr;
        }

        /**
         * @brief   Обновить временную метку пакета.
         * @param   new_time   Новое значение времени.
         */
        void UpdateTime(uint32_t new_time){
            package_body.time = new_time;
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

    } // namespace STM_Packages
} // namespace STM_CppLib

#endif /*   TELEGA_PACKAGE_HPP   */