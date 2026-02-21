/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __BASE_PACKAGE_HPP
#define __BASE_PACKAGE_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

/* Defines -------------------------------------------------------------------*/

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------
namespace STM_CppLib{
    namespace STM_Packages{

    // -------------------------------------------------------------------------
    /* Класс для описания базового пакета информации
    *  Виртуальные функции закомментированы, чтобы не создавать vtable, тем не 
    *  менее эти методы необходимо реализовать в дочерних классах для 
    *  удобства работы.
    *  Для отправки посылки по интерфейсу связи нужен доступ только к data_ptr 
    *  и len, которые необходимо определить в дочернем классе.
    *  ---------------------------------------------------------------------- */
    class BasePackage{
        // virtual void DataPackaging() = 0;
        // virtual uint8_t CountControlSum() = 0;

    public:
        uint8_t *data_ptr;
        uint8_t len;

        BasePackage(): data_ptr(nullptr), len(0) {}
        ~BasePackage(){};

        // virtual void UpdateData() = 0;

    };

    } // namespace STM_Packages
} // namespace STM_CppLib
#endif /*   __BASE_PACKAGE_HPP   */