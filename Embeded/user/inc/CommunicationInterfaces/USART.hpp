/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __USART_HPP
#define __USART_HPP

/* Includes ------------------------------------------------------------------*/
#include "stm32f30x_gpio.h"
#include "stm32f30x_rcc.h"
#include "stm32f30x_misc.h"
#include "stm32f30x_usart.h"

#include "BasePackage.hpp"

/* Defines -------------------------------------------------------------------*/

// -----------------------------------------------------------------------------
namespace STM_CppLib{

    // Класс для работы с USART
    class USARTx{
    public:
        void Init(){
            NVIC_InitTypeDef NVIC_InitStructure;
            GPIO_InitTypeDef GPIO_InitStructure;
            USART_InitTypeDef USART_InitStructure;
	
            /* Enable the USART1 Interrupt */
            NVIC_InitStructure.NVIC_IRQChannel = USART1_IRQn;
            NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority = 0;
            NVIC_InitStructure.NVIC_IRQChannelSubPriority = 0;
            NVIC_InitStructure.NVIC_IRQChannelCmd = ENABLE;
            NVIC_Init(&NVIC_InitStructure);

            /* Enable GPIO clock */
            RCC_AHBPeriphClockCmd(RCC_AHBPeriph_GPIOC, ENABLE);

            /* Enable USART clock */
            RCC_APB2PeriphClockCmd(RCC_APB2Periph_USART1, ENABLE); 

            /* Connect PXx to USARTx_Tx */
            GPIO_PinAFConfig(GPIOC, GPIO_PinSource4, GPIO_AF_7);

            /* Connect PXx to USARTx_Rx */
            GPIO_PinAFConfig(GPIOC, GPIO_PinSource5, GPIO_AF_7);

            /* Configure USART Tx as alternate function push-pull */
            GPIO_InitStructure.GPIO_Pin = GPIO_Pin_4;
            GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AF;
            GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
            GPIO_InitStructure.GPIO_OType = GPIO_OType_PP;
            GPIO_InitStructure.GPIO_PuPd = GPIO_PuPd_UP;
            GPIO_Init(GPIOC, &GPIO_InitStructure);

            /* Configure USART Rx as alternate function push-pull */
            GPIO_InitStructure.GPIO_Pin = GPIO_Pin_5;
            GPIO_Init(GPIOC, &GPIO_InitStructure);

            USART_InitStructure.USART_BaudRate = 921600; //115200;
            USART_InitStructure.USART_WordLength = USART_WordLength_8b;
            USART_InitStructure.USART_StopBits = USART_StopBits_2;
            USART_InitStructure.USART_Parity = USART_Parity_No;
            USART_InitStructure.USART_HardwareFlowControl = USART_HardwareFlowControl_None;
            USART_InitStructure.USART_Mode = USART_Mode_Tx;

            /* USART configuration */
            USART_Init(USART1, &USART_InitStructure);

            /* Enable USART */
            USART_Cmd(USART1, ENABLE);

            USART_ITConfig(USART1, USART_IT_TXE, ENABLE);
            USART_ITConfig(USART1, USART_IT_RXNE, DISABLE);
        }

        void SendByte(uint8_t bt){
           
            // Отправляем байт
            USART_SendData(USART1, static_cast<uint16_t>(bt));
            // USART_ITConfig(USART1, USART_IT_TXE, ENABLE);
            
            // Ждем завершения передачи
            while(USART_GetFlagStatus(USART1, USART_FLAG_TXE) == RESET){};

        }

        void SendBuffer(uint8_t* buffer, uint8_t len){
            for (uint8_t i = 0; i < len; i++){
                SendByte(buffer[i]);
            }
        }

        void SendPackage(STM_Packages::BasePackage& package){
            for (uint8_t i = 0; i < package.len; i++){
                SendByte(package.data_ptr[i]);
            }
        }
    };
} // namespace STM_CppLib



#endif /*   __USART_HPP   */