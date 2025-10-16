/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MAIN_H
#define __MAIN_H

#include <math.h>
#include <stdlib.h>
#include "diag/Trace.h"
#include "Sensors.h"
#include "core_cm4.h"


// ===============================================================================
// Sample pragmas to cope with warnings. Please note the related line at
// the end of this function, used to pop the compiler diagnostics status.
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-parameter"
#pragma GCC diagnostic ignored "-Wmissing-declarations"
#pragma GCC diagnostic ignored "-Wreturn-type"
#pragma GCC diagnostic ignored "-Wunused-variable"
#pragma GCC diagnostic pop

#define FALSE 0
#define TRUE  1

/* Exported functions ------------------------------------------------------- */
#ifdef __cplusplus
 extern "C" {
#endif 

void InitAll();
void InitDecoder();
void ProcessInByte(unsigned char Bt);

void LedsInit(void);
void Toggle_Leds(void);	
void LedsOn(void);
void LedsOff(void);

void LedOn(Led_TypeDef Led);
void LedOff(Led_TypeDef Led);

void TimerInit(void);
void TIM4_IRQHandler(void);

void UserEP3_OUT_Callback(uint8_t *buffer);
void restart(void);
void start_InitialSetting(void);
void start_Measuring(void);
void stop_Measuring(void);
void stop_CollectingData(void);
void error_msg(void);

void Delay(__IO uint32_t nTime);
void TimingDelay_Decrement(void);


#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */

