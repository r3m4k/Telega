#include "stm32f30x.h" /* STM32F303 definitions         */
#include "Drv_Gpio.h"
#include "stm32f30x_tim.h"


bool pc8;

/*
 Для переключателя скоростей-приращениц кода используются следующие порты
 PC10,PC11,PC12,PD0,PD1,PD2(used as gnd),PD3,PD4,PD5,PD6

 */

void InitGPIO()
{
    GPIO_InitTypeDef GPIO_InitStructure;

    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;

    /* Enable GPIO clock */
    RCC_AHBPeriphClockCmd(RCC_AHBPeriph_GPIOE, ENABLE);
    RCC_AHBPeriphClockCmd(RCC_AHBPeriph_GPIOC, ENABLE);

    RCC_AHBPeriphClockCmd(RCC_AHBPeriph_GPIOB, ENABLE);
    RCC_AHBPeriphClockCmd(RCC_AHBPeriph_GPIOD, ENABLE);

    //
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_8 | GPIO_Pin_9 | GPIO_Pin_10 | GPIO_Pin_11 | GPIO_Pin_12 | GPIO_Pin_13 | GPIO_Pin_14 | GPIO_Pin_15;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_OUT;
    GPIO_InitStructure.GPIO_OType = GPIO_OType_PP;
    GPIO_InitStructure.GPIO_PuPd = GPIO_PuPd_UP;
    GPIO_Init(GPIOE, &GPIO_InitStructure);
    // данная вывод инициализируется как вход для опроса пользовательской кнопки
    // С учетом схемотехники платы STM32F3....discovery board целесообразно подтянуть
    // эту кнопку к 0 споротивлением порядка 3-4 ком, разместив его в районе R4 и
    // отладочного разъема USB эмулятора
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_0;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IN;
    GPIO_InitStructure.GPIO_PuPd = GPIO_PuPd_UP;
    GPIO_Init(GPIOA, &GPIO_InitStructure);

    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_10 | GPIO_Pin_11 | GPIO_Pin_12 | GPIO_Pin_8 | GPIO_Pin_6 | GPIO_Pin_7;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IN;
    GPIO_InitStructure.GPIO_PuPd = GPIO_PuPd_UP; // GPIO_PuPd_DOWN;
    GPIO_Init(GPIOC, &GPIO_InitStructure);

    // PD0,PD1,PD2(used as gnd),PD3,PD4,PD5,

    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_0 | GPIO_Pin_1 | GPIO_Pin_3 | GPIO_Pin_4 | GPIO_Pin_5 | GPIO_Pin_6;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IN;
    GPIO_InitStructure.GPIO_PuPd = GPIO_PuPd_UP; // GPIO_PuPd_DOWN;
    GPIO_Init(GPIOD, &GPIO_InitStructure);

    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_2;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_OUT;
    GPIO_InitStructure.GPIO_PuPd = GPIO_PuPd_UP; // GPIO_PuPd_DOWN;
    GPIO_Init(GPIOD, &GPIO_InitStructure);

    //	  for (;;)
    //	  {
    //		  GPIO_SetBits(GPIOD, GPIO_Pin_2);
    GPIO_ResetBits(GPIOD, GPIO_Pin_2); // имитирует "0" для общего вывода переключателя приращений
    //	  }

    pc8 = GPIO_ReadInputDataBit(GPIOC, GPIO_Pin_8); // задает формат выдачи байта по UART см Drv_Uart.cpp, строка 66

    return;
}

/*
Инициализация ножки PA1 для запуска аппаратного перезапуска платы, путём подтяжки ножки к земле в нужный момент.
Нормально ножка в состоянии GPIO_PuPd_UP. Данная ножка должна быть соединена через диод к 5-ой ножке модуля SWD.
При переводе в состояние GPIO_PuPd_DOWN, инициируется сигнал NRST на SWD, что запускает аппаратный перезапуск платы
*/
void InitResetPin(){
    GPIO_InitTypeDef GPIO_InitStructure;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    RCC_AHBPeriphClockCmd(RCC_AHBPeriph_GPIOA, ENABLE);

    GPIO_InitStructure.GPIO_Pin = ResetPin;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_OUT;
    GPIO_InitStructure.GPIO_OType = GPIO_OType_PP;
    GPIO_InitStructure.GPIO_PuPd = GPIO_PuPd_UP;

    GPIO_Init(GPIOA, &GPIO_InitStructure);
    GPIO_SetBits(GPIOA, ResetPin);
}