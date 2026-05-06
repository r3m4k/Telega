/** ****************************************************************************
 * @file    CommandProcessing.hpp
 * @author  Романовский Роман
 * @brief   Модуль обработки команд для встроенной системы.
 *
 * @details Регистрирует поддерживаемые команды и предоставляет менеджер
 *          для их сопоставления и выполнения. Структурные классы команд
 *          (CommandHandler, BaseCommand, Command<N>, ByteCommand<N>,
 *          StringCommand<N>) определены в CommandStructure.hpp.
 *
 *          Поддерживаются два вида команд:
 *          - Срочные (urgent) — выполняются немедленно в контексте декодера
 *            (в IRQ USART). Используются для коротких IRQ-safe действий.
 *          - Отложенные (deferred) — помещаются в очередь и исполняются
 *            в основном цикле программы.
 *
 *          В этом файле определены:
 *          - inline-объекты ByteCommand/StringCommand (поддерживаемые команды);
 *          - CommandManager — контейнер со списками urgent/deferred команд
 *                             и очередью для отложенного исполнения.
 *************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef COMMAND_PROCESSING_HPP
#define COMMAND_PROCESSING_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

#include "main.h"
#include "Messages.hpp"
#include "SpscRingBuffer.hpp"
#include "CommandStructure.hpp"

/* Defines -------------------------------------------------------------------*/

/* Usings --------------------------------------------------------------------*/

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------
namespace Commands{

    // -------------------------------------------------------------------------
    /*!
     * @defgroup SupportedCommands Поддерживаемые команды
     * @brief    Глобальные объекты команд, регистрируемые в CommandManager.
     * @details  Каждая команда — inline-объект ByteCommand<N> или StringCommand<N>
     * @{
     */

    /**
     * @brief   Срочная команда: перезагрузка микроконтроллера.
     */
    inline ByteCommand Restart_Cmd({0xff, 0xff}, restart, ConfirmPolicy::Required);

    /**
     * @brief   Отложенная команда: переход в стадию FooStage.
     */
    inline ByteCommand Set_FooStage_Cmd({0xaa, 0x00}, set_FooStage, ConfirmPolicy::Required);

    /**
     * @brief   Отложенная команда: переход в стадию CalibrationStage.
     */
    inline ByteCommand Set_CalibrationStage_Cmd({0xaa, 0x01}, set_CalibrationStage, ConfirmPolicy::Required);

    /**
     * @brief   Отложенная команда: переход в стадию MeasuringStage.
     */
    inline ByteCommand Set_MeasureStage_Cmd({0xaa, 0x02}, set_MeasureStage, ConfirmPolicy::Required);

    /**
     * @brief   Отложенная команда: переход в стадию StaticStage.
     */
    inline ByteCommand Set_StaticInitStage_Cmd({0xaa, 0x03}, set_StaticStage, ConfirmPolicy::Required);

    /**
     * @brief   Отложенная команда: отправка подтверждения приёма.
     */
    inline StringCommand Send_Confirm_Cmd("CONFIRM", send_confirm_msg, ConfirmPolicy::NotRequired);

    /**
     * @brief   Отложенная команда: отправка ack на handshake.
     */
    inline StringCommand Send_Handshake_Ack_Cmd("HANDSHAKE_REQ", send_handshake_ack, ConfirmPolicy::NotRequired);

    /**
     * @brief   Отложенная команда: отправка ack на heartbeat.
     */
    inline StringCommand Send_Heartbeat_Ack_Cmd("HEARTBEAT_REQ", send_heartbeat_ack, ConfirmPolicy::NotRequired);

    /**
     * @brief   Системная команда: отправка сообщения об ошибке.
     */
    inline StringCommand Send_Error_Cmd("UNKNOWN_COMMAND", send_error_msg, ConfirmPolicy::NotRequired);

    /** @} */ // SupportedCommands

    // -------------------------------------------------------------------------

    /**
     * @brief   Менеджер поддерживаемых команд.
     * @details Хранит два статических списка указателей на BaseCommand:
     *          urgent_commands (исполняются в IRQ-контексте немедленно)
     *          и deferred_commands (помещаются в очередь для исполнения в main).
     *          Также владеет очередью CommandHandler для отложенных команд.
     * @note    При добавлении новой команды (ByteCommand или StringCommand)
     *          не забыть включить её в соответствующий массив ниже.
     */
    class CommandManager{
    public:
        /**
         * @brief   Список срочных команд (исполняются в контексте декодера).
         */
        inline static const BaseCommand* urgent_commands[] = {
            &Restart_Cmd
        };

        /**
         * @brief   Список отложенных команд (помещаются в очередь).
         */
        inline static const BaseCommand* deferred_commands[] = {
            &Set_FooStage_Cmd,
            &Set_MeasureStage_Cmd,
            &Send_Confirm_Cmd,
            &Send_Handshake_Ack_Cmd,
            &Send_Heartbeat_Ack_Cmd
        };

        /**
         * @brief   Очередь отложенных команд для исполнения в main.
         * @details Используется SPSC-очередь: put() вызывается из контекста
         *          USART IRQ (через DecoderTelega::process_command_packet),
         *          get() — из основного цикла main.
         */
        SpscRingBuffer<CommandHandler, 8> command_queue;

        /**
         * @brief   Поиск срочной команды по коду.
         * @param   code   View на байты кода (обычно data-секция пакета).
         * @return  Указатель на найденную BaseCommand или nullptr.
         */
        const BaseCommand* find_urgent(const Messages::Message& code) const {
            for (const BaseCommand* cmd : urgent_commands){
                if (cmd->code == code){
                    return cmd;
                }
            }
            return nullptr;
        }

        /**
         * @brief   Поиск отложенной команды по коду.
         * @param   code   View на байты кода (обычно data-секция пакета).
         * @return  Указатель на найденную BaseCommand или nullptr.
         */
        const BaseCommand* find_deferred(const Messages::Message& code) const {
            for (const BaseCommand* cmd : deferred_commands){
                if (cmd->code == code){
                    return cmd;
                }
            }
            return nullptr;
        }

        /**
         * @brief   Добавление команды в очередь отложенного исполнения.
         * @param   command   Ссылка на команду (только её handler копируется
         *                    в очередь).
         * @return  true, если команда добавлена; false, если очередь заполнена.
         */
        bool add_to_queue(const BaseCommand& command){
            return command_queue.put(command.handler);
        }
    };

} // namespace Commands

#endif /*   COMMAND_PROCESSING_HPP   */