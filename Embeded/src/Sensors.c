#include "Sensors.h"

extern float gyro_multiplier;


void GYRO_INIT(void)
{
    L3GD20_InitTypeDef InitStruct;
    L3GD20_FilterConfigTypeDef FilterStruct;

    InitStruct.Power_Mode = L3GD20_MODE_ACTIVE;                     /* Power-down/Sleep/Normal Mode */
    InitStruct.Output_DataRate = L3GD20_OUTPUT_DATARATE_2;          /* OUT data rate */
    InitStruct.Axes_Enable = L3GD20_AXES_ENABLE;                    /* Axes enable */
    InitStruct.Band_Width = L3GD20_BANDWIDTH_2;                     /* Bandwidth selection */
    InitStruct.BlockData_Update = L3GD20_BlockDataUpdate_Continous; /* Block Data Update */
    InitStruct.Endianness = L3GD20_BLE_LSB;                         /* Endian Data selection */
    InitStruct.Full_Scale = L3GD20_FULLSCALE_500;                   /* Full Scale selection */

    L3GD20_Init(&InitStruct);

    /* High Pass Filter Configuration Functions */
    FilterStruct.HighPassFilter_Mode_Selection = L3GD20_HPM_NORMAL_MODE; /* Internal filter mode */
    FilterStruct.HighPassFilter_CutOff_Frequency = L3GD20_HPFCF_5;       /* High pass filter cut-off frequency */

    L3GD20_FilterConfig(&FilterStruct);

    // Зададим множитель для гироскопа в соответствии с документацией
    // (см. документацию для L3GD20, таблица 3 "Mechanical characteristics", стр. 9)
    switch (InitStruct.Full_Scale)
    {
    case L3GD20_FULLSCALE_250:
        gyro_multiplier = 8.75;
        break;

    case L3GD20_FULLSCALE_500:
        gyro_multiplier = 17.5;
        break;    

    case L3GD20_FULLSCALE_2000:
        gyro_multiplier = 70.0;
        break; 
    }
}

void ReadGyro(float *pfData)
{
    static uint8_t buffer[6] = {0};

    L3GD20_Read(buffer,     L3GD20_OUT_X_H_ADDR, 1);
    L3GD20_Read(buffer + 1, L3GD20_OUT_X_L_ADDR, 1);
    L3GD20_Read(buffer + 2, L3GD20_OUT_Y_H_ADDR, 1);
    L3GD20_Read(buffer + 3, L3GD20_OUT_Y_L_ADDR, 1);
    L3GD20_Read(buffer + 4, L3GD20_OUT_Z_H_ADDR, 1);
    L3GD20_Read(buffer + 5, L3GD20_OUT_Z_L_ADDR, 1);

    for (uint8_t i = 0; i < 3; i++)
    {
        pfData[i] = ((float)((int16_t)((((int16_t)buffer[2 * i]) << 8) + buffer[2 * i + 1])));
    }
}

void MAG_INIT(void)
{
    LSM303DLHCMag_InitTypeDef InitStruct;
    InitStruct.MagFull_Scale = LSM303DLHC_FS_2_5_GA;
    InitStruct.MagOutput_DataRate = LSM303DLHC_ODR_220_HZ;
    InitStruct.Working_Mode = LSM303DLHC_CONTINUOS_CONVERSION;
    InitStruct.Temperature_Sensor = LSM303DLHC_TEMPSENSOR_ENABLE;

    LSM303DLHC_MagInit(&InitStruct);
}

void ReadMag(float *pfData)
{
    static uint8_t buffer[6] = {0};
    uint8_t CTRLB = 0;
    uint16_t Magn_Sensitivity_XY = 0, Magn_Sensitivity_Z = 0;
    uint8_t i = 0;
    LSM303DLHC_Read(MAG_I2C_ADDRESS, LSM303DLHC_CRB_REG_M, &CTRLB, 1);

    LSM303DLHC_Read(MAG_I2C_ADDRESS, LSM303DLHC_OUT_X_H_M, buffer, 1);
    LSM303DLHC_Read(MAG_I2C_ADDRESS, LSM303DLHC_OUT_X_L_M, buffer + 1, 1);
    LSM303DLHC_Read(MAG_I2C_ADDRESS, LSM303DLHC_OUT_Y_H_M, buffer + 2, 1);
    LSM303DLHC_Read(MAG_I2C_ADDRESS, LSM303DLHC_OUT_Y_L_M, buffer + 3, 1);
    LSM303DLHC_Read(MAG_I2C_ADDRESS, LSM303DLHC_OUT_Z_H_M, buffer + 4, 1);
    LSM303DLHC_Read(MAG_I2C_ADDRESS, LSM303DLHC_OUT_Z_L_M, buffer + 5, 1);
    
    /* Switch the sensitivity set in the CRTLB*/
    switch (CTRLB & 0xE0)
    {
    case LSM303DLHC_FS_1_3_GA:
        Magn_Sensitivity_XY = LSM303DLHC_M_SENSITIVITY_XY_1_3Ga;
        Magn_Sensitivity_Z = LSM303DLHC_M_SENSITIVITY_Z_1_3Ga;
        break;
    case LSM303DLHC_FS_1_9_GA:
        Magn_Sensitivity_XY = LSM303DLHC_M_SENSITIVITY_XY_1_9Ga;
        Magn_Sensitivity_Z = LSM303DLHC_M_SENSITIVITY_Z_1_9Ga;
        break;
    case LSM303DLHC_FS_2_5_GA:
        Magn_Sensitivity_XY = LSM303DLHC_M_SENSITIVITY_XY_2_5Ga;
        Magn_Sensitivity_Z = LSM303DLHC_M_SENSITIVITY_Z_2_5Ga;
        break;
    case LSM303DLHC_FS_4_0_GA:
        Magn_Sensitivity_XY = LSM303DLHC_M_SENSITIVITY_XY_4Ga;
        Magn_Sensitivity_Z = LSM303DLHC_M_SENSITIVITY_Z_4Ga;
        break;
    case LSM303DLHC_FS_4_7_GA:
        Magn_Sensitivity_XY = LSM303DLHC_M_SENSITIVITY_XY_4_7Ga;
        Magn_Sensitivity_Z = LSM303DLHC_M_SENSITIVITY_Z_4_7Ga;
        break;
    case LSM303DLHC_FS_5_6_GA:
        Magn_Sensitivity_XY = LSM303DLHC_M_SENSITIVITY_XY_5_6Ga;
        Magn_Sensitivity_Z = LSM303DLHC_M_SENSITIVITY_Z_5_6Ga;
        break;
    case LSM303DLHC_FS_8_1_GA:
        Magn_Sensitivity_XY = LSM303DLHC_M_SENSITIVITY_XY_8_1Ga;
        Magn_Sensitivity_Z = LSM303DLHC_M_SENSITIVITY_Z_8_1Ga;
        break;
    }

    for (i = 0; i < 2; i++)
    {
        pfData[i] = ((((float)((int16_t)((((int16_t)buffer[2 * i]) << 8) + buffer[2 * i + 1]))) * 1000) / Magn_Sensitivity_XY) * (-1);
    }
    pfData[2] = ((((float)((int16_t)((((int16_t)buffer[4]) << 8) + buffer[5]))) * 1000) / Magn_Sensitivity_Z) * (-1);
}

void ACC_INIT(void)
{
    LSM303DLHCAcc_InitTypeDef AInitStruct;
    LSM303DLHCAcc_FilterConfigTypeDef FInitStructure;

    /* Fill the accelerometer structure */
    AInitStruct.Power_Mode = LSM303DLHC_NORMAL_MODE;                    // NORMAL or LOWPOWER MODE (CTRL_REG1 ODR[3])
    AInitStruct.AccOutput_DataRate = LSM303DLHC_ODR_400_HZ;             // output data rate				(CTRL_REG1) //400Hz - less zero values
    AInitStruct.Axes_Enable = LSM303DLHC_AXES_ENABLE;                   // enable x, y and z axes	(CTRL_REG1)
    AInitStruct.AccFull_Scale = LSM303DLHC_FULLSCALE_16G;               // full scale - "polnaya shkala"   (CTRL_REG4)
    AInitStruct.BlockData_Update = LSM303DLHC_BlockUpdate_Continous;    // Block data update. Default value: 0; (0: continuous update, 1: output registers not updated until MSB and LSB have been read (CTRL_REG4)
    AInitStruct.Endianness = LSM303DLHC_BLE_LSB;                        //??? Big/little endian data selection. Default value 0.(0: data LSB @ lower address, 1: data MSB @ lower address) AInitStruct.High_Resolution=LSM303DLHC_HR_ENABLE; (CTRL_REG4)
    AInitStruct.High_Resolution = LSM303DLHC_HR_ENABLE;
    /* Configure the accelerometer main parameters */
    LSM303DLHC_AccInit(&AInitStruct);

    /* Fill the accelerometer LPF structure ; CTRL_REG2 register*/
    /* mode, cutoff frquency, Filter status, Click, AOI1 and AOI2 */

    FInitStructure.HighPassFilter_Mode_Selection = LSM303DLHC_HPM_NORMAL_MODE;      //??? rejim filtra verhnih chastot 00 Normal mode (reset reading HP_RESET_FILTER) 01 Reference signal for filtering 10 Normal mode 11 Autoreset on interrupt event
    FInitStructure.HighPassFilter_CutOff_Frequency = LSM303DLHC_HPFCF_32;           // vybor chastoty sreza (8, 16, 32, 64)
    FInitStructure.HighPassFilter_FDS = LSM303DLHC_HIGHPASSFILTER_ENABLE;           // LSM303DLHC_HIGHPASSFILTER_DISABLE;
    FInitStructure.HighPassFilter_AOI1 = LSM303DLHC_HPF_AOI1_ENABLE;
    FInitStructure.HighPassFilter_AOI2 = LSM303DLHC_HPF_AOI2_ENABLE;

    /* Configure the accelerometer LPF main parameters */
    LSM303DLHC_AccFilterConfig(&FInitStructure);
}

void ReadAcc(float *pfData)
{
    int16_t pnRawData[3];
    uint8_t ctrlx[2];
    uint8_t buffer[6] = {0.0f};
    uint8_t cDivider;
    uint8_t i = 0;
    float LSM_Acc_Sensitivity = LSM_Acc_Sensitivity_2g;
    // uint8_t single_buffer = 0;

    /* Read the register content */
    LSM303DLHC_Read(ACC_I2C_ADDRESS, LSM303DLHC_CTRL_REG4_A, ctrlx, 2);
    // LSM303DLHC_Read(ACC_I2C_ADDRESS, LSM303DLHC_OUT_X_L_A, buffer, 6);
    
    LSM303DLHC_Read(ACC_I2C_ADDRESS, LSM303DLHC_OUT_X_L_A, buffer, 1);
    LSM303DLHC_Read(ACC_I2C_ADDRESS, LSM303DLHC_OUT_X_H_A, buffer + 1, 1);
    LSM303DLHC_Read(ACC_I2C_ADDRESS, LSM303DLHC_OUT_Y_L_A, buffer + 2, 1);
    LSM303DLHC_Read(ACC_I2C_ADDRESS, LSM303DLHC_OUT_Y_H_A, buffer + 3, 1);
    LSM303DLHC_Read(ACC_I2C_ADDRESS, LSM303DLHC_OUT_Z_L_A, buffer + 4, 1);
    LSM303DLHC_Read(ACC_I2C_ADDRESS, LSM303DLHC_OUT_Z_H_A, buffer + 5, 1);

    if (ctrlx[1] & 0x40)
        cDivider = 64;
    else
        cDivider = 16;

    /* check in the control register4 the data alignment*/
    if (!(ctrlx[0] & 0x40) || (ctrlx[1] & 0x40)) /* Little Endian Mode or FIFO mode */
    {
        for (i = 0; i < 3; i++)
        {
            pnRawData[i] = ((int16_t)((uint16_t)buffer[2 * i + 1] << 8) + buffer[2 * i]) / cDivider; //       pfData[i]=(float)((int16_t)((((int16_t)buffer[2*i]) << 8) + buffer[2*i+1]));
        }
    }
    else /* Big Endian Mode */
    {
        for (i = 0; i < 3; i++)
            pnRawData[i] = ((int16_t)((uint16_t)buffer[2 * i] << 8) + buffer[2 * i + 1]) / cDivider;
    }
    /* Read the register content */
    LSM303DLHC_Read(ACC_I2C_ADDRESS, LSM303DLHC_CTRL_REG4_A, ctrlx, 2);

    if (ctrlx[1] & 0x40)
    {
        /* FIFO mode */
        LSM_Acc_Sensitivity = 0.25;
    }
    else
    {
        /* normal mode */
        /* switch the sensitivity value set in the CRTL4*/
        switch (ctrlx[0] & 0x30)
        {
        case LSM303DLHC_FULLSCALE_2G:
            LSM_Acc_Sensitivity = LSM_Acc_Sensitivity_2g;
            break;
        case LSM303DLHC_FULLSCALE_4G:
            LSM_Acc_Sensitivity = LSM_Acc_Sensitivity_4g;
            break;
        case LSM303DLHC_FULLSCALE_8G:
            LSM_Acc_Sensitivity = LSM_Acc_Sensitivity_8g;
            break;
        case LSM303DLHC_FULLSCALE_16G:
            LSM_Acc_Sensitivity = LSM_Acc_Sensitivity_16g;
            break;
        }
    }

    /* Obtain the mg value for the three axis */
    for (i = 0; i < 3; i++)
    {
        pfData[i] = (float)pnRawData[i] / LSM_Acc_Sensitivity;
    }
}

void ReadMagTemp(float *pfTData)
{
    static uint8_t buffer[2] = {0};

    LSM303DLHC_Read(MAG_I2C_ADDRESS, LSM303DLHC_TEMP_OUT_H_M, buffer, 1);
    LSM303DLHC_Read(MAG_I2C_ADDRESS, LSM303DLHC_TEMP_OUT_L_M, buffer + 1, 1);

    *pfTData = (float)((int16_t)(((uint16_t)buffer[0] << 8) + buffer[1]) >> 4) * 100;
    *pfTData /= 100;
}

/**
 * @brief ADC1 channel configuration
 * @param None
 * @retval None
 */
void ADC_Config(void)
{
    ADC_InitTypeDef ADC_InitStructure;
    ADC_CommonInitTypeDef ADC_CommonInitStructure;
    GPIO_InitTypeDef GPIO_InitStructure;

    /* GPIOA Periph clock enable */

    RCC_AHBPeriphClockCmd(RCC_AHBPeriph_ADC12, ENABLE);

    /* Configure ADC Channel1 as analog input */
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_2;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AN;
    GPIO_InitStructure.GPIO_PuPd = GPIO_PuPd_NOPULL;
    GPIO_Init(GPIOA, &GPIO_InitStructure);

    RCC_ADCCLKConfig(RCC_ADC12PLLCLK_Div2);

    /* Initialize ADC structure */
    ADC_StructInit(&ADC_InitStructure);

    /* ADC Calibration */
    ADC_VoltageRegulatorCmd(ADC1, ENABLE);
    ADC_SelectCalibrationMode(ADC1, ADC_CalibrationMode_Single);
    ADC_StartCalibration(ADC1);

    ADC_CommonInitStructure.ADC_Mode = ADC_Mode_Independent;
    ADC_CommonInitStructure.ADC_Clock = ADC_Clock_AsynClkMode;
    ADC_CommonInitStructure.ADC_DMAAccessMode = ADC_DMAAccessMode_Disabled;
    ADC_CommonInitStructure.ADC_DMAMode = ADC_DMAMode_OneShot;
    ADC_CommonInitStructure.ADC_TwoSamplingDelay = 0;
    ADC_CommonInit(ADC1, &ADC_CommonInitStructure);

    /* Enable ADC_DMA */
    ADC_DMACmd(ADC1, ENABLE);

    /* ADC DMA request in circular mode */
    ADC_DMAConfig(ADC1, ADC_DMAMode_Circular);

    /* Configure the ADC1 in continuous mode withe a resolution equal to 12 bits */
    // ADC_CommonInitStructure.ADC_Mode = ADC_Mode_Independent;
    ADC_InitStructure.ADC_ContinuousConvMode = ADC_ContinuousConvMode_Enable;
    ADC_InitStructure.ADC_Resolution = ADC_Resolution_12b;
    ADC_InitStructure.ADC_ExternalTrigConvEvent = ADC_ExternalTrigConvEvent_0;
    ADC_InitStructure.ADC_ExternalTrigEventEdge = ADC_ExternalTrigEventEdge_None;
    ADC_InitStructure.ADC_DataAlign = ADC_DataAlign_Right;
    ADC_InitStructure.ADC_OverrunMode = ADC_OverrunMode_Disable;
    ADC_InitStructure.ADC_AutoInjMode = ADC_AutoInjec_Disable;
    ADC_InitStructure.ADC_NbrOfRegChannel = 1;
    ADC_Init(ADC1, &ADC_InitStructure);

    /* Convert the ADC1 Channel1 with 65.5 Cycles as sampling time */
    ADC_RegularChannelConfig(ADC1, ADC_Channel_TempSensor, 1, ADC_SampleTime_61Cycles5); // ADC_Channel_TempSensor

    /* Enable the ADC peripheral */
    ADC_Cmd(ADC1, ENABLE);

    /* Wait the ADRDY flag */
    while (!ADC_GetFlagStatus(ADC1, ADC_FLAG_RDY))
        ;

    /* ADC1 regular Software Start Conv */
    ADC_StartConversion(ADC1);
}
