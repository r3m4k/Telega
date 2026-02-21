/* Includes H files ----------------------------------------------------------*/
#include "main.h"

/* Includes HPP files --------------------------------------------------------*/
#include "Consts.hpp"
#include "GPTimers.hpp"
#include "Leds.hpp"
#include "L3GD20.hpp"
#include "LSM303DLHC.hpp"
#include "TelegaPackage.hpp"
#include "ComPort.hpp"
#include "Message.hpp"
#include "CommandProcessing.hpp"
#include "NSigmaFilter.hpp"

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


/* Global variables ---------------------------------------------------------*/
typedef void
(* const pHandler)(void);

extern pHandler __isr_vectors[];

// ----------------------------------------------------------------------------
#define IST_VECTORS_NUM     98      // Количество векторов прерываний
#define InitFrameNum        256     // Количество пакетов для выставки
#define MessageLen          8       // Длина информационных сообщений
 

// Собственная таблица прерываний
__attribute__((aligned(128)))    // Cortex-M4 требует выравнивание по 128 байт!
_user_pHandler _user_vector_table[IST_VECTORS_NUM] = {0};

// -------------------------------------------------------------------------------

// Перечисление для стадии выполнения программы
enum class ProgramStages{
    BeforeBeginning,    // Фиктивная стадия программы (необходима для индикации первой смены стадии программы)
    FooStage,           // Данные с датчиков считываются, но не фильтруются и не отправляются
    InitialSetting,     // Сбор и отправка данных для выставки 
    Measuring,          // Сбор и отправка данных с частотой 4 Гц
};

// Тк будем менять стадии программы из других файлов, то разместим стадии в глобальной зоне видимости
auto stage = ProgramStages::FooStage;
auto previous_stage = ProgramStages::BeforeBeginning;

// ----------------------------------------------------------------------------

uint32_t tick_counter = 0;      // Счётчик тиков основного таймера
volatile bool timer_tick_flag = false;

// ----------------------------------------------------------------------------

// Периферия
STM_CppLib::Leds        leds;                   // Светодиоды на плате
STM_CppLib::L3GD20      sensor_L3GD20;          // Встроенный гироскоп
STM_CppLib::LSM303DLHC  sensor_LSM303DLHC;      // Встроенный датчик с акселерометром,
                                                // магнитным и температурным датчиками

// Обработчик поступивших команд
STM_CppLib::Commands::CommandManager command_manager;

// Интерфейсы связи
STM_CppLib::ComPort::ComPort com_port;

// Используемые таймеры
STM_CppLib::STM_Timer::Timer3<[](){
    /* Объявление лямбды, которая будет вызываться в прерывании */
    leds.ChangeLedStatus(LED9);
    timer_tick_flag = true;    
}>  timer3;

STM_CppLib::STM_Timer::Timer4<[](){
    /* Объявление лямбды, которая будет вызываться в прерывании */
    leds.ChangeLedStatus(LED6);
    leds.ChangeLedStatus(LED7);
}>  timer4;     // Таймер для мерцания светодиодами LED6, LED7


// -------------------------------------------------------------------------------


int main()
{
    /* ***************************************************************************
    * Загрузим собственную таблицу прерываний для возможности её модификации
    *************************************************************************** */

    __disable_irq();    // Отключим прерывания

    // Скопируем исходную таблицу прерываний
    memcpy(_user_vector_table, __isr_vectors, IST_VECTORS_NUM * sizeof(pHandler));

    SCB->VTOR = (uint32_t)_user_vector_table;

    __DSB();    // Ожидаем завершения записи в регистр VTOR
    __ISB();    // Сбрасываем конвейер команд, чтобы следующие инструкции и прерывания
                // использовали новую таблицу векторов

    __enable_irq();     // Включим прерывания

    // ---------------------------------------------------------------------------

    // Получаем текущие значения тактовых частот системы и настроим
    // SysTick для генерации прерываний с периодом 1 мс
    // Если конфигурация SysTick завершилась ошибкой – входим в бесконечный цикл
	RCC_GetClocksFreq(&RCC_Clocks);
	if (SysTick_Config(RCC_Clocks.HCLK_Frequency / 1000))
		while(true) {}
    
    // ---------------------------------------------------------------------------

    // Инициализируем всё оборудования
    InitAll();             
    
    // Поморгаем светодиодами после успешной инициализации
    leds.ToggleLeds();

    // ---------------------------------------------------------------------------

    // Используемые фильтры
    NSigmaFilter<TriaxialData, 4, 16> filter_acc(2.0);     // Фильтр ускорений
    NSigmaFilter<TriaxialData, 4, 16> filter_gyro(2.0);    // Фильтр угловой скорости 
    NSigmaFilter<float, 1, 16>        filter_temp(2.0);    // Фильтр температуры

    // Значения ускорений, угловой скорости и температуры для отправки
    TriaxialData acc_value;
    TriaxialData gyro_value;
    float temp_value;

    // Посылка данных
    // TODO: в дальнейшем, надо добавить датчик ДПП и пульт 
    STM_CppLib::STM_Packages::TelegaPackage telega_package(
        &acc_value, &gyro_value, &temp_value
    );

    // Счётчик, необходимый для снижения частоты опроса температурного датчика
    uint8_t sensor_reading_counter = 0;     

    // ---------------------------------------------------------------------------
    // Основной цикл программы
    while (true)
    {
        // Проверка очереди поступивших команд 
        if (!command_manager.command_queue.is_empty()){
            auto command = command_manager.command_queue.get();
            command.execute();
        }

        /* ***********************************************************************
        ШАБЛОН ОТРАБОТКИ СТАДИИ ПРОГРАММЫ:
        Каждая стадия (stage) отрабатывается по единому принципу:
        1. ИНИЦИАЛИЗАЦИЯ СТАДИИ (однократное выполнение при входе в стадию)
        2. ЦИКЛИЧЕСКОЕ ВЫПОЛНЕНИЕ ОСНОВНОЙ ЛОГИКИ СТАДИИ
        *********************************************************************** */

        switch (stage)
        {
        case ProgramStages::FooStage:
            if (previous_stage != ProgramStages::FooStage){
                previous_stage = ProgramStages::FooStage;
                // Выключим все таймеры
                timer3.Stop();
                timer3.ResetCounter();
                timer4.Stop();
                timer4.ResetCounter();
                // Включим все светодиоды
                leds.LedsOn();
            }

            // Периодическое чтение данных для поддержания температуры кристалла датчиков
            // Возможно, это излишне
            sensor_L3GD20.ReadData();
            sensor_LSM303DLHC.ReadData();

            break;

        case ProgramStages::InitialSetting:
            if (previous_stage != ProgramStages::InitialSetting){
                previous_stage = ProgramStages::InitialSetting;
                tick_counter = 0;
                sensor_reading_counter = 0;
                leds.LedsOff();
                timer4.ResetCounter();
                timer4.Start();
            }

            // Сбросим фильтры перед сбором данных
            filter_acc.reset();
            filter_gyro.reset();
            filter_temp.reset();

            for(int i = 0; i < InitFrameNum; i++){

                /* ***************************************************************
                * Параметры фильтров подобраны так, что все фильтры готовятся за 
                * одинаковое число итераций, что критически важно для корректности 
                * отработки цикла!
                *************************************************************** */

                while(!filter_acc.is_data_filtered() || !filter_gyro.is_data_filtered() || !filter_temp.is_data_filtered()){
                    // Считаем значения и добавим полученные значения в фильтры
                    sensor_L3GD20.ReadGyro();
                    filter_gyro.append_value(sensor_L3GD20.gyro_data);
                    
                    sensor_LSM303DLHC.ReadAcc();
                    filter_acc.append_value(sensor_LSM303DLHC.acc_data);

                    // Данные температуры будем считывать в 4 раза реже
                    if (sensor_reading_counter++ % 4 == 0) {
                        sensor_LSM303DLHC.ReadTemp();
                        filter_temp.append_value(sensor_LSM303DLHC.temperature);
                    }
                }

                // Обновим данные с датчиков
                acc_value = filter_acc.get_filtered_data();
                gyro_value = filter_gyro.get_filtered_data();
                temp_value = filter_temp.get_filtered_data();

                // Обновим данные в посылке и отправим её по com-порту
                telega_package.UpdateData();
                telega_package.UpdateTime(tick_counter++);  // Фиктивное изменение метки времени
                telega_package.UpdateControlSum();
                com_port.SendPackage(telega_package);

                // Сбросим фильтры
                filter_acc.reset();
                filter_gyro.reset();
                filter_temp.reset();
            }

            // В конце отправим сообщение об окончании выставки
            send_end_of_initial_setting_msg();

            stage = ProgramStages::FooStage;
            break;

        case ProgramStages::Measuring:
            if (previous_stage != ProgramStages::Measuring){
                previous_stage = ProgramStages::Measuring;
                tick_counter = 0;
                sensor_reading_counter = 0;
                leds.LedsOff();
                // Запустим таймер сбора данных с частотой 4 Гц
                timer3.ResetCounter();
                timer3.Start();
                // Запустим таймер индикации работы
                timer4.ResetCounter();
                timer4.Start();
            }

            if (timer_tick_flag){

                /* ***********************************************************************
                * ВАЖНО! Длительность выполнения этой стадии не должна превышать 200мс
                * для обеспечения выдачи данных с частотой 4 Гц. Длительность выполнения
                * можно менять с помощью шаблонных параметров NSigmaFilter.
                *********************************************************************** */

                leds.LedOn(LED5);

                while(!filter_acc.is_data_filtered() || !filter_gyro.is_data_filtered() || !filter_temp.is_data_filtered()){
                    // Считаем значения и добавим полученные значения в фильтры
                    sensor_L3GD20.ReadGyro();
                    filter_gyro.append_value(sensor_L3GD20.gyro_data);

                    sensor_LSM303DLHC.ReadAcc();
                    filter_acc.append_value(sensor_LSM303DLHC.acc_data);
    
                    // Данные температуры будем считывать в 4 раза реже
                    if (sensor_reading_counter++ % 4 == 0) {
                        sensor_LSM303DLHC.ReadTemp();
                        filter_temp.append_value(sensor_LSM303DLHC.temperature);
                    }
                }

                // Обновим данные с датчиков
                acc_value = filter_acc.get_filtered_data();
                gyro_value = filter_gyro.get_filtered_data();
                temp_value = filter_temp.get_filtered_data();

                // Обновим данные в посылке и отправим её по com-порту
                telega_package.UpdateData();
                telega_package.UpdateTime(tick_counter++);
                telega_package.UpdateControlSum();
                com_port.SendPackage(telega_package);

                // Сбросим фильтры
                filter_acc.reset();
                filter_gyro.reset();
                filter_temp.reset();

                leds.LedOff(LED5);
                timer_tick_flag = false;
            }

            break;
        }
    }
}

// -------------------------------------------------------------------------------
// Инициализация оборудования
// -------------------------------------------------------------------------------
void InitAll(){
    leds.Init();
    leds.LedsOn();

    sensor_L3GD20.Init();
    sensor_LSM303DLHC.Init();
    
    com_port.Init();

    // Настройка основного таймера с периодом счёта в 250 мс (4 Гц)
    uint32_t tim3_period = 2500 - 1;
    timer3.Init(tim3_period);

    // Настройка таймера для мерцания светодиодами с периодом счёта в 2 с
    uint32_t tim4_period = 20000 - 1;
    timer4.Init(tim4_period);
}

// -------------------------------------------------------------------------------
// Функции для отработки поступивших команд
// -------------------------------------------------------------------------------

void UserEP3_OUT_Callback(uint8_t *buffer){
    STM_CppLib::Message message(buffer);
    com_port.EP3_OUT_Callback(message);
}

// Функции для обработки поступивших команд
void restart(){
    NVIC_SystemReset();
}

void start_InitialSetting(){
    stage = ProgramStages::InitialSetting;
}

void start_Measuring(){
    stage = ProgramStages::Measuring;
}

void stop_Measuring(){
    stage = ProgramStages::FooStage;
}

void stop_CollectingData(){
    stage = ProgramStages::FooStage;
}

// -------------------------------------------------------------------------------
// Отправка предопределённых сообщений
// -------------------------------------------------------------------------------

void send_confirm_msg(){
    constexpr uint8_t ConfirmMessage[MessageLen] = {0x7e, 0xe7, 0xff, 0xaa, 0xaa, 0xb8, 0};
    STM_CppLib::Message message(ConfirmMessage, MessageLen);
    com_port.SendMessage(message);   // В таком случае передаём lvalue ссылку
}

void send_hello_msg(){
    const char* text = "STM_Telega by Romanovskiy Roma\n";
    STM_CppLib::Message message(reinterpret_cast<const uint8_t*>(text), strlen(text));
    com_port.SendMessage(message);
}

void send_error_msg(){
    constexpr uint8_t ErrorMessage[MessageLen] = {0x7e, 0xe7, 0xff, 0xff, 0xff, 0x62, 0};
    STM_CppLib::Message message(ErrorMessage, MessageLen);
    com_port.SendMessage(message);
}

void send_end_of_initial_setting_msg(){
    constexpr uint8_t EndOfInitialSettingMessage[MessageLen] = {0x7e, 0xe7, 0xff, 0xba, 0xab, 0xc9, 0};
    STM_CppLib::Message message(EndOfInitialSettingMessage, MessageLen);
    com_port.SendMessage(message);
}

// -------------------------------------------------------------------------------
// Системные функции
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
