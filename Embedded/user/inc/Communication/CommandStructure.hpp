/** ****************************************************************************
 * @file    CommandStructure.hpp
 * @author  Романовский Роман
 * @brief   Структурные классы команд для модуля обработки команд.
 *
 * @details Определяет иерархию классов, описывающих команду как связку
 *          кода (байтового массива произвольной длины) и обработчика
 *          (функции без аргументов). Конкретные объекты команд и их
 *          менеджер вынесены в CommandProcessing.hpp.
 *
 *          Классы:
 *          - CommandHandler — обёртка для функции-обработчика.
 *          - BaseCommand    — нешаблонный класс команды (код + обработчик).
 *                             Код представлен view-объектом Message, ссылающимся
 *                             на буфер наследника.
 *          - Command<N>     — шаблонный наследник с собственным буфером для
 *                             кода длиной N байт.
 *          - ByteCommand<N> — наследник Command<N> с CTAD из массива uint8_t.
 *          - StringCommand<N> — наследник Command<N> с CTAD из строкового
 *                             литерала (завершающий '\0' отбрасывается).
 *************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef COMMAND_STRUCTURE_HPP
#define COMMAND_STRUCTURE_HPP

/* Includes ------------------------------------------------------------------*/
#include <cstring>
#include <stdint.h>

#include "main.h"
#include "Messages.hpp"

/* Defines -------------------------------------------------------------------*/

/* Usings --------------------------------------------------------------------*/
/**
 * @brief   Тип функции-обработчика команды (без аргументов и возврата).
 */
using CommandHandlerFunc = void(*)(void);

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------
namespace Commands{

    /**
     * @brief   Политика подтверждения получения команды.
     * @details Указывается при регистрации команды и определяет, отправляется
     *          ли Send_Confirm_Cmd при её приёме декодером.
     *          - Required — при приёме команды декодер отправляет подтверждение
     *            (для urgent — немедленно из IRQ, для deferred — через очередь).
     *          - NotRequired — подтверждение не отправляется. Используется
     *            для команд, сам смысл которых — ответ или запрос
     *            (handshake ack, heartbeat ack, запрос confirm от ПК и т.п.).
     */
    enum class ConfirmPolicy{
        Required,
        NotRequired
    };

    /**
     * @brief   Обёртка для функции-обработчика команды.
     * @details Инкапсулирует указатель на функцию, предоставляет безопасный
     *          запуск (nullptr-обработчик просто ничего не делает).
     *          Поддерживает только копирование; перемещение запрещено.
     */
    class CommandHandler{
        CommandHandlerFunc handler;

    public:
        /**
         * @brief   Конструктор по умолчанию (nullptr-обработчик).
         * @details Пустой хэндлер безопасен — execute() на nullptr ничего
         *          не делает. Default-ctor требуется, в частности, для
         *          массивов слотов в SpscRingBuffer<CommandHandler, N>.
         */
        CommandHandler(): handler(nullptr) {}

        /**
         * @brief   Конструктор из указателя на функцию.
         */
        CommandHandler(CommandHandlerFunc h): handler(h) {}

        /**
         * @brief   Конструктор копирования.
         */
        CommandHandler(const CommandHandler& other): handler(other.handler) {}

        /**
         * @brief   Оператор присваивания копированием.
         */
        CommandHandler& operator=(const CommandHandler& other){
            if (this != &other){
                handler = other.handler;
            }
            return *this;
        }

        /**
         * @brief   Move-операции запрещены.
         */
        CommandHandler(CommandHandler&&) noexcept = delete;
        CommandHandler& operator=(CommandHandler&&) noexcept = delete;

        /**
         * @brief   Запуск обработчика.
         * @details Если handler == nullptr, вызов игнорируется.
         */
        void execute() const {
            if (handler){
                handler();
            }
        }
    };

    // -------------------------------------------------------------------------

    /**
     * @brief   Нешаблонный базовый класс команды.
     * @details Содержит код команды (view-объект Message, ссылающийся на буфер
     *          наследника) и обработчик. Хранение и размер буфера — забота
     *          наследника Command<N>. BaseCommand позволяет складывать команды
     *          разной длины кода в один массив указателей на базу.
     * @note    Поля code/handler публичные — в стиле остальных классов проекта
     *          (ср. Messages::bytes_msg).
     */
    class BaseCommand{
    public:
        Messages::Message code;         ///< View на буфер кода команды
        CommandHandler handler;         ///< Обработчик команды
        ConfirmPolicy confirm_policy;   ///< Политика подтверждения при приёме

        /**
         * @brief   Конструктор с привязкой к внешнему буферу.
         * @param   buf   Указатель на буфер кода (живёт в наследнике).
         * @param   size  Длина кода в байтах (msg_size).
         * @param   h     Функция-обработчик команды.
         */
        BaseCommand(uint8_t* buf, uint8_t size, CommandHandlerFunc h, ConfirmPolicy policy):
            code(buf, size), handler(h), confirm_policy(policy) {}

        /**
         * @brief   Деструктор по умолчанию.
         */
        ~BaseCommand() = default;

        /**
         * @brief   Копирование и перемещение запрещены.
         * @details Команды — глобальные объекты, копировать их нет смысла.
         *          Массивы указателей на BaseCommand в CommandManager
         *          хранят ссылки, а не копии.
         */
        BaseCommand(const BaseCommand&) = delete;
        BaseCommand& operator=(const BaseCommand&) = delete;
        BaseCommand(BaseCommand&&) noexcept = delete;
        BaseCommand& operator=(BaseCommand&&) noexcept = delete;
    };

    // -------------------------------------------------------------------------

    /**
     * @brief   Команда с собственным буфером кода фиксированной длины.
     * @tparam  N   Длина кода в байтах.
     * @details Наследник BaseCommand, владеющий буфером-массивом для кода.
     *          В конструкторе копирует N байт из переданного указателя
     *          в собственный буфер и инициализирует BaseCommand view-объектом
     *          на этот буфер.
     *
     *          Для удобного создания из массивов/литералов следует
     *          использовать наследников ByteCommand<N> и StringCommand<N>,
     *          у каждого из которых есть собственный deduction guide
     *          с выводом N. Прямое создание объекта Command<N> возможно,
     *          но требует явного указания N и источника как указателя:
     *
     *            uint8_t raw[3] = {0x01, 0x02, 0x03};
     *            Command<3> cmd(raw, handler);
     */
    template<uint8_t N>
    class Command: public BaseCommand{
        uint8_t buffer[N];      ///< Собственный буфер кода команды

    public:
        /**
         * @brief   Конструктор команды из указателя на источник.
         * @param   src   Указатель на массив из N байт. Данные копируются
         *                в собственный буфер объекта, поэтому источник
         *                может жить меньше, чем команда.
         * @param   h     Функция-обработчик команды.
         */
        Command(const uint8_t* src, CommandHandlerFunc h, ConfirmPolicy policy):
            BaseCommand(buffer, N, h, policy){
            std::memcpy(buffer, src, N);
        }

        /**
         * @brief   Копирование и перемещение запрещены (в стиле BaseCommand).
         */
        Command(const Command&) = delete;
        Command& operator=(const Command&) = delete;
        Command(Command&&) noexcept = delete;
        Command& operator=(Command&&) noexcept = delete;

        ~Command() = default;
    };

    // -------------------------------------------------------------------------

    /**
     * @brief   Команда, создаваемая из байтового массива.
     * @tparam  N   Длина кода в байтах (выводится через deduction guide
     *              из размера инициализирующего массива).
     * @details Наследник Command<N>: не добавляет полей, только
     *          принимает инициализацию в виде массива uint8_t[N]. 
     * 
     *          Нужен для того, чтобы CTAD корректно выводил N без конфликта
     *          со StringCommand — каждый тип имеет ровно один способ
     *          создания и ровно один deduction guide.
     */
    template<uint8_t N>
    class ByteCommand: public Command<N>{
    public:
        /**
         * @brief   Конструктор из байтового массива.
         * @param   code_data   Массив байт кода команды (длина выводится в N).
         * @param   h           Функция-обработчик команды.
         */
        ByteCommand(const uint8_t (&code_data)[N], CommandHandlerFunc h, ConfirmPolicy policy):
            Command<N>(code_data, h, policy) {}
    };

    /**
     * @brief   Deduction guide для ByteCommand.
     * @details Позволяет писать: ByteCommand cmd({0x01, 0x02}, handler),
     *          с автоматическим выводом ByteCommand<2>.
     */
    template<uint8_t N>
    ByteCommand(const uint8_t (&)[N], CommandHandlerFunc, ConfirmPolicy) -> ByteCommand<N>;

    // -------------------------------------------------------------------------

    /**
     * @brief   Команда, создаваемая из строкового литерала.
     * @tparam  N   Длина кода в байтах (длина литерала без учёта '\0',
     *              выводится через deduction guide).
     * @details Наследник Command<N>: не добавляет полей, только
     *          принимает инициализацию в виде строкового литерала
     *          длиной N+1 (включая завершающий '\0', который отбрасывается).
     *
     *          Отбрасывание '\0' означает, что на стороне ПК команда
     *          должна отправляться без завершающего нуля (data-поле
     *          пакета содержит только значащие символы).
     */
    template<uint8_t N>
    class StringCommand: public Command<N>{
    public:
        /**
         * @brief   Конструктор из строкового литерала.
         * @param   code_data   Литерал длины N+1 (с завершающим '\0').
         *                      В буфер команды копируются первые N байт.
         * @param   h           Функция-обработчик команды.
         */
        StringCommand(const char (&code_data)[N + 1], CommandHandlerFunc h, ConfirmPolicy policy):
            Command<N>(reinterpret_cast<const uint8_t*>(code_data), h, policy) {}
    };

    /**
     * @brief   Deduction guide для StringCommand.
     * @details Позволяет писать: StringCommand cmd("TEXT", handler),
     *          с автоматическим выводом StringCommand<4> (длина без '\0').
     *          Строковый литерал имеет тип const char[N], где N — длина
     *          с учётом '\0'; в целевой тип передаётся N - 1.
     */
    template<uint8_t N>
    StringCommand(const char (&)[N], CommandHandlerFunc, ConfirmPolicy) -> StringCommand<N - 1>;

} // namespace Commands

#endif /*   COMMAND_STRUCTURE_HPP   */
