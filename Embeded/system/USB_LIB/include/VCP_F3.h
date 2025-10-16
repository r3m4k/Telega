/*#############################################################
Driver name	    : VCP_F3
Author 					: Grant Phillips
Date Modified   : 10/04/2014
Compiler        : Keil ARM-MDK (uVision V4.70.0.0)
Tested On       : STM32F3-Discovery

Description			: Provides a library to use the USER USB port
									on the STM32F3-Discovery to establish a serial
									communication with a remote device (e.g. PC)
									via a Virtual COM Port.  Please study the
									documentation on the example website to fully
									understand how to install and implement this.

Requirements    : * STM32F3-Discovery Board

Functions				: VCP_Init
									VCP_ResetPort
									VCP_PutStr
									VCP_GetStr
													  
Special Note(s) : NONE
##############################################################*/

#include <stdio.h>
#include <string.h>
#include <stdbool.h>

#include "stm32f30x_gpio.h"
#include "stm32f30x_rcc.h"
#include "hw_config.h"
#include "usb_lib.h"
#include "usb_desc.h"
#include "usb_pwr.h"
#include "usb_prop.h"

extern __IO uint32_t packet_sent;
extern __IO uint8_t Send_Buffer[VIRTUAL_COM_PORT_DATA_SIZE] ;
extern __IO  uint32_t packet_receive;
extern __IO uint8_t Receive_length;
extern __IO uint8_t Receive_Buffer[64];

#ifdef __cplusplus
extern "C" {
#endif
void VCP_Init(void);
void VCP_ResetPort(void);
void VCP_PutStr(char *str);
void VCP_GetStr(char str[]);
void VCP_Polling();
#ifdef __cplusplus
}
#endif

/****END OF FILE****/
