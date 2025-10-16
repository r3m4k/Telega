/* Includes ------------------------------------------------------------------*/
#include "Drv_Gpio.h"
#include "Drv_Uart.h"

#include "main.h"

/* Includes HPP files --------------------------------------------------------*/
#include "COM_Port.hpp"
#include "Measure.hpp"

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
// Необходимые дефайны
#define PI 3.14159265358979f
#define TIM_PRESCALER      720          // При таком предделителе таймера получается один тик таймера на 10 мкс
#define TIM_PERIOD         25000        // Количество тиков таймера с частотой 10 кГц перед вызовом прерывания --> 250 мс период
// ----------------------------------------------------------------------------
// Сообщения, которые будем отправлять в ответ по COM порту (определены в COM_Port.hpp)
extern uint8_t ErrorMessage[MaxCommand_Length];
extern uint8_t ConfirmMessage[MaxCommand_Length];
extern uint8_t EndOfInitialSetting[MaxCommand_Length];

float gyro_multiplier;             // Множитель для данных с гироскопа
// -------------------------------------------------------------------------------
// Перечисление для стадии выполнения программы
enum Stages{BeforeBeginning, FooStage, InitialSetting, Measuring};
unsigned int stage = FooStage;
unsigned int previous_stage = BeforeBeginning;

// Перечисление, используемое при декодировании полученных сообщений по com порту
enum DecodeStages{Want7E, WantE7, WantFormat, WantData, WantConSum};
unsigned int decode_stage = Want7E;

// -------------------------------------------------------------------------------
// Создадим экземпляры классов системы STM в глобальной зоне видимости 
COM_Port COM_port;

// -------------------------------------------------------------------------------
// Пользовательские экземпляры классов
Measure measure(55.7522 * PI / 180, TIM_PERIOD * 0.00001);

// -------------------------------------------------------------------------------

int main()
{
    __disable_irq();
    __enable_irq();

	RCC_GetClocksFreq(&RCC_Clocks);
	if (SysTick_Config(RCC_Clocks.HCLK_Frequency / 1000))
		while(1);       //will end up in this infinite loop if there was an error with Systick_Config
    
    // Инициализируем всё оборудования
    InitAll();             
    
    // Поморгаем светодиодами после успешной инициализации
    Toggle_Leds();
   
    // Основной цикл программы
    while (TRUE)
    {
        // Вызов функции из очереди при заполненной очереди для отладки программы
        if (!(COM_port.command_queue.isEmpty())){
            COM_port.command_queue.get()();
        }

        switch (stage)
        {
        case FooStage:
            if (previous_stage != FooStage){
                previous_stage = FooStage;
                TIM_Cmd(TIM4, DISABLE);
                LedsOn();
            }

            measure.foo_reading_data();
            break;

        case InitialSetting:
            if (previous_stage != InitialSetting){
                previous_stage = InitialSetting;
                measure.TickCounter = 0;
                LedsOff();
            }
            // Начнём первоначальную выставку датчиков
            measure.initial_setting();
            // Отправим сообщение об успешном завершении выставки датчиков
            COM_port.sending_package(EndOfInitialSetting, MaxCommand_Length);
            
            stage = FooStage;

            break;

        case Measuring:
            if (previous_stage != Measuring){
                previous_stage = Measuring;

                measure.TickCounter = 0;
                // Запускаем таймер 
                TIM_Cmd(TIM4, ENABLE);
            }
            
            // // Включим зелёные светодиоды для указания корректной работы 
            LedsOff();
            LedOn(LED6);
            LedOn(LED7);
                       
            // Начнём работу
            measure.measuring();  
            break;
        }
    }
}

// -------------------------------------------------------------------------------
// Инициализация оборудования
void InitAll(){

    // Инициализируем периферию
    LedsInit();
    // Init.GPIO();
    InitResetPin();

    // Инициализируем Virtual Com Port
    VCP_ResetPort();        // Подтянули ножку d+ к нулю для правильной идентификации
    VCP_Init();        

    // Инициализируем датчики
    GYRO_INIT();
    ACC_INIT();
    MAG_INIT();

    // Инициализация таймера и его настройка
    TimerInit();  
}

// -------------------------------------------------------------------------------
// Настройка светодиодов
void LedsInit(void)
{
    STM_EVAL_LEDInit(LED4);
    STM_EVAL_LEDInit(LED3);
    STM_EVAL_LEDInit(LED5);
    STM_EVAL_LEDInit(LED7);
    STM_EVAL_LEDInit(LED9);
    STM_EVAL_LEDInit(LED10);
    STM_EVAL_LEDInit(LED8);
    STM_EVAL_LEDInit(LED6);
}

void Toggle_Leds(void)
{
    STM_EVAL_LEDOn(LED3);
    Delay(100);
    STM_EVAL_LEDOff(LED3);
    STM_EVAL_LEDOn(LED4);
    Delay(100);
    STM_EVAL_LEDOff(LED4);
    STM_EVAL_LEDOn(LED6);
    Delay(100);
    STM_EVAL_LEDOff(LED6);
    STM_EVAL_LEDOn(LED8);
    Delay(100);
    STM_EVAL_LEDOff(LED8);
    STM_EVAL_LEDOn(LED10);
    Delay(100);
    STM_EVAL_LEDOff(LED10);
    STM_EVAL_LEDOn(LED9);
    Delay(100);
    STM_EVAL_LEDOff(LED9);
    STM_EVAL_LEDOn(LED7);
    Delay(100);
    STM_EVAL_LEDOff(LED7);
    STM_EVAL_LEDOn(LED5);
    Delay(100);
    STM_EVAL_LEDOff(LED5);
}

void LedsOn(){
    STM_EVAL_LEDOn(LED3);
    STM_EVAL_LEDOn(LED4);
    STM_EVAL_LEDOn(LED5);
    STM_EVAL_LEDOn(LED6);
    STM_EVAL_LEDOn(LED7);
    STM_EVAL_LEDOn(LED8);
    STM_EVAL_LEDOn(LED9);
    STM_EVAL_LEDOn(LED10);
}

void LedsOff(){
    STM_EVAL_LEDOff(LED3);
    STM_EVAL_LEDOff(LED4);
    STM_EVAL_LEDOff(LED5);
    STM_EVAL_LEDOff(LED6);
    STM_EVAL_LEDOff(LED7);
    STM_EVAL_LEDOff(LED8);
    STM_EVAL_LEDOff(LED9);
    STM_EVAL_LEDOff(LED10);
}

void LedOn(Led_TypeDef Led){   STM_EVAL_LEDOn(Led);   }

void LedOff(Led_TypeDef Led){  STM_EVAL_LEDOff(Led);  }

// -------------------------------------------------------------------------------
// Настройка таймера
void TimerInit(void){

    NVIC_InitTypeDef NVIC_InitStructure;

    /* Enable TIM clock */
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_TIM4, ENABLE);

    /* Enable the Tim4 Interrupt */
    NVIC_InitStructure.NVIC_IRQChannel = TIM4_IRQn;
    NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority = 0;
    NVIC_InitStructure.NVIC_IRQChannelSubPriority = 0;
    NVIC_InitStructure.NVIC_IRQChannelCmd = ENABLE;
    NVIC_Init(&NVIC_InitStructure);

    TIM_TimeBaseInitTypeDef TIM_TimeBaseStructure;
    uint16_t TIMER_PRESCALER = TIM_PRESCALER;         
    /* Set the default configuration */
    TIM_TimeBaseStructInit(&TIM_TimeBaseStructure);
    TIM_TimeBaseStructure.TIM_Prescaler = TIMER_PRESCALER - 1;
    TIM_TimeBaseStructure.TIM_Period = TIM_PERIOD;
    TIM_TimeBaseInit(TIM4, &TIM_TimeBaseStructure);

    TIM_ITConfig(TIM4, TIM_IT_Update, ENABLE);
}

void TIM4_IRQHandler(void)
{ 
    LedOn(LED9);
    
    measure.TickCounter++;
    measure.new_tick_Flag = TRUE;
    
    TIM_ClearITPendingBit(TIM4, TIM_IT_Update);     // Очистим регистр наличия прерывания от датчика
    LedOff(LED9);
}

// -------------------------------------------------------------------------------
// Собственный callback для отработки поступления нового сообщения по com порту
void UserEP3_OUT_Callback(uint8_t *buffer){
    uint8_t bt;                 // Текущий обрабатываемый байт сообщения
    uint16_t con_sum = 0;       // Посчитанная контрольная сумма
    uint8_t len;                // Длина данных в сообщении
    uint8_t dataIndex = 0;      // Текущий индекс информации в сообщении 

    for(uint8_t i = 0; i < 64; i++){        // hw_config.c --> len(buffer) = 64
        bt = buffer[i];
        switch (decode_stage)
        {
        case Want7E:
            if (bt == 0x7e){
                decode_stage = WantE7;
                con_sum += bt;
            } else    decode_stage = Want7E;
            break;
        case WantE7:
            if (bt == 0xe7){
                decode_stage = WantFormat;
                con_sum += bt;
            } else    decode_stage = Want7E;
            break;
        case WantFormat:
            if (bt == 0xff){
                decode_stage = WantData;
                con_sum += bt;
                len = 2;        // Количество байт данных в сообщении с форматом 0xff
            } else    decode_stage = Want7E;
            break;
        case WantData:
            if (dataIndex < len){
                con_sum += bt;
                dataIndex++;
            }

            if (dataIndex == len){
                decode_stage = WantConSum; 
            }
            break;
        
        case WantConSum:
            decode_stage = Want7E;
            if (uint8_t(con_sum) == bt){
                COM_port.sending_package(ConfirmMessage, MaxCommand_Length);
                COM_port.new_message(buffer);
                return;
            }
            break;
        }
    }
}

// Функции для обработки поступивших команд
void restart(){
    NVIC_SystemReset();
}

void start_InitialSetting(){
    stage = InitialSetting;
}

void start_Measuring(){
    stage = Measuring;
}

void stop_Measuring(){
    stage = FooStage;
}

void stop_CollectingData(){
    stage = FooStage;
    measure.TickCounter = 0;
}

void error_msg(){
    COM_port.sending_package(ErrorMessage, MaxCommand_Length);
    Delay(1000);
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
    // for (int i = 0; i < 1000000; i++){}
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
