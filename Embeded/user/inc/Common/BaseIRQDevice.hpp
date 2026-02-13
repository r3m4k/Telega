/*****************************************************************************
 * @file    BaseIRQDevice.hpp
 * @author  Романовский Роман
 * @brief   Базовый CRTP-класс для привязки прерываний к объектам-обработчикам
 * 
 * @details Предоставляет механизм регистрации пользовательского обработчика
 *          прерывания в таблице векторов _user_vector_table с последующим
 *          перенаправлением вызова на метод irq_handler() класса-наследника.
 *          Использует идиому CRTP для статического полиморфизма.
 *************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef BASE_IRQ_DEVICE_HPP
#define BASE_IRQ_DEVICE_HPP

/* Includes ------------------------------------------------------------------*/
#include "stm32f30x.h"
#include "stm32f30x_misc.h"

#include "Consts.hpp"

/* Defines -------------------------------------------------------------------*/
/**
 * @def     PeriphIRQnBase
 * @brief   Смещение векторов периферии в таблице векторов NVIC (16).
 * @details Первые 16 векторов зарезервированы для системных исключений,
 *          векторы периферии начинаются с 16-го индекса.
 */
#define PeriphIRQnBase          16

/**
 * @def     DefaultIRQChannelPreemptionPriority
 * @brief   Приоритет вытеснения по умолчанию (0 – наивысший).
 */
#define DefaultIRQChannelPreemptionPriority     0

/**
 * @def     DefaultIRQChannelSubPriority
 * @brief   Подприоритет по умолчанию (0).
 */
#define DefaultIRQChannelSubPriority            0

/* Global variables ----------------------------------------------------------*/
/**
 * @var     _user_vector_table
 * @brief   Пользовательская таблица векторов прерываний.

 */
extern _user_pHandler _user_vector_table[];

// -----------------------------------------------------------------------------

namespace STM_CppLib{

/**
 * @brief   Базовый CRTP-класс для привязки прерывания к объекту.
 * 
 * @tparam  IRQDevice   Класс-наследник, реализующий метод irq_handler().
 * @tparam  IRQn        Номер прерывания (IRQn_Type).
 * 
 * @details Обеспечивает регистрацию статического обработчика прерывания
 *          в пользовательской таблице векторов. При срабатывании прерывания
 *          вызывается статический метод static_irq_handler(), который
 *          перенаправляет вызов на метод irq_handler() конкретного
 *          экземпляра класса-наследника, сохранённого в irq_device_ptr.
 */
template <typename IRQDevice, IRQn_Type IRQn>
class BaseIRQDevice{
protected:
    /**
     * @brief   Указатель на активный экземпляр класса-обработчика.
     */
    inline static IRQDevice* irq_device_ptr = nullptr;

    /**
     * @brief   Инициализация прерывания и регистрация обработчика.
     * @param   NVIC_InitStructure_ptr   Указатель на структуру настройки NVIC.
     *                                   Если nullptr, используется конфигурация
     *                                   с приоритетами по умолчанию.
     */
    void InitInterrupt(NVIC_InitTypeDef* NVIC_InitStructure_ptr = nullptr){

        if (!NVIC_InitStructure_ptr){
            NVIC_InitTypeDef NVIC_InitStructure;

            /* Enable the Interrupt */
            NVIC_InitStructure.NVIC_IRQChannel = IRQn;
            NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority = DefaultIRQChannelPreemptionPriority;
            NVIC_InitStructure.NVIC_IRQChannelSubPriority = DefaultIRQChannelSubPriority;
            NVIC_InitStructure.NVIC_IRQChannelCmd = ENABLE;
            NVIC_Init(&NVIC_InitStructure);
        }
        else{   NVIC_Init(NVIC_InitStructure_ptr);  }

        register_interrupt();
    }
    
private:
    /**
     * @brief   Регистрация статического обработчика в таблице векторов.
     */
    void register_interrupt(){
        _user_vector_table[PeriphIRQnBase + IRQn] = static_irq_handler;
    }
    
    /**
     * @brief   Статический обработчик прерывания.
     */
    static void static_irq_handler(){
        irq_device_ptr->irq_handler();
    }
    
};

} // namespace STM_CppLib

#endif /*   BASE_IRQ_DEVICE_HPP   */