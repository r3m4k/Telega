/** ***************************************************************************
 * @file    UsartConfig.hpp
 * @author  Романовский Роман
 * @brief   Структура конфигурации USART для STM32F30x
 *
 * @details Содержит структуру UsartConfig, описывающую настраиваемые
 *          параметры модуля USART: скорость передачи, длину слова, количество
 *          стоп-битов, проверку чётности, режим работы и аппаратное управление
 *          потоком. Используется в методах инициализации класса Usart.
 *************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef USART_CONFIG_HPP
#define USART_CONFIG_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

#include "main.h"
#include "stm32f30x.h"
#include "stm32f30x_usart.h"

#include "Consts.hpp"

/* Defines -------------------------------------------------------------------*/

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------
namespace STM_CppLib{
    namespace STM_Usart{

    /**
     * @brief   Структура для настройки USART.
     * @details Содержит все параметры, передаваемые в USART_InitTypeDef.
     *          Пользователь может создать структуру вручную и передать её
     *          в метод Init() класса Usart, либо воспользоваться конфигурацией
     *          по умолчанию (см. параметры по умолчанию в Usart::Init).
     */
    struct UsartConfig{
        uint32_t BaudRate;              ///< Скорость передачи (бит/с)
        uint32_t WordLength;            ///< Длина слова: USART_WordLength_8b / _9b
        uint32_t StopBits;              ///< Стоп-биты: USART_StopBits_1 / _0_5 / _2 / _1_5
        uint32_t Parity;                ///< Чётность: USART_Parity_No / _Even / _Odd
        uint32_t Mode;                  ///< Режим: USART_Mode_Rx | USART_Mode_Tx
        uint32_t HardwareFlowControl;   ///< Аппаратное управление потоком
    };

    } // namespace STM_Usart
} // namespace STM_CppLib

#endif /*   USART_CONFIG_HPP   */
