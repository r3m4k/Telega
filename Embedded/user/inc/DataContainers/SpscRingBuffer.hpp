/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __SPSC_RING_BUFFER_HPP
#define __SPSC_RING_BUFFER_HPP

/** ****************************************************************************
 * @file    SpscRingBuffer.hpp
 * @author  Романовский Роман
 * @brief   Lock-free кольцевой буфер для сценария Single Producer / Single Consumer
 *
 * @details Шаблонный класс SpscRingBuffer<T, N> реализует FIFO-очередь
 *          фиксированного размера на базе кольцевого буфера, безопасную
 *          для использования между одним писателем и одним читателем,
 *          работающими в разных контекстах (например, IRQ-обработчик
 *          и основной цикл программы).
 *
 *          Отличия от StaticQueue:
 *          - put() и get() выполняются за O(1) (без сдвига массива);
 *          - корректно работает без отключения прерываний, если put
 *            вызывается из одного контекста, а get — из другого;
 *          - размер N ограничен степенью двойки, что позволяет заменить
 *            операцию взятия остатка по модулю битовой маской.
 *
 * @section Модель синхронизации
 *          Используется классическая SPSC-схема с двумя индексами:
 *          - head — индекс следующего свободного слота для записи,
 *            модифицирует только producer;
 *          - tail — индекс следующего элемента для чтения,
 *            модифицирует только consumer.
 *          Пустая очередь: head == tail.
 *          Заполненная очередь: ((head + 1) & mask) == tail
 *          (один слот остаётся неиспользуемым — плата за возможность
 *          отличить пустую очередь от полной без дополнительного счётчика).
 *
 *          Для корректного порядка операций между записью элемента
 *          и обновлением head (а также чтения элемента и обновления tail)
 *          индексы объявлены как std::atomic<uint32_t> с явным указанием
 *          memory_order_acquire / memory_order_release. На Cortex-M4
 *          acquire/release-операции с обычной SRAM компилируются в обычные
 *          ldr / str плюс компиляторный барьер, без DMB-инструкций,
 *          поэтому оверхед по тактам нулевой. uint32_t выбран как нативный
 *          для ARMv7-M размер — это снимает риск зависания на libatomic
 *          для 1-байтовых atomic на -O0.
 *
 * @section Ограничения
 *          - Только один поток/контекст может вызывать put();
 *          - Только один поток/контекст может вызывать get();
 *          - N должен быть степенью двойки и не меньше 2;
 *          - Тип T должен иметь конструктор копирования и оператор
 *            присваивания копированием. Корректность публикации слота
 *            обеспечивается release/acquire-барьерами на индексах head/tail,
 *            а не простотой operator= самого T — поэтому пользовательский
 *            copy assignment безопасен.
 *
 * @version 1.0.0
 * @date Апрель 2026
 **************************************************************************** */

/* Includes ------------------------------------------------------------------*/
#include <atomic>
#include <type_traits>
#include <stdint.h>

/* Defines -------------------------------------------------------------------*/

/* Global variables ----------------------------------------------------------*/

/** ****************************************************************************
 * @class   SpscRingBuffer
 * @brief   Lock-free кольцевой буфер фиксированного размера для SPSC-сценария.
 *
 * @tparam  T   Тип элементов, хранящихся в очереди. Должен быть копируемым
 *              (copy constructible и copy assignable). Дополнительных требований
 *              нет: безопасность публикации обеспечивается барьерами на head/tail.
 * @tparam  N   Размер буфера в элементах. Должен быть степенью двойки,
 *              не меньше 2. Фактически доступно N - 1 слотов (один слот
 *              зарезервирован для различения состояний "пусто" и "полно").
 *
 * @warning Безопасность обеспечивается только если put() и get() вызываются
 *          из разных контекстов, причём каждый из методов — только из своего.
 *          Два одновременных put() или два одновременных get() из разных
 *          контекстов приведут к повреждению состояния.
 **************************************************************************** */
template <typename T, uint32_t N>
class SpscRingBuffer{

    // N должен быть степенью двойки — тогда mask = N - 1 корректно
    // выполняет роль оператора взятия остатка по модулю N для любых индексов.
    static_assert(N >= 2, "SpscRingBuffer: N must be at least 2");
    static_assert((N & (N - 1)) == 0,
                  "SpscRingBuffer: N must be a power of two");

    // Требования к типу элементов.
    // is_copy_assignable используется в put (buffer[h] = new_item);
    // is_copy_constructible используется в get (возврат T по значению).
    //
    // Не требуем trivially_copyable: в проекте есть типы с user-provided
    // copy-методами (например, CommandHandler) и = delete для move.
    // Для корректности SPSC важно лишь, чтобы запись слота буфера
    // не наблюдалась consumer'ом в промежуточном состоянии. Это
    // гарантировано не свойством типа, а тем, что consumer всегда читает
    // head с acquire-семантикой — и видит либо предыдущее значение слота
    // (до инкремента head), либо полностью записанное. Промежуточные
    // состояния operator= невидимы из-за release/acquire-барьеров.
    static_assert(std::is_copy_constructible_v<T>,
                  "SpscRingBuffer: T must be copy constructible");
    static_assert(std::is_copy_assignable_v<T>,
                  "SpscRingBuffer: T must be copy assignable");

    static constexpr uint32_t mask = N - 1;  ///< Маска для перехода через границу буфера

    T buffer[N];                             ///< Массив-хранилище элементов
    std::atomic<uint32_t> head{0};           ///< Индекс следующего слота для записи (producer)
    std::atomic<uint32_t> tail{0};           ///< Индекс следующего элемента для чтения (consumer)

public:

    /**
     * @brief   Конструктор по умолчанию.
     */
    SpscRingBuffer() = default;

    /**
     * @brief   Деструктор по умолчанию.
     */
    ~SpscRingBuffer() = default;

    /**
     * @brief   Копирование и перемещение запрещены.
     * @details Атомарные поля head/tail не копируются (по стандарту),
     *          а копирование всего буфера между двумя экземплярами
     *          в SPSC-сценарии не имеет смысла.
     */
    SpscRingBuffer(const SpscRingBuffer&) = delete;
    SpscRingBuffer& operator=(const SpscRingBuffer&) = delete;
    SpscRingBuffer(SpscRingBuffer&&) noexcept = delete;
    SpscRingBuffer& operator=(SpscRingBuffer&&) noexcept = delete;

    /**
     * @brief   Добавление элемента в очередь (producer).
     * @param   new_item   Элемент для помещения в очередь.
     * @return  true, если элемент добавлен; false, если очередь полна.
     * @details Вызывается только из контекста producer. Если очередь полна,
     *          элемент не добавляется. Возврат bool позволяет вызывающему
     *          отреагировать на переполнение (например, зарегистрировать
     *          ошибку или отправить уведомление в обратный канал).
     *
     *          Порядок операций:
     *          1. Загрузить текущий head (relaxed — модифицирует только
     *             producer, никто другой не пишет).
     *          2. Загрузить tail с memory_order_acquire, чтобы увидеть
     *             актуальное значение после возможного get() в consumer
     *             (и вместе с ним все изменения, опубликованные до этого).
     *          3. Проверить, есть ли свободный слот.
     *          4. Записать элемент в buffer[head].
     *          5. Опубликовать новый head с memory_order_release —
     *             consumer, увидев обновлённый head, гарантированно
     *             увидит и записанный элемент.
     */
    bool put(const T& new_item){
        const uint32_t head_local = head.load(std::memory_order_relaxed);
        const uint32_t next_head  = (head_local + 1) & mask;

        // Очередь полна, если следующий head догнал tail
        if (next_head == tail.load(std::memory_order_acquire)){
            return false;
        }

        buffer[head_local] = new_item;
        head.store(next_head, std::memory_order_release);
        return true;
    }

    /**
     * @brief   Извлечение элемента из очереди (consumer).
     * @return  T   Копия извлечённого элемента.
     *
     * @warning Предварительная проверка is_empty() обязательна. Вызов get()
     *          на пустой очереди — UB на уровне логики (на уровне памяти
     *          вернётся устаревшее содержимое слота buffer[tail]).
     *          Поведение идентично StaticQueue::get().
     *
     * @details Вызывается только из контекста consumer.
     *
     *          Порядок операций:
     *          1. Загрузить текущий tail (relaxed — модифицирует только
     *             consumer, никто другой не пишет).
     *          2. Скопировать элемент из buffer[tail].
     *          3. Опубликовать новый tail с memory_order_release —
     *             producer, увидев обновлённый tail, узнает об
     *             освободившемся слоте только после того, как consumer
     *             фактически скопирует элемент наружу.
     *
     *          acquire-чтение head здесь не требуется: предполагается,
     *          что вызывающий уже сделал is_empty() (которое делает
     *          acquire) и тем самым убедился в наличии элемента.
     */
    T get(){
        const uint32_t tail_local = tail.load(std::memory_order_relaxed);
        T item = buffer[tail_local];
        tail.store((tail_local + 1) & mask, std::memory_order_release);
        return item;
    }

    /**
     * @brief   Проверка, пуста ли очередь.
     * @return  true, если head == tail.
     * @details Безопасно вызывается из любого контекста. В consumer-контексте
     *          результат true гарантирует, что на момент вызова очередь пуста.
     *          В producer-контексте результат false гарантирует, что в очереди
     *          есть как минимум один элемент (consumer мог их забрать только
     *          полностью, не вставляя промежуточные состояния).
     */
    bool is_empty() const {
        return head.load(std::memory_order_acquire) ==
               tail.load(std::memory_order_acquire);
    }

    /**
     * @brief   Проверка, заполнена ли очередь.
     * @return  true, если ((head + 1) & mask) == tail.
     * @details Безопасно вызывается из любого контекста. Фактическая ёмкость
     *          очереди — N - 1 элемент (один слот всегда остаётся пустым
     *          для различения пустой и полной очереди).
     */
    bool is_full() const {
        const uint32_t next_head =
            (head.load(std::memory_order_acquire) + 1) & mask;
        return next_head == tail.load(std::memory_order_acquire);
    }
};

#endif /*   __SPSC_RING_BUFFER_HPP   */
