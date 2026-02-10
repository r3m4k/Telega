/* Includes H files ----------------------------------------------------------*/
#include "main.h"

/* Includes HPP files --------------------------------------------------------*/
#include "Consts.hpp"
#include "GPTimers.hpp"
#include "Leds.hpp"
#include "L3GD20.hpp"
#include "LSM303DLHC.hpp"
#include "GyronavtPackage.hpp"
#include "ComPort.hpp"
#include "USART.hpp"
#include "GpioPort.hpp"
#include "GpioPin.hpp"

// ----------------------------------------------------------------------------
//
// Standalone STM32F3 empty sample (trace via NONE).
//
// Trace support is enabled by adding the TRACE macro definition.
// By default the trace messages are forwarded to the NONE output,
// but can be rerouted to any device or completely suppressed, by
// changing the definitions required in system/src/diag/trace_impl.c
// (currently OS_USE_TRACE_ITM, OS_USE_TRACE_SEMIHOSTING_DEBUG/_STDOUT).
//

/* #global variables -----------------------------------------*/
RCC_ClocksTypeDef RCC_Clocks; // structure used for setting up the SysTick Interrupt

// Unused global variables that have to be included to ensure correct compiling
// ###### DO NOT CHANGE ######
// ===============================================================================
__IO uint32_t TimingDelay = 0;                     // used with the Delay function
__IO uint8_t DataReady = 0;
__IO uint32_t USBConnectTimeOut = 100;
__IO uint32_t UserButtonPressed = 0;
__IO uint8_t PrevXferComplete = 1;
__IO uint8_t buttonState;
// ===============================================================================


/* Defines ------------------------------------------------------------------*/
#define IST_VECTORS_NUM     98

/* Typedef ------------------------------------------------------------------*/
typedef void (* const pHandler)(void);

/* Global variables ---------------------------------------------------------*/

extern pHandler __isr_vectors[];

// Собственная таблица прерываний
__attribute__((aligned(128)))    // Cortex-M4 требует выравнивание по 128 байт!
__user_pHandler __user_vector_table[IST_VECTORS_NUM] = {0};

// ----------------------------------------------------------------------------

// Стадии программы
enum class ProgramStages{InfiniteSending};

// ----------------------------------------------------------------------------

using namespace STM_CppLib;

// Периферия
Leds leds;                          // Светодиоды на плате
L3GD20 gyro_sensor;                 // Встроенный гироскоп
LSM303DLHC acc_sensor;              // Встроенный датчик с акселерометром,
                                    // магнитным и температурным датчиками
STM_Packages::GyronavtPackage gyronavt_package;   // Пакет данных в формате "Гиронавт"

// Интерфейсы связи
ComPort com_port;
USARTx usart1;

// Используемые таймеры
STM_Timer::Timer3<send_package> timer3;   // Основной таймер, запускающий чтение и отправку данных 
STM_Timer::Timer4<[](){
    leds.ChangeLedStatus(LED6);
    leds.ChangeLedStatus(LED7);
}> timer4;   // Таймер для мерцания светодиодами LED6, LED7

// Пин Pin_PC0 используется для инициализации прерывания EXTI_Line1, настроенное
// на перевод пина Pin_PC1 из состояние Reset в состояние Set.
// ВАЖНО! Данные пины должны быть соединены перемычкой на плате. 
STM_GPIO::GPIO_Pin <STM_GPIO::GPIO_Port::PortC, GPIO_PinSource0> Pin_PC0;

// Настройка внешнего прерывания, которое будет вызываться из main
STM_GPIO::GPIO_Pin_EXTI
    <STM_GPIO::GPIO_Port::PortC, GPIO_PinSource1, update_package_data> Pin_PC1;

// ----------------------------------------------------------------------------

uint32_t tick_counter = 0;      // Счётчик тиков основного таймера

// ----------------------------------------------------------------------------


int main()
{
    // ##########################

    // Загрузим собственную таблицу прерываний
    __disable_irq();

    // Скопируем исходную таблицу прерываний
    for(uint8_t i = 0; i < IST_VECTORS_NUM; i++){
        __user_vector_table[i] = __isr_vectors[i];
    }

    SCB->VTOR = (uint32_t)__user_vector_table;

    __DSB();
    __ISB();

    __enable_irq();

	RCC_GetClocksFreq(&RCC_Clocks);
	if (SysTick_Config(RCC_Clocks.HCLK_Frequency / 1000))
		while(true) {}     //will end up in this infinite loop if there was an error with Systick_Config
    
    // ##########################

    auto stage = ProgramStages::InfiniteSending;    // Стадия программы

    // Инициализируем всё оборудования
    InitAll();             
    
    // Поморгаем светодиодами после успешной инициализации
    leds.ToggleLeds();

    // Считаем показания датчиков до запуска таймеров, чтобы не отправлять нулевые данные
    gyro_sensor.ReadData();
    acc_sensor.ReadData();
    update_package_data();
    
    // Запустим таймеры
    timer3.Start();
    timer4.Start();

    // Основной цикл программы
    while (true)
    {
        switch (stage){
        case ProgramStages::InfiniteSending:

            leds.LedOn(LED9);

            // Считаем показания датчиков
            gyro_sensor.ReadData();
            acc_sensor.ReadData();
            
            // Обновим данные gyronavt_package в прерывании EXTI_Line1 

            /* Программная инициализация прерывания */
            EXTI_GenerateSWInterrupt(EXTI_Line1);

            /* ***************************
            Инициализация прерывания через поднятие ножки PC0.
            Для этого необходимо соединить ножки PC0 и PC1 с помощью джампера!
            *************************** */
            // Pin_PC0.SetPin();
            // Pin_PC0.ResetPin();
            
            leds.LedOff(LED9);

            break;
        }
    }
}

// -------------------------------------------------------------------------------
// Инициализация оборудования
void InitAll(){
    leds.Init();
    gyro_sensor.Init();
    acc_sensor.Init();
    com_port.Init();
    usart1.Init();
    Pin_PC0.InitPin();
    Pin_PC1.InitPinExti();

    // Настройка таймера для начала сбора данных
    uint32_t tim3_period = 25 - 1;      // те на 25 тик таймер переполнится и вызовется прерывание
    timer3.Init(tim3_period);

    // Настройка таймера для мерцания светодиодами
    uint32_t tim4_period = 20000 - 1;   // срабатывание каждые 2 с
    timer4.Init(tim4_period);
}

// -------------------------------------------------------------------------------

// Функция для обновления данных в посылке gyronavt_package
void update_package_data(){
    gyronavt_package.UpdateData();
}

// -------------------------------------------------------------------------------

// Функция для отправки посылки gyronavt_package по COM порту
void send_package(){
    // Изменим состояние светодиода при отправке сообщения
    leds.ChangeLedStatus(LED8);

    // Обновим счётчик таймера и контрольную сумму перед отправкой
    gyronavt_package.UpdateTime(++tick_counter);
    gyronavt_package.UpdateControlSum();

    // Отправим посылку по com порту и usart1
    leds.LedOn(LED4);
    com_port.SendPackage(gyronavt_package);
    leds.LedOff(LED4);

    leds.LedOn(LED5);
    usart1.SendPackage(gyronavt_package);
    leds.LedOff(LED5);
}

// -------------------------------------------------------------------------------

void UserEP3_OUT_Callback(uint8_t *buffer)
{
    buffer[0] = 0;
}

// -------------------------------------------------------------------------------

void USART1_IRQHandler(void)
{
    if (USART_GetITStatus(USART1, USART_IT_RXNE) != RESET) // было прерывание от приемника
        __NOP();

    if (USART_GetITStatus(USART1, USART_IT_TXE) != RESET){ // было прерывание от передатчика
        while (USART_GetFlagStatus(USART1, USART_FLAG_TC) == RESET){} // дожидаюсь завершения выдачи текущего байта и отключаю прерывания от выдачи
        USART_ITConfig(USART1, USART_IT_TXE, DISABLE);
    }
    USART_ClearITPendingBit(USART1, USART_IT_ORE);
}

// -------------------------------------------------------------------------------

void Error_Handler(void)
{
    /* Turn LED10/3 (RED) on */
    STM_EVAL_LEDOn(LED10);
    STM_EVAL_LEDOn(LED3);
    while (1)
    {
    }
}

// Function to insert a timing delay of nTime
// ###### DO NOT CHANGE ######
void Delay(__IO uint32_t nTime)
{
    TimingDelay = nTime;

    while (TimingDelay != 0){}
}

// Function to Decrement the TimingDelay variable.
// ###### DO NOT CHANGE ######
void TimingDelay_Decrement(void)
{
    if (TimingDelay != 0x00)
    {
        TimingDelay--;
    }
}

// Unused functions that have to be included to ensure correct compiling
// ###### DO NOT CHANGE ######
// =======================================================================
uint32_t L3GD20_TIMEOUT_UserCallback(void)
{
    return 0;
}

uint32_t LSM303DLHC_TIMEOUT_UserCallback(void)
{
    return 0;
}
// =======================================================================
