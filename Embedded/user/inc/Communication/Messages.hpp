/** ***************************************************************************
 * @file    Message.hpp
 * @author  Романовский Роман
 * @brief   Универсальный контейнер сообщения + наследник с собственным буфером.
 *
 * @details Классы для работы с сообщениями произвольной длины:
 *          - Message — базовый контейнер, не владеющий буфером напрямую.
 *            Хранит указатель на внешний буфер и текущий размер значащих
 *            данных. Используется как тип приёма по ссылке (const Message&)
 *            для сообщений любого размера.
 *          - SizedMessage<N> — наследник с собственным буфером фиксированной
 *            длины N байт.
 *************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef MESSAGE_HPP
#define MESSAGE_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>
#include <string.h>

/* Defines -------------------------------------------------------------------*/
/**
 * @def     VCP_BUFFER_SIZE
 * @brief   Размер буфера, используемого в hw_config.c
 */
#define VCP_BUFFER_SIZE      64

/* Global variables ----------------------------------------------------------*/

// -----------------------------------------------------------------------------
namespace Messages{

    /**
     * @brief   Базовый контейнер сообщения, без владения буфером.
     * @details Хранит указатель на внешний буфер и текущий размер значащих
     *          данных. Сам буфер, его обнуление и безопасное копирование
     *          находятся в наследнике (SizedMessage<N>).
     * @note    Время жизни буфера должно перекрывать время жизни объекта.
     *          Класс не выполняет аллокаций.
     */
    class Message{
    public:
        uint8_t* bytes_msg = nullptr;   ///< Указатель на буфер
        uint8_t msg_size = 0;           ///< Фактический размер данных

        /**
         * @brief   Конструктор по умолчанию запрещён — Message без буфера невалиден.
         */
        Message() = delete;

        /**
         * @brief   Конструктор с привязкой к внешнему буферу.
         * @param   buf   Указатель на внешний буфер.
         * @note    Данные не копируются. buf должен оставаться валидным
         *          всё время жизни объекта. msg_size не изменяется (0 по умолчанию).
         */
        explicit Message(uint8_t* buf): bytes_msg(buf) {}

        /**
         * @brief   Конструктор-view с указанием размера значащих данных.
         * @param   buf    Указатель на внешний буфер.
         * @param   size   Количество значащих байт в буфере (msg_size).
         * @note    Данные не копируются. Используется для построения view
         *          на готовый участок (например, data-секцию принятого пакета).
         */
        Message(uint8_t* buf, uint8_t size): bytes_msg(buf), msg_size(size) {}

        /**
         * @brief   Деструктор по умолчанию.
         */
        ~Message() = default;

        /**
         * @brief   Move-операции запрещены (класс не поддерживает move-семантику).
         */
        Message(Message&&) noexcept = delete;
        Message& operator=(Message&&) noexcept = delete;

        /**
         * @brief   Оператор сравнения двух сообщений.
         * @return  true, если размеры и содержимое совпадают.
         */
        bool operator==(const Message& other) const {
            if (msg_size != other.msg_size) return false;
            return memcmp(bytes_msg, other.bytes_msg, msg_size) == 0;
        }

        /**
         * @brief   Лёгкий сброс сообщения – только обнуление размера.
         * @details Содержимое буфера не стирается; следующие записи через
         *          наследника перезапишут нужные ячейки. Безопасно вызывать
         *          в «горячем пути» декодера (нет memset'а в IRQ).
         */
        void reset() {
            msg_size = 0;
        }
    };

    // -------------------------------------------------------------------------

    /**
     * @brief   Сообщение с собственным буфером фиксированной длины.
     * @tparam  N   Ёмкость буфера в байтах.
     * @details Наследник Message, владеющий буфером-массивом. Предоставляет
     *          операции, требующие знания размера буфера (clear, operator=).
     *          Доступ к полям bytes_msg/msg_size — через унаследованные поля базы.
     */
    template<uint8_t N>
    class SizedMessage: public Message{
        uint8_t buffer[N] = {0};   ///< Собственный буфер фиксированного размера

    public:
        /**
         * @brief   Конструктор по умолчанию. Буфер инициализируется нулями.
         */
        SizedMessage(): Message(buffer) {}

        /**
         * @brief   Конструктор, копирующий данные из внешнего буфера.
         * @param   src    Указатель на источник данных.
         * @param   size   Количество байт для копирования (не более N).
         */
        SizedMessage(const uint8_t* src, uint8_t size): Message(buffer) {
            if (size > N) size = N;
            msg_size = size;
            memcpy(buffer, src, size);
        }

        /**
         * @brief   Конструктор копирования.
         */
        SizedMessage(const SizedMessage& other): Message(buffer) {
            msg_size = other.msg_size;
            memcpy(buffer, other.bytes_msg, msg_size);
        }

        /**
         * @brief   Оператор присваивания копированием.
         * @details Защита от переполнения: если other.msg_size превышает N,
         *          копируется не более N байт.
         */
        SizedMessage& operator=(const SizedMessage& other) {
            if (this != &other) {
                uint8_t n = (other.msg_size <= N) ? other.msg_size : N;
                memcpy(buffer, other.bytes_msg, n);
                msg_size = n;
            }
            return *this;
        }

        /**
         * @brief   Move-операции запрещены (класс не поддерживает move-семантику).
         */
        SizedMessage(SizedMessage&&) noexcept = delete;
        SizedMessage& operator=(SizedMessage&&) noexcept = delete;

        /**
         * @brief   Очистка сообщения – заполняет весь буфер нулями.
         */
        void clear() {
            memset(buffer, 0, N);
            msg_size = 0;
        }

        /**
         * @brief   Деструктор по умолчанию.
         */
        ~SizedMessage() = default;
    };

} // namespace Message

#endif /*   MESSAGE_HPP   */