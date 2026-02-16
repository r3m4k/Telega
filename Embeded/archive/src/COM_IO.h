  /* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __COM_IO_H
#define __COM_IO_H

#ifdef __cplusplus
 extern "C" {
#endif 

/* Includes ------------------------------------------------------------------*/
#include "stm32f30x_adc.h"
#include "stm32f30x.h"
#include "stm32f3_discovery.h"
#include <stdio.h>
#include "stm32f3_discovery_lsm303dlhc.h"
#include "stm32f3_discovery_l3gd20.h"
#include "usb_lib.h"
#include "hw_config.h"
#include "usb_pwr.h"
#include "platform_config.h"
#include "stm32f30x_tim.h"
#include "stm32f30x_gpio.h"
#include "stm32f30x_rcc.h"
#include "stm32f30x_misc.h"
#include "stm32f30x_exti.h"
#include "stm32f30x_syscfg.h"
#include "VCP_F3.h"														//for the UART4 functions on the STM32F3-Discovery


/* Exported functions ------------------------------------------------------- */
void SendVal(uint8_t Command,int16_t Value, uint8_t Counter);
void P_SendVal(uint8_t Command, uint8_t Value1, uint8_t Value2);
void TESTSend(uint16_t Value1, uint16_t Value2, uint16_t Value3, uint16_t Value4, uint16_t Value5, uint16_t Value6);	 
//void UsartSend(uint16_t Value1, uint16_t Value2, uint16_t Value3, int DPP_Value);
//	void UsartSend(uint16_t Value1, uint16_t Value2, uint16_t Value3, uint16_t DPPValue1, uint16_t DPPValue2, uint16_t DPPValue3,  uint16_t DPPValue4); 
void UsartSend(uint16_t Value1, uint16_t Value2, uint16_t Value3, uint16_t maxValue1, uint16_t maxValue2, uint16_t maxValue3, uint16_t DPPValue1, uint16_t DPPValue2, uint16_t DPPValue3,  uint16_t DPPValue4);
#ifdef __cplusplus
}
#endif

#endif /* __COM_IO_H */
