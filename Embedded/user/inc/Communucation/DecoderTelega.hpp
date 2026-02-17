/**
 * @file    DecoderTelega.hpp
 * @author  Романовский Роман
 * @brief   Декодер сообщений протокола «Телега» для приёма команд по COM-порту.
 * 
 * @note    Для работы необходимы глобальные объекты command_manager и com_port,
 *          определённые в пользовательском коде.
 */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef DECODER_TELEGA
#define DECODER_TELEGA

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

#include "Message.hpp"
#include "CommandProcessing.hpp"
#include "ComPort.hpp"

/* Defines -------------------------------------------------------------------*/

/* Global variables ----------------------------------------------------------*/
extern STM_CppLib::Commands::CommandManager command_manager;
extern STM_CppLib::ComPort::ComPort com_port;

// -----------------------------------------------------------------------------
/**
 * @brief   Декодер сообщений от компьютера (протокол «Телега»).
 * @details Содержит конечный автомат для последовательного разбора байтов
 *          входящего сообщения. Поддерживаемый формат:
 *          - Заголовок: 0x7E, 0xE7
 *          - Формат: 0xFF (в данной версии только этот формат)
 *          - Данные: 2 байта
 *          - Контрольная сумма: младший байт суммы всех предыдущих байтов.
 * 
 *          При успешном приёме вызывается com_port.SendConfirmMessage(),
 *          сообщение передаётся в command_manager.match_message_to_command(),
 *          и если команда найдена, она добавляется в очередь команд.
 *          В противном случае отправляется сообщение об ошибке.
 */
class DecoderTelega{
private:
    /**
     * @brief   Состояния конечного автомата разбора сообщения.
     */
    enum class DecoderStages{
        Want7E,         ///< Ожидание первого байта заголовка (0x7E)
        WantE7,         ///< Ожидание второго байта заголовка (0xE7)
        WantFormat,     ///< Ожидание байта формата (0xFF)
        WantData,       ///< Ожидание заданного количества байт данных
        WantConSum      ///< Ожидание байта контрольной суммы
    };

    STM_CppLib::Message current_message;   ///< Текущее обрабатываемое сообщение

    DecoderStages decode_stage; ///< Текущее состояние автомата
    uint16_t con_sum;           ///< Накопленная сумма байтов (для контроля)
    uint8_t len;                ///< Ожидаемая длина поля данных
    uint8_t dataIndex;          ///< Текущий индекс в поле данных

public:
    /**
     * @brief   Конструктор по умолчанию.
     * @details Инициализирует автомат начальным состоянием Want7E.
     */
    DecoderTelega(): decode_stage(DecoderStages::Want7E) {}

    /**
     * @brief   Деструктор по умолчанию.
     */
    ~DecoderTelega() = default;

    /**
     * @brief   Обработка входящего сообщения.
     * @param   message   Константная ссылка на объект Message (64 байта).
     * @details Сохраняет сообщение во внутренний буфер и последовательно
     *          передаёт каждый байт методу byte_processing().
     */
    void message_processing(const STM_CppLib::Message& message){
        current_message = message;
        for (uint8_t i = 0; i < MessageLength; i++){
            byte_processing(current_message.bytes_msg[i]);
        }
    }

private:
    /**
     * @brief   Обработка одного байта входящего потока.
     * @param   bt   Текущий байт.
     * @details Реализует конечный автомат разбора протокола.
     */
    void byte_processing(uint8_t bt){
        switch (decode_stage)
        {
        case DecoderStages::Want7E:
            if (bt == 0x7e){
                decode_stage = DecoderStages::WantE7;
                con_sum = bt;
                len = 0;
                dataIndex = 0;
            } else    decode_stage = DecoderStages::Want7E;
            break;
            
        case DecoderStages::WantE7:
            if (bt == 0xe7){
                decode_stage = DecoderStages::WantFormat;
                con_sum += bt;
            } else    decode_stage = DecoderStages::Want7E;
            break;

        case DecoderStages::WantFormat:
            if (bt == 0xff){
                decode_stage = DecoderStages::WantData;
                con_sum += bt;
                len = 2;        // Количество байт данных в сообщении с форматом 0xff
            } else    decode_stage = DecoderStages::Want7E;
            break;
            
        case DecoderStages::WantData:
            if (dataIndex < len){
                con_sum += bt;
                dataIndex++;
            }

            if (dataIndex == len){
                decode_stage = DecoderStages::WantConSum; 
            }
            break;
        
        case DecoderStages::WantConSum:
            decode_stage = DecoderStages::Want7E;
            if (uint8_t(con_sum) == bt){
                com_port.SendConfirmMessage();
                const Command* command = command_manager.match_message_to_command(current_message);
                if (command){
                    command_manager.add_command(command);
                }
                else {
                    com_port.SendErrorMessage();
                }
            }
            break;
        }
    }
};

#endif /*   DECODER_TELEGA   */