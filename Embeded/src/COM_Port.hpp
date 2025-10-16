/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __COM_PORT_HPP
#define __COM_PORT_HPP

/* Includes ------------------------------------------------------------------*/
#include <cstring>

#include "main.h"
#include "hw_config.h"
#include "VCP_F3.h"
#include "Data.hpp"
#include "Frame.hpp"

/* Defines -------------------------------------------------------------------*/
#define ReceiveBuffer_Length    8       // Обрабатываемая длина полученных сообщений
#define MaxCommands_Num         8       // Максимальная длина очереди команд
#define MaxCommand_Length       8       // Максимальная длина команды

// -------------------------------------------------------------------------------
// Сообщения, которые будем отправлять в ответ по COM порту
uint8_t ErrorMessage[MaxCommand_Length] =           {0x7e, 0xe7, 0xff, 0xff, 0xff, 0x62, 0};           // Сообщение, которое отправляется при получении неизвестного сообщения 
uint8_t ConfirmMessage[MaxCommand_Length] =         {0x7e, 0xe7, 0xff, 0xaa, 0xaa, 0xb8, 0};           // Сообщение, которое отправляется при успешном получении сообщения
uint8_t EndOfInitialSetting[MaxCommand_Length] =    {0x7e, 0xe7, 0xff, 0xba, 0xab, 0xc9, 0};           // Сообщение, которое отправляется при успешном получении сообщения

// Список обрабатываемых сообщений из COM порта
uint8_t Restart_cmd[MaxCommand_Length] = {0x7e, 0xe7, 0xff, 0xff, 0x00, 0x63, 0};

#define Start_InitialSetting        {0x7e, 0xe7, 0xff, 0xab, 0xba, 0xc9, 0}
#define Start_Measuring             {0x7e, 0xe7, 0xff, 0xbc, 0xcb, 0xeb, 0}
#define Stop_Measuring              {0x7e, 0xe7, 0xff, 0xcd, 0xdc, 0x0d, 0}
#define Stop_CollectingData         {0x7e, 0xe7, 0xff, 0xde, 0xed, 0x2f, 0}
// -------------------------------------------------------------------------------
// Структура для описания команды
typedef struct Command
{
    uint8_t command_code[MaxCommand_Length];        // Массив, кодирующий команду
    void (*command_function)(void);                 // Указатель на функцию выполнения команды
} Command;

// Структура для описания всех команд, поддерживаемые в данном проекте 
typedef struct Commands
{
    // Начало выставки датчиков
    Command command_start_InitialSetting = {
        .command_code = Start_InitialSetting,
        .command_function = start_InitialSetting
    };

    // Начало измерений
    Command command_start_Measuring = {
        .command_code = Start_Measuring,
        .command_function = start_Measuring
    };

    // Конец измерений
    Command command_stop_Measuring = {
        .command_code = Stop_Measuring,
        .command_function = stop_CollectingData
    };

    // Неизвестная команда
    Command unknown_command = {
        .command_code = {0},
        .command_function = (error_msg)
    };

} Commands;

// -------------------------------------------------------------------------------
// Класс полученных сообщений по COM порту
class Message
{
    uint8_t receive_Buffer[ReceiveBuffer_Length];   // Полученное сообщение
public:
    void new_message(uint8_t *buffer){
        for (uint8_t i = 0; i < ReceiveBuffer_Length; i++){
            receive_Buffer[i] = buffer[i];
            buffer[i] = 0;  // Очистим входной буфер
        }
    }
    
    uint8_t* get_message(){
        return receive_Buffer;
    }

    void set_message(uint8_t *buffer){
        memcpy(receive_Buffer, buffer, ReceiveBuffer_Length);
    }
};

// -------------------------------------------------------------------------------
// Класс очереди поступивших команд
class Command_Queue{
    /*
    Класс, описывающий статичную очередь, которая не использует функции аллокатора и имеющая фиксированную максимальную длину.
    Эта очередь инициализируется при инициализации класса COM_Port, поэтому она будет храниться в той же области памяти.
    */
    Message messages[MaxCommands_Num];     // Создадим массив команд, присланных по COM порту
    int8_t lastIndex = -1;                 // Индекс последнего элемента в очереди. Если lastIndex == -1, то очередь пуста
    Commands command_list;                 // Структура со всеми поддерживаемыми командами

    // Временные переменные для избежания их постоянной инициализации
    uint8_t i;
    Message tmp_message;

    // Декодер сообщения, полученного по COM порту, который возвращает функцию отработки команды
    void (*decode_msg(Message &msg))(void){
        // start_InitialSetting
        if (!(memcmp(msg.get_message(), command_list.command_start_InitialSetting.command_code, MaxCommand_Length))){
            return command_list.command_start_InitialSetting.command_function;
        }
        
        // start_Measuring
        if (!(memcmp(msg.get_message(), command_list.command_start_Measuring.command_code, MaxCommand_Length))){
            return command_list.command_start_Measuring.command_function;
        }
        
        // stop_Measuring
        if (!(memcmp(msg.get_message(), command_list.command_stop_Measuring.command_code, MaxCommand_Length))){
            return command_list.command_stop_Measuring.command_function;
        }
        
        // Если команда не распознана, то отправим ответ по COM порту, сообщающий данную проблему. И включим красные светодиод
        LedsOff();
        LedOn(LED10); LedOn(LED3);
        return command_list.unknown_command.command_function;
    }

public:
    // Получение первого элемента очереди
    void (*get())(void){
        tmp_message.set_message(messages[0].get_message());  // Скопируем первую команду во временную переменную
        // Сместим все элементы очереди, тк мы скопировали первый элемент
        for (i = 1; i < MaxCommands_Num; i++){
            messages[i-1].set_message(messages[i].get_message());
        }
        lastIndex--;
        return decode_msg(tmp_message);
    }

    // Добавление нового элемента в конец очереди
    void put(uint8_t *buffer){
        if (!(memcmp(buffer, Restart_cmd, MaxCommand_Length))){
            restart();
            return;
        }

        if (isFull()){
            // Проверим наличие свободного места
            // Если места нет, то поморгаем 3 раза красным светодиодом 
            for (i = 0; i < 3; i++){
                LedOn(LED10);
                Delay(100);
                LedOff(LED10);
                Delay(100);
            }
            return;
        }

        // Добавим элемент в очередь
        messages[++lastIndex].set_message(buffer);
    }

    bool isEmpty(){
        return (lastIndex == -1);
    }

    bool isFull(){
        return (lastIndex == MaxCommands_Num - 1);
    }
};

// -------------------------------------------------------------------------------
// Класс для работы с COM портом
class COM_Port{

    int16_t tmp;
    uint8_t i;  

    // #############################################
    typedef struct Frame_Struct
    {
        uint8_t X_coord[2];
        uint8_t Y_coord[2];
        uint8_t Z_coord[2];
    }Frame_Struct;
    
    typedef struct Data_Struct{
        Frame_Struct Acc;
        Frame_Struct Gyro;
    }Data_Struct;
    
    // Структура для отправки Data
    typedef struct outbuf_typeData
    {
        // 2 байта - заголовок посылки, 1 байт - формат, 1 байт - размер данных в посылке
        uint8_t Header[4] = {0x7E, 0xE7, 0xC8, 0x10};      // 0xC8 - формат пакета данных

        uint8_t Time[2];
        Data_Struct data_struct;
        uint8_t Temp[2];

        uint8_t checksum = 0;
    } outbuf_type1;

    //#############################################

    // Заполнение структуры frame_struct данными из frame
    void filling_FrameStruct(Frame &frame, Frame_Struct &frame_struct){
        for (i = 0; i < 3; i++){
            // ((uint8_t*)&frame_struct)[0 + 2 * i] = frame_struct.XYZ_coord_lowBit  (т.е младший разряд Acc.XYZ_coord)
            // ((uint8_t*)&frame_struct)[1 + 2 * i] = frame_struct.XYZ_coord_highBit (т.е старший разряд Acc.XYZ_coord)
            tmp = round(frame[i] * 1000);
            ((uint8_t*)&frame_struct)[0 + 2 * i] = tmp;                 // Младший разряд
            ((uint8_t*)&frame_struct)[1 + 2 * i] = tmp >> 8;            // Старший разряд
        }
    }
    
    // Заполнение структуры data_struct данными из data
    void filling_DataStruct(Data &data, Data_Struct &data_struct){
        filling_FrameStruct(data.Acc, data_struct.Acc);
        filling_FrameStruct(data.Gyro, data_struct.Gyro);
    }
   
    //#############################################
    
public:
    Command_Queue command_queue;

    // Отправка посылки с одним пакетом измерений data
    void sending_data(uint32_t Ticks, Data &data){

        outbuf_type1 Out_Buf;

        tmp = (uint16_t)Ticks;
        ((uint8_t*)&Out_Buf)[4] = tmp;                 // Младший разряд счётчика таймера
        ((uint8_t*)&Out_Buf)[5] = tmp >> 8;            // Старший разряд счётчика таймера

        filling_DataStruct(data, Out_Buf.data_struct);

        // ((uint8_t*)&Out_Buf)[sizeof(Out_Buf) - 3] = data.Temp_lowBit  (т.е младший разряд Temp)
        // ((uint8_t*)&Out_Buf)[sizeof(Out_Buf) - 2] = data.Temp_highBit (т.е старший разряд Temp)
        tmp = round(data.Temp * 100);
        ((uint8_t*)&Out_Buf)[sizeof(Out_Buf) - 3] = tmp;                 // Младший разряд
        ((uint8_t*)&Out_Buf)[sizeof(Out_Buf) - 2] = tmp >> 8;            // Старший разряд

        // Посчитаем контрольную сумму
        tmp = 0;
        for (i = 0; i < sizeof(Out_Buf) - 1; i++){
            tmp += ((uint8_t*)&Out_Buf)[i];       
        }
        Out_Buf.checksum = tmp;

        CDC_Send_DATA((uint8_t*)&Out_Buf, sizeof(Out_Buf));
    }

    // Отправка произвольного пакета данных
    void sending_package(uint8_t *package){
        CDC_Send_DATA(package, sizeof(package));
    }

    // Отправка пакета данных с заданной длиной
    void sending_package(uint8_t *package, uint8_t size){
        CDC_Send_DATA(package, size);
    }

    // Получение нового сообщения
    void new_message(uint8_t *msg_buffer){
        command_queue.put(msg_buffer);
    }
};

#endif /*    __COM_PORT_HPP    */