/* Includes H files ----------------------------------------------------------*/
#include "main.h"

/* Includes HPP files --------------------------------------------------------*/
#include "Consts.hpp"
#include "GPTimers.hpp"
#include "Leds.hpp"
#include "L3GD20.hpp"
#include "LSM303DLHC.hpp"
#include "TelegaPackage.hpp"

#include "RingBuffer.hpp"
#include "UsbPort.hpp"
#include "MessagePackage.hpp"
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


/* Defines -------------------------------------------------------------------*/
#define IST_VECTORS_NUM     98      // Количество векторов прерываний
#define InitFrameNum        256     // Количество пакетов для выставки

/* Global variables ---------------------------------------------------------*/

typedef void
(* const pHandler)(void);

extern pHandler __isr_vectors[];

/* ****************************************************************************
 * Пользовательские переменные
 *************************************************************************** */

// Собственная таблица прерываний
__attribute__((aligned(128)))    // Cortex-M4 требует выравнивание по 128 байт!
_user_pHandler _user_vector_table[IST_VECTORS_NUM] = {0};

// ----------------------------------------------------------------------------

// Необходимые счётчик и флаг
uint32_t tick_counter = 0;
volatile bool timer_tick_flag = false;

// Счётчик, необходимый для снижения частоты опроса температурного датчика
uint8_t sensor_reading_counter = 0;     

// ----------------------------------------------------------------------------

// Светодиоды на плате
STM_CppLib::Leds leds;

// Обработчик поступивших команд
Commands::CommandManager command_manager;

// Интерфейсы связи
STM_CppLib::UsbPort::UsbPort com_port;

// Используемые таймеры -------------------------------------------------------

// Таймер для чтения данных
STM_CppLib::STM_Timer::Timer3<[](){
    /* Объявление лямбды, которая будет вызываться в прерывании */
    leds.ChangeLedStatus(LED9);
    timer_tick_flag = true;    
}>  timer3;

// Таймер для мерцания светодиодами LED6, LED7
STM_CppLib::STM_Timer::Timer4<[](){
    /* Объявление лямбды, которая будет вызываться в прерывании */
    leds.ChangeLedStatus(LED6);
    leds.ChangeLedStatus(LED7);
}>  timer4;     // Таймер для мерцания светодиодами LED6, LED7


/* ****************************************************************************
 * Объявление датчиков, используемых фильтров и пакетов данных
 *************************************************************************** */

STM_CppLib::L3GD20      sensor_L3GD20;          // Встроенный гироскоп
STM_CppLib::LSM303DLHC  sensor_LSM303DLHC;      // Встроенный датчик с акселерометром,
                                                // магнитным и температурным датчиками

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
Packages::TelegaPackage telega_package(
    &tick_counter, &acc_value, &gyro_value, &temp_value
);

/* ****************************************************************************
 * Описание стадий программы
 *************************************************************************** */

class ProgramStage{
    CommandHandlerFunc init_func;
    CommandHandlerFunc execute_func;
    
public:
    bool is_init = false;

    ProgramStage(CommandHandlerFunc _init_func, CommandHandlerFunc _execute_func):
        init_func(_init_func), execute_func(_execute_func) {}

    void init(){
        init_func();
        is_init = true;
    }

    void execute(){
        execute_func();
    }
};

// -------------------------------------------------------------------------------

// Очередь стадий программ (используется для смены стадий программ).
RingBuffer<ProgramStage*, 2> program_stage_queue;

// Поддерживаемые стадии программы
ProgramStage FooStage(FooStage_init, FooStage_execute);
ProgramStage StaticStage(StaticStage_init, StaticStage_execute);
ProgramStage MeasuringStage(MeasuringStage_init, MeasuringStage_execute);


/* **************************************************************************** */

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

    // Изначально добавим FooStage в program_stage_queue
    program_stage_queue.put(&FooStage);
    ProgramStage* current_stage_ptr = &FooStage;

    // ---------------------------------------------------------------------------
    // Основной цикл программы
    while (true)
    {
        // Выполним все поступившие команды при их наличии
        while (!command_manager.command_queue.is_empty()){
            auto command = command_manager.command_queue.get();
            command.execute();
        }

        // Сменим current_stage_ptr, если есть элементы в очереди program_stage_queue
        if(!program_stage_queue.is_empty()){
            current_stage_ptr->is_init = false;     // Сбросим флаг у текущей стадии
            current_stage_ptr = program_stage_queue.get();
        }

        /* ***********************************************************************
        ШАБЛОН ОТРАБОТКИ СТАДИИ ПРОГРАММЫ:
        Каждая стадия (ProgramStage) отрабатывается по единому принципу:
        1. ИНИЦИАЛИЗАЦИЯ СТАДИИ (однократное выполнение при входе в стадию)
        2. ЦИКЛИЧЕСКОЕ ВЫПОЛНЕНИЕ ОСНОВНОЙ ЛОГИКИ СТАДИИ
        *********************************************************************** */

        if (!current_stage_ptr->is_init){
            current_stage_ptr->init();
        }
        current_stage_ptr->execute();        
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
// Функции для отработки стадий программы
// -------------------------------------------------------------------------------

// Функция для инициализации FooStage
void FooStage_init(){
    // Выключим все таймеры
    timer3.Stop();
    timer3.ResetCounter();
    timer4.Stop();
    timer4.ResetCounter();
    // Включим все светодиоды
    leds.LedsOn();
}

// Функция для исполнения FooStage 
void FooStage_execute(){
    // Периодическое чтение данных для поддержания температуры кристалла датчиков
    // Возможно, это излишне
    sensor_L3GD20.ReadData();
    sensor_LSM303DLHC.ReadData();
}

// Функция для инициализации StaticStage
void StaticStage_init(){
    tick_counter = 0;
    sensor_reading_counter = 0;
    leds.LedsOff();
    timer4.ResetCounter();
    timer4.Start();
}

// Функция для исполнения StaticStage
void StaticStage_execute(){
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
        telega_package.UpdateControlSum();
        com_port.SendPackage(telega_package);

        // Сбросим фильтры
        filter_acc.reset();
        filter_gyro.reset();
        filter_temp.reset();
    }

    // В конце отправим сообщение об окончании выставки
    send_end_of_static_init_msg();
    program_stage_queue.put(&FooStage);
}

// Функция для инициализации MeasuringStage
void MeasuringStage_init(){
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

// Функция для исполнения MeasuringStage 
void MeasuringStage_execute(){
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
    telega_package.UpdateControlSum();
    com_port.SendPackage(telega_package);

    // Сбросим фильтры
    filter_acc.reset();
    filter_gyro.reset();
    filter_temp.reset();

    leds.LedOff(LED5);
    timer_tick_flag = false;
}
}

// -------------------------------------------------------------------------------
// Функции для отработки поступивших команд
// -------------------------------------------------------------------------------

void UserEP3_OUT_Callback(uint8_t *buffer){
    Messages::SizedMessage<VCP_BUFFER_SIZE> message(buffer, VCP_BUFFER_SIZE);
    com_port.EP3_OUT_Callback(message);
}

// Функции для обработки поступивших команд
void restart(){
    NVIC_SystemReset();
}

void set_FooStage(){
    program_stage_queue.put(&FooStage);
}

void set_StaticStage(){
    program_stage_queue.put(&StaticStage);;
}

void set_MeasureStage(){
    program_stage_queue.put(&MeasuringStage);
}

// -------------------------------------------------------------------------------
// Отправка предопределённых сообщений
// -------------------------------------------------------------------------------


void send_confirm_msg(){
    const char* text = "CONFIRM_RECEIVED_COMMAND";
    Packages::MessagePackage msg_package(text, strlen(text));
    com_port.SendPackage(msg_package);
}

void send_handshake_ack(){
    const char* text = "IMU_STM32_ACK";
    Packages::MessagePackage msg_package(text, strlen(text));
    com_port.SendPackage(msg_package);
}

void send_heartbeat_ack(){
    const char* text = "IMU_STM32_ALIVE";
    Packages::MessagePackage msg_package(text, strlen(text));
    com_port.SendPackage(msg_package);
}

void send_error_msg(){
    const char* text = "UNKNOWN_COMMAND";
    Packages::MessagePackage msg_package(text, strlen(text));
    com_port.SendPackage(msg_package);
}

void send_end_of_static_init_msg(){
    const char* text = "END_OF_STATIC_INIT";
    Packages::MessagePackage msg_package(text, strlen(text));
    com_port.SendPackage(msg_package);
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
