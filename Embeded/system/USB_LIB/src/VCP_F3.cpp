#include "VCP_F3.h"
// #include "CBUFFER.h"

// int VCP_PollingCounter = 0;
// #define VCP_PollingPeriod 100
// CBuffer<unsigned char> VCP_Buff;

/*********************************************************************************************
Function name   : VCP_Init
Author 					: Grant Phillips
Date Modified   : 10/04/2014
Compiler        : Keil ARM-MDK (uVision V4.70.0.0)

Description			: Initializes the Virtual COM Port module

Special Note(s) : NONE

Parameters			: NONE
Return value		: NONE
*********************************************************************************************/
#define VCP_BUF_SIZE 1000
unsigned char VCP_STATIC_BFR[VCP_BUF_SIZE];
void VCP_Init(void)
{
    // VCP_Buff.Init(VCP_BUF_SIZE, (int)&VCP_STATIC_BFR);
    Set_System();
    Set_USBClock();
    USB_Interrupts_Config();
    USB_Init();
    // packet_sent=1;
}

/*********************************************************************************************
Function name   : VCP_ResetPort
Author 					: Grant Phillips
Date Modified   : 10/04/2014
Compiler        : Keil ARM-MDK (uVision V4.70.0.0)

Description			: Resets the Virtual COM Port so that the user is not required to unplug the
                                    USB port and plug it back in again.

Special Note(s) : NONE

Parameters			: NONE

Return value		: NONE
*********************************************************************************************/
void VCP_ResetPort(void)
{
    GPIO_InitTypeDef GPIO_InitStructure;

    RCC_AHBPeriphClockCmd(RCC_AHBPeriph_GPIOA, ENABLE); // enable the AHB bus to use GPIOA

    /* Configure PA12 in output pushpull mode */
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_12;        // which pins to setup, seperated by |
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_OUT;     // setup for output mode
    GPIO_InitStructure.GPIO_OType = GPIO_OType_PP;    // push-pull mode; also available is GPIO_OType_OD (open drain)
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz; // update speed is 50Mhz; also available is GPIO_Speed_10MHz and GPIO_Speed_2MHz
    GPIO_InitStructure.GPIO_PuPd = GPIO_PuPd_NOPULL;    // output pulled down
    GPIO_Init(GPIOA, &GPIO_InitStructure);            // initialize GPIOA with the above structure

    GPIO_WriteBit(GPIOA, GPIO_Pin_12, Bit_RESET);     // pull the USB BUS+ low to reset the bus
}

/*********************************************************************************************
Function name   : VCP_PutStr
Author 					: Grant Phillips
Date Modified   : 10/04/2014
Compiler        : Keil ARM-MDK (uVision V4.70.0.0)

Description			: Prints a string to the Virtual COM Port

Special Note(s) : NONE

Parameters			: str			-	string (char array) to print

Return value		: NONE
*********************************************************************************************/
void VCP_PutStr(char *str)
{
    /*if (packet_sent == 1)																	//make sure previous data has been sent
        CDC_Send_DATA((unsigned char*)str, strlen(str));*/

    // while(packet_sent != 1){}																//make sure previous data has been sent
    CDC_Send_DATA((unsigned char *)str, strlen(str));
}

/*********************************************************************************************
Function name   : VCP_GetStr
Author 					: Grant Phillips
Date Modified   : 10/04/2014
Compiler        : Keil ARM-MDK (uVision V4.70.0.0)

Description			: Waits for a string from the Virtual COM Port terminated by \n or \r

Special Note(s) : NONE

Parameters			: str			-	string (char array) to print

Return value		: NONE
*********************************************************************************************/
// void VCP_GetStr(char str[])
//{
//	uint8_t i;
//
//	CDC_Receive_DATA();																		//start receiving data from Virtual COM Port
//
//	//wait for the \n or \r terminating characters
//	while((Receive_Buffer[Receive_length-1] != '\n') && (Receive_Buffer[Receive_length-1] != '\r'));
//
//	for(i=0; i<Receive_length; i++)
//	{
//		str[i] = Receive_Buffer[i];
//	}
//	str[i] = '\0';
//	Receive_length = 0;
// }
//
void VCP_GetStr(char str[])
{
    uint8_t i;
    Receive_length = 0;
    CDC_Receive_DATA(); // start receiving data from Virtual COM Port

    // wait for the \n or \r terminating characters
    while (Receive_length < 13)
        ;

    for (i = 0; i < Receive_length; i++)
    {
        str[i] = Receive_Buffer[i];
    }
    str[i] = '\0';
    Receive_length = 0;
}

// bool __attribute__((weak)) ProcessInByteUSB(unsigned char Bt)
// {
//     return true;
// }

// void VCP_Polling()
// {
//     if ((VCP_PollingCounter++) % VCP_PollingPeriod)
//     {
//         if (VCP_Buff.DataSize)
//             ProcessInByteUSB(VCP_Buff.ReadFrom());
//         return;
//     }
//     for (int i = 0; i < Receive_length; i++)
//         VCP_Buff.WriteTo(Receive_Buffer[i]);
//     Receive_length = 0;
//     CDC_Receive_DATA();
// }
