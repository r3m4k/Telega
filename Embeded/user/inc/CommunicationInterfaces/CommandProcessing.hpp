/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __COMMAND_PROCESSING_HPP
#define __COMMAND_PROCESSING_HPP

/** ****************************************************************************
 * @file CommandProcessing.hpp
 * @brief Модуль обработки команд для встроенной системы.
 * 
 * Данный модуль предоставляет механизмы для регистрации, сравнения и выполнения 
 * команд в системе. Команды представляются в виде байтовых последовательностей 
 * фиксированной длины и связываются с обработчиками - функциями без аргументов.
 * 
 * @version 1.0.0
 * @date Январь 2026
 * @author Романовский Роман
 **************************************************************************** */

/* Includes ------------------------------------------------------------------*/
#include <cstring>

#include "main.h"
#include "Message.hpp"
#include "StaticQueue.hpp"

/* Defines -------------------------------------------------------------------*/
#define CommandLength   8   // Длина массива для кодировки команды

/* Using  --------------------------------------------------------------------*/
using CommandHandlerFunc = void(*)(void);

/* Global variables ----------------------------------------------------------*/

namespace STM_CppLib{
    namespace Commands{

/** ****************************************************************************
 * @class CommandHandler
 * @brief Класс-обёртка для функции-обработчика команды.
 * 
 * Инкапсулирует указатель на функцию, предоставляет безопасный интерфейс 
 * для выполнения обработчика. Поддерживает только копирование, перемещение 
 * запрещено.
 **************************************************************************** */

class CommandHandler{
    CommandHandlerFunc handler;

public:
    // 
    CommandHandler(): handler(nullptr) {}

    // Конструктор с функцией без аргументов
    CommandHandler(CommandHandlerFunc _handler): handler(_handler){}

    // Конструктор копирования
    CommandHandler(const CommandHandler& other){
        handler = other.handler;
    }
    
    // Оператор присваивания копированием
    CommandHandler& operator=(const CommandHandler& other){
        if (this != &other){
            handler = other.handler;
        }        
        return *this;
    }

    // Конструктор перемещения 
    CommandHandler(CommandHandler&& other) noexcept = delete;
    
    // Оператор присваивания перемещением
    CommandHandler& operator=(CommandHandler&& other) noexcept = delete;

    // Запуск обработчика
    void execute(){
        if (handler) {
            handler();
        }
    }
};

/** ****************************************************************************
 * @class Command
 * @brief Класс, описывающий команду системы.
 * 
 * Содержит байтовый код команды и связанный с ней обработчик.
 * Предоставляет операторы сравнения с сообщениями и другими командами.
 **************************************************************************** */

class Command{
public:
    uint8_t command_code[CommandLength];    // Массив для кодировки команды
    CommandHandler command_handler;         // Обработчик команды
    
    // Конструктор с массивом и обработчиком
    Command(const uint8_t* _command_code, CommandHandlerFunc _handler_func): 
            command_handler(_handler_func){
        std::memcpy(command_code, _command_code, CommandLength);
    }

    // Конструктор копирования
    Command(const Command& other) : command_handler(other.command_handler) {
        std::memcpy(command_code, other.command_code, CommandLength);
    }
    
    // Оператор присваивания копированием
    Command& operator=(const Command& other){
        if (this != &other){
            std::memcpy(command_code, other.command_code, CommandLength);
            command_handler = other.command_handler;
        }        
        return *this;
    }

    // Конструктор перемещения 
    Command(Command&& other) noexcept = delete;
    
    // Оператор присваивания перемещением
    Command& operator=(Command&& other) noexcept = delete;

    // Оператор сравнения
    bool operator==(const Message& msg){
        return std::memcmp(command_code, msg.bytes_msg, CommandLength) == 0;
    }

    // Оператор сравнения с массивом байтов
    bool operator==(const uint8_t* code) const {
        return std::memcmp(command_code, code, CommandLength) == 0;
    }
};

// -----------------------------------------------------------------------------
/*!
 * @defgroup SupportedCommands Поддерживаемые команды
 * @brief Предопределенные команды системы.
 * 
 * Каждая команда представлена в виде глобального объекта Command 
 * с уникальным байтовым кодом и привязанным обработчиком.
 * @{
 */

//! Количество поддерживаемых команд
inline constexpr uint8_t num_of_supported_commands = 1;

/*!
 * @var Restart
 * @brief Команда перезагрузки микроконтроллера.
 * 
 * Код команды: {0x7e, 0xe7, 0xff, 0xff, 0x00, 0x63, 0x00, 0x00}
 * Обработчик: restart()
 */
inline constexpr uint8_t Restart_Code[CommandLength] = 
        {0x7e, 0xe7, 0xff, 0xff, 0x00, 0x63, 0x00, 0x00};
inline Command Restart(Restart_Code, restart);

/** @} */ // конец группы SupportedCommands


/** ****************************************************************************
 * @class CommandManager
 * @brief Менеджер команд системы.
 * 
 * Управляет набором поддерживаемых команд, обеспечивает их сопоставление
 * с поступающими сообщениями и помещение в очередь на выполнение.
  **************************************************************************** */
 
class CommandManager{
private:
    // Массив поддерживаемых команд
    inline static Command supported_commands[num_of_supported_commands] = {
        Restart
    };

public:
    StaticQueue<CommandHandler, 4> command_queue;      // Статичная очередь поступивших команд

    // Метод для проверки, является ли сообщение одной из поддерживаемых команд
    const Command* match_message_to_command(Message& message) const {
        for (uint8_t i = 0; i < num_of_supported_commands; i++){
            if (supported_commands[i] == message){
                return &supported_commands[i];
            }
        }
        return nullptr;
    }

    // Добавление команды в очередь команд
    bool add_command(const Command& command){
        if(!command_queue.is_full()){
            command_queue.put(command.command_handler);
            return true;
        }
        return false;
    }

};

    } // namespace Commands
} // namespace STM_CppLib

#endif /*   __COMMAND_PROCESSING_HPP   */