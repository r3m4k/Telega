/* Define to prevent recursive inclusion ------------------------------------*/
#ifndef __MAIN_H
#define __MAIN_H

/* --------------------------------------------------------------------------*/

#ifdef __cplusplus
 extern "C" {
#endif 

/* Includes Global files ----------------------------------------------------*/
#include <math.h>
#include <stdlib.h>
#include "diag/Trace.h"

/* Includes StmLib files ----------------------------------------------------*/
#include "stm32f30x.h"

#include "stm32f30x_adc.h"
#include "stm32f30x_can.h"
#include "stm32f30x_comp.h"
#include "stm32f30x_crc.h"
#include "stm32f30x_dac.h"
#include "stm32f30x_dbgmcu.h"
#include "stm32f30x_dma.h"
#include "stm32f30x_exti.h"
#include "stm32f30x_flash.h"
#include "stm32f30x_gpio.h"
#include "stm32f30x_i2c.h"
#include "stm32f30x_it.h"
#include "stm32f30x_iwdg.h"
#include "stm32f30x_misc.h"
#include "stm32f30x_opamp.h"
#include "stm32f30x_pwr.h"
#include "stm32f30x_rcc.h"
#include "stm32f30x_rtc.h"
#include "stm32f30x_spi.h"
#include "stm32f30x_syscfg.h"
#include "stm32f30x_tim.h"
#include "stm32f30x_usart.h"
#include "stm32f30x_wwdg.h"
#include "stm32f3_discovery.h"
#include "stm32f3_discovery_l3gd20.h"
#include "stm32f3_discovery_lsm303dlhc.h"

/* Includes UsbLib files ----------------------------------------------------*/
#include "hw_config.h"
#include "usb_conf.h"
#include "usb_core.h"
#include "usb_def.h"
#include "usb_desc.h"
#include "usb_init.h"
#include "usb_int.h"
#include "usb_istr.h"
#include "usb_lib.h"
#include "usb_mem.h"
#include "usb_prop.h"
#include "usb_pwr.h"
#include "usb_regs.h"
#include "usb_sil.h"
#include "usb_type.h"
#include "VCP_F3.h"

/* Includes Core files ------------------------------------------------------*/
#include "core_cm4.h"

#ifdef __cplusplus
}
#endif

// ============================================================================
// Sample pragmas to cope with warnings. Please note the related line at
// the end of this function, used to pop the compiler diagnostics status.
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-parameter"
#pragma GCC diagnostic ignored "-Wmissing-declarations"
#pragma GCC diagnostic ignored "-Wreturn-type"
#pragma GCC diagnostic ignored "-Wunused-variable"
#pragma GCC diagnostic pop

#ifndef __cplusplus
#define false 0
#define true  1
#endif

/* Exported functions ------------------------------------------------------- */
#ifdef __cplusplus
 extern "C" {
#endif 

// Инициализация оборудования
void InitAll();

// Функции для отработки поступивших команд
void UserEP3_OUT_Callback(uint8_t *buffer);
void restart(void);
void start_InitialSetting(void);
void start_Measuring(void);
void stop_Measuring(void);
void stop_CollectingData(void);

// Отправка предопределённых сообщений
void send_confirm_msg(void);
void send_hello_msg(void);
void send_error_msg(void);
void send_end_of_initial_setting_msg(void);

// Системные функции
void Error_Handler(void);
void Delay(__IO uint32_t nTime);
void TimingDelay_Decrement(void);

uint32_t L3GD20_TIMEOUT_UserCallback(void);
uint32_t LSM303DLHC_TIMEOUT_UserCallback(void);

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */

