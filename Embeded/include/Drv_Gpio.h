#include "stm32f30x_gpio.h"  
#include "stm32f30x_rcc.h"

#define MAIN_LED_ON() 	GPIO_SetBits(GPIOA, GPIO_Pin_11)
#define MAIN_LED_OFF() 	GPIO_ResetBits(GPIOA, GPIO_Pin_11)

#define EXTRA_LED_ON() 		GPIO_SetBits(GPIOA, GPIO_Pin_12)
#define EXTRA_LED_OFF()  	GPIO_ResetBits(GPIOA, GPIO_Pin_12)

#define FlashReProgramError() for (;;){	MAIN_LED_ON();EXTRA_LED_ON();	for(int i=0;i<100000;i++);	MAIN_LED_OFF();EXTRA_LED_OFF();	for(int i=0;i<1000000;i++);	}// ������������ ��������� ������ ������������������� Flash

#define LINK_LED_ON				MAIN_LED_ON
#define LINK_LED_OFF				MAIN_LED_OFF

#define ResetPin           GPIO_Pin_1   // Ножка пересброса на плате

void InitGPIO(void);
void InitResetPin();