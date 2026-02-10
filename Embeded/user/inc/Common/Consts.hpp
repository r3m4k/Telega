/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __CONSTS_HPP
#define __CONSTS_HPP

/* Includes ------------------------------------------------------------------*/
#include "stm32f30x.h"
#include "stm32f30x_rcc.h"

/* Defines -------------------------------------------------------------------*/

// ----------------------------------------------------------------------------

using __user_pHandler = void (*)(void);

namespace STM_CppLib{
    using handler_t = void(*)(void);
    using RCC_PeriphClockCmd_Type = void (*)(uint32_t, FunctionalState);
}

#endif /*   __CONSTS_HPP   */