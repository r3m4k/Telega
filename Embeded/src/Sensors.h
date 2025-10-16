  /* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __SENSORS_H
#define __SENSORS_H

#ifdef __cplusplus
 extern "C" {
#endif 
	 
/* #defines --------------------------------------------------*/
#define LSM_Acc_Sensitivity_2g     (float)     1.0f            /*!< accelerometer sensitivity with 2 g full scale [LSB/mg] */
#define LSM_Acc_Sensitivity_4g     (float)     0.5f            /*!< accelerometer sensitivity with 4 g full scale [LSB/mg] */
#define LSM_Acc_Sensitivity_8g     (float)     0.25f           /*!< accelerometer sensitivity with 8 g full scale [LSB/mg] */
#define LSM_Acc_Sensitivity_16g    (float)     0.0834f         /*!< accelerometer sensitivity with 12 g full scale [LSB/mg] */
	 
/* Includes ------------------------------------------------------------------*/
#include "stm32f30x_adc.h"
#include "stm32f30x.h"
#include "stm32f3_discovery.h"
#include <stdio.h>
#include "stm32f3_discovery_lsm303dlhc.h"
#include "stm32f3_discovery_l3gd20.h"
#include "platform_config.h"
#include "stm32f30x_tim.h"
#include "stm32f30x_gpio.h"
#include "stm32f30x_rcc.h"
#include "stm32f30x_misc.h"
#include "stm32f30x_exti.h"
#include "stm32f30x_syscfg.h"
#include "stm32f30x_tim.h"
#include "hw_config.h"
#include "usb_lib.h"
#include "usb_desc.h"
#include "usb_pwr.h"
#include "usb_prop.h"
#include "VCP_F3.h"														//for the UART4 functions on the STM32F3-Discovery	 
#include "COM_IO.h"
#include "main.h"		 
	 
void MAG_INIT(void);
void ReadMag (float* pfData); 
void ReadMagTemp (float* pfTData);

void ACC_INIT(void);
void ReadAcc (float *pfData); 
	 
void GYRO_INIT (void);
void ReadGyro (float* pfData);

void ADC_Config(void);	 
	  
	 
#ifdef __cplusplus
}
#endif

#endif /* __SENSORS_H */
