#include "COM_IO.h"
#include "Drv_Uart.h"

void SendVal(uint8_t Command, int16_t Value, uint8_t Counter)
{
    char bufout[7];
    bufout[0] = 126;
    bufout[1] = 3;
    bufout[2] = Counter;
    bufout[3] = Command;
    bufout[4] = (uint8_t)Value;                                 //(uint8_t)MagBuffer[0];
    bufout[5] = ((uint8_t)((uint16_t)(((int16_t)Value) >> 8))); //((uint8_t)(((uint16_t)MagBuffer[0])>>8));
    bufout[6] = (bufout[0] + bufout[1] + bufout[2] + bufout[3] + bufout[4] + bufout[5]);

    CDC_Send_DATA((unsigned char *)(&bufout), 7);
}

void P_SendVal(uint8_t Command, uint8_t Value1, uint8_t Value2)
{
    char bufoutP[7] = {0};
    bufoutP[0] = 126;
    bufoutP[1] = 3;
    bufoutP[2] = 0;
    bufoutP[3] = Command;
    bufoutP[4] = (uint8_t)Value1;
    bufoutP[5] = (uint8_t)Value2;
    bufoutP[6] = (bufoutP[0] + bufoutP[1] + bufoutP[2] + bufoutP[3] + bufoutP[4] + bufoutP[5]);

    CDC_Send_DATA((unsigned char *)(&bufoutP), 7);
}

void TESTSend(uint16_t Value1, uint16_t Value2, uint16_t Value3, uint16_t Value4, uint16_t Value5, uint16_t Value6)
{
    char bufoutP[21] = {0};
    bufoutP[0] = 126;
    bufoutP[1] = 17;
    bufoutP[2] = 255;
    bufoutP[3] = 200;
    bufoutP[4] = (uint8_t)Value1;
    bufoutP[5] = ((uint8_t)((uint16_t)(((int16_t)Value1) >> 8)));
    bufoutP[6] = (uint8_t)Value2;
    bufoutP[7] = ((uint8_t)((uint16_t)(((int16_t)Value2) >> 8)));
    bufoutP[8] = (uint8_t)Value3;
    bufoutP[9] = ((uint8_t)((uint16_t)(((int16_t)Value3) >> 8)));
    bufoutP[10] = (uint8_t)Value4;
    bufoutP[11] = ((uint8_t)((uint16_t)(((int16_t)Value4) >> 8)));
    bufoutP[12] = (uint8_t)Value5;
    bufoutP[13] = ((uint8_t)((uint16_t)(((int16_t)Value5) >> 8)));
    bufoutP[14] = (uint8_t)Value6;
    bufoutP[15] = ((uint8_t)((uint16_t)(((int16_t)Value6) >> 8)));
    bufoutP[20] = (bufoutP[0] + bufoutP[1] + bufoutP[2] + bufoutP[3] + bufoutP[4] + bufoutP[5] + bufoutP[6] + bufoutP[7] + bufoutP[8] + bufoutP[9] + bufoutP[10] + bufoutP[11] + bufoutP[12] + bufoutP[13] + bufoutP[14] + bufoutP[15]);

    CDC_Send_DATA((unsigned char *)(&bufoutP), 21);
}

void UsartSend(uint16_t Value1, uint16_t Value2, uint16_t Value3, uint16_t maxValue1, uint16_t maxValue2, uint16_t maxValue3, uint16_t DPPValue1, uint16_t DPPValue2, uint16_t DPPValue3, uint16_t DPPValue4)
{
    char bufoutP[21] = {0};
    bufoutP[0] = 126;
    bufoutP[1] = 17;
    bufoutP[2] = 255;
    bufoutP[3] = 201; // 201 (C9), standard - 200 (C8)

    bufoutP[4] = (uint8_t)Value1;
    bufoutP[5] = ((uint8_t)((uint16_t)(((int16_t)Value1) >> 8)));
    bufoutP[6] = (uint8_t)Value2;
    bufoutP[7] = ((uint8_t)((uint16_t)(((int16_t)Value2) >> 8)));
    bufoutP[8] = (uint8_t)Value3;
    bufoutP[9] = ((uint8_t)((uint16_t)(((int16_t)Value3) >> 8)));

    bufoutP[10] = (uint8_t)maxValue1;
    bufoutP[11] = ((uint8_t)((uint16_t)(((int16_t)maxValue1) >> 8)));
    bufoutP[12] = (uint8_t)maxValue2;
    bufoutP[13] = ((uint8_t)((uint16_t)(((int16_t)maxValue2) >> 8)));
    bufoutP[14] = (uint8_t)maxValue3;
    bufoutP[15] = ((uint8_t)((uint16_t)(((int16_t)maxValue3) >> 8)));

    bufoutP[16] = (uint8_t)DPPValue1;
    bufoutP[17] = (uint8_t)DPPValue2;
    bufoutP[18] = (uint8_t)DPPValue3;
    bufoutP[19] = (uint8_t)DPPValue4;

    bufoutP[20] = (bufoutP[0] + bufoutP[1] + bufoutP[2] + bufoutP[3] + bufoutP[4] + bufoutP[5] + bufoutP[6] + bufoutP[7] + bufoutP[8] + bufoutP[9] + bufoutP[10] + bufoutP[11] + bufoutP[12] + bufoutP[13] + bufoutP[14] + bufoutP[15] + bufoutP[16] + bufoutP[17] + bufoutP[18] + bufoutP[19]);

    UartSendString((unsigned char *)(&bufoutP), 21);
}

// void UsartSend(uint16_t Acc_X, uint16_t Acc_Y, uint16_t Acc_Z,
//                uint16_t Giro_X, uint16_t Giro_Y, uint16_t Giro_Z,
//                uint16_t Mag_X, uint16_t Mag_Y, uint16_t Mag_Z,
//                uint16_t DPPValue1, uint16_t DPPValue2, uint16_t DPPValue3, uint16_t DPPValue4)
// {
//     char bufoutP[27] = {0};
//     bufoutP[0] = 126;
//     bufoutP[1] = 17;
//     bufoutP[2] = 255;
//     bufoutP[3] = 201; // 201 (C9), standard - 200 (C8)

//     bufoutP[4] = (uint8_t)Acc_X;
//     bufoutP[5] = ((uint8_t)((uint16_t)(((int16_t)Acc_X) >> 8)));
//     bufoutP[6] = (uint8_t)Acc_Y;
//     bufoutP[7] = ((uint8_t)((uint16_t)(((int16_t)Acc_Y) >> 8)));
//     bufoutP[8] = (uint8_t)Acc_Z;
//     bufoutP[9] = ((uint8_t)((uint16_t)(((int16_t)Acc_Z) >> 8)));

//     bufoutP[10] = (uint8_t)Giro_X;
//     bufoutP[11] = ((uint8_t)((uint16_t)(((int16_t)Giro_X) >> 8)));
//     bufoutP[12] = (uint8_t)Giro_Y;
//     bufoutP[13] = ((uint8_t)((uint16_t)(((int16_t)Giro_Y) >> 8)));
//     bufoutP[14] = (uint8_t)Giro_Z;
//     bufoutP[15] = ((uint8_t)((uint16_t)(((int16_t)Giro_Z) >> 8)));

//     bufoutP[16] = (uint8_t)Mag_X;
//     bufoutP[17] = ((uint8_t)((uint16_t)(((int16_t)Mag_X) >> 8)));
//     bufoutP[18] = (uint8_t)Mag_Y;
//     bufoutP[19] = ((uint8_t)((uint16_t)(((int16_t)Mag_Y) >> 8)));
//     bufoutP[20] = (uint8_t)Mag_Z;
//     bufoutP[21] = ((uint8_t)((uint16_t)(((int16_t)Mag_Z) >> 8)));

//     bufoutP[22] = (uint8_t)DPPValue1;
//     bufoutP[23] = (uint8_t)DPPValue2;
//     bufoutP[24] = (uint8_t)DPPValue3;
//     bufoutP[25] = (uint8_t)DPPValue4;

//     bufoutP[26] = (598 + bufoutP[4] + bufoutP[5] + bufoutP[6] + bufoutP[7] + bufoutP[8] + bufoutP[9] + bufoutP[10] +
//                         bufoutP[11] + bufoutP[12] + bufoutP[13] + bufoutP[14] + bufoutP[15] + bufoutP[16] + bufoutP[17] + 
//                         bufoutP[18] + bufoutP[19] + bufoutP[20] + bufoutP[21] + bufoutP[22] + bufoutP[23] + bufoutP[24] + bufoutP[25]);


//     UartSendString((unsigned char *)(&bufoutP), 27);
// }