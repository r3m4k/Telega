/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __RING_BUFFER_HPP
#define __RING_BUFFER_HPP

/** ****************************************************************************
 * @file    RingBuffer.hpp
 * @author  Романовский Роман
 * @brief   Простой кольцевой буфер фиксированного размера для single-context
 *
 * @details Шаблонный класс RingBuffer<T, N> реализует FIFO-очередь
 *          на базе кольцевого буфера с операциями put/get за O(1).
 *          Предназначен для использования в одном контексте исполнения
 *          (например, внутри main-цикла без участия прерываний).
 *
 *          Отличия от SpscRingBuffer:
 *          - не thread-safe: put и get не синхронизированы между собой,
 *            поэтому пригоден только для single-context сценариев;
 *          - используется отдельный счётчик элементов item_count,
 *            благодаря чему доступны все N слотов (SPSC-версия
 *            жертвует одним слотом ради отсутствия счётчика);
 *          - N может быть любым (не обязательно степенью двойки), однако
 *            для максимальной производительности рекомендуется выбирать N
 *            как степень двойки (см. раздел "Производительность и выбор N").
 *
 *          Отличия от StaticQueue:
 *          - put() и get() за O(1) (без сдвига массива);
 *          - put() возвращает bool (true при успехе, false при переполнении);
 *          - одна и та же сложность независимо от размера элементов T.
 *
 * @section Производительность и выбор N
 *          Для N, являющегося степенью двойки, переход через границу буфера
 *          выполняется битовой маской (& (N-1)) — одна инструкция AND
 *          на Cortex-M4 при любом уровне оптимизации.
 *          Для N, не являющегося степенью двойки, используется оператор %,
 *          который в debug-сборке (-O0) превращается в вызов
 *          __aeabi_uidivmod (~30+ тактов). На -O2 компилятор обычно делает
 *          strength reduction для константных N-степеней-двойки и без явной
 *          подсказки, но в -O0 этого не происходит — поэтому выбор ветки
 *          производится через if constexpr, что даёт предсказуемый результат
 *          на любом уровне оптимизации.
 *
 *          Итого: для максимальной производительности в debug-сборке
 *          рекомендуется выбирать N как степень двойки (2, 4, 8, 16, ...).
 *
 * @section Ограничения
 *          - Один контекст исполнения: put и get нельзя вызывать
 *            из разных потоков или из main + IRQ;
 *          - N >= 1;
 *          - Тип T должен быть copy constructible и copy assignable.
 *
 * @version 1.0.0
 * @date Апрель 2026
 **************************************************************************** */

/* Includes ------------------------------------------------------------------*/
#include <type_traits>
#include <stdint.h>

/* Defines -------------------------------------------------------------------*/

/* Global variables ----------------------------------------------------------*/

/** ****************************************************************************
 * @class   RingBuffer
 * @brief   Кольцевой буфер фиксированного размера для single-context сценария.
 *
 * @tparam  T   Тип элементов, хранящихся в очереди. Должен быть copy
 *              constructible (используется при возврате из get) и copy
 *              assignable (используется в put: buffer[head] = new_item).
 * @tparam  N   Ёмкость буфера в элементах; должна быть >= 1. Все N слотов
 *              доступны одновременно (в отличие от SpscRingBuffer).
 *
 * @warning Класс не предназначен для использования между прерыванием и
 *          основным циклом. Если нужно передавать данные между контекстами,
 *          используйте SpscRingBuffer.
 **************************************************************************** */
template <typename T, uint32_t N>
class RingBuffer{

    static_assert(N >= 1, "RingBuffer: N must be at least 1");

    static_assert(std::is_copy_constructible_v<T>,
                  "RingBuffer: T must be copy constructible");
    static_assert(std::is_copy_assignable_v<T>,
                  "RingBuffer: T must be copy assignable");

    /// Признак того, что N является степенью двойки — включает fast-path
    /// с битовой маской вместо оператора %.
    static constexpr bool is_power_of_two = (N & (N - 1)) == 0;

    T buffer[N];                ///< Массив-хранилище элементов
    uint32_t head       = 0;    ///< Индекс слота для следующей записи
    uint32_t tail       = 0;    ///< Индекс слота для следующего чтения
    uint32_t item_count = 0;    ///< Текущее число элементов в буфере

    /**
     * @brief   Переход через границу буфера: возврат (idx + 1) mod N.
     * @details Если N — степень двойки, используется битовая маска
     *          (одна инструкция AND на Cortex-M4). Иначе используется
     *          оператор %, который в debug-сборке (-O0) превращается
     *          в вызов __aeabi_uidivmod (~30+ тактов).
     *          Выбор ветки происходит на этапе компиляции через
     *          if constexpr — в машинном коде остаётся только одна ветка.
     */
    static constexpr uint32_t advance(uint32_t idx){
        if constexpr (is_power_of_two){
            return (idx + 1) & (N - 1);
        } else {
            return (idx + 1) % N;
        }
    }

public:

    /**
     * @brief   Конструктор по умолчанию.
     */
    RingBuffer() = default;

    /**
     * @brief   Деструктор по умолчанию.
     */
    ~RingBuffer() = default;

    /**
     * @brief   Копирование и перемещение запрещены.
     * @details Согласуется со стилем остальных контейнеров проекта
     *          (StaticQueue, SpscRingBuffer).
     */
    RingBuffer(const RingBuffer&)            = delete;
    RingBuffer& operator=(const RingBuffer&) = delete;
    RingBuffer(RingBuffer&&)                 = delete;
    RingBuffer& operator=(RingBuffer&&)      = delete;

    /**
     * @brief   Добавление элемента в очередь.
     * @param   new_item   Элемент для помещения в очередь.
     * @return  true, если элемент добавлен; false, если очередь заполнена.
     * @details O(1). Переход через границу буфера — см. advance().
     */
    bool put(const T& new_item){
        if (item_count == N){
            return false;
        }

        buffer[head] = new_item;
        head = advance(head);
        item_count++;
        return true;
    }

    /**
     * @brief   Извлечение элемента из очереди.
     * @return  T   Копия извлечённого элемента.
     *
     * @warning Предварительная проверка is_empty() обязательна. Вызов get()
     *          на пустой очереди — UB на уровне логики (на уровне памяти
     *          вернётся устаревшее содержимое слота buffer[tail]).
     *          Поведение идентично StaticQueue::get() и SpscRingBuffer::get().
     *
     * @details O(1).
     */
    T get(){
        T item = buffer[tail];
        tail = advance(tail);
        item_count--;
        return item;
    }

    /**
     * @brief   Проверка, пуста ли очередь.
     * @return  true, если в очереди нет элементов.
     */
    bool is_empty() const {
        return item_count == 0;
    }

    /**
     * @brief   Проверка, заполнена ли очередь.
     * @return  true, если в очереди ровно N элементов.
     */
    bool is_full() const {
        return item_count == N;
    }
};

#endif /*   __RING_BUFFER_HPP   */
