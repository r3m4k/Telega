/** ****************************************************************************
 * @file    NSigmaFilter.hpp
 * @brief   Шаблонный фильтр N-сигма для различных типов данных
 * @author  Романовский Роман
 * @date    Февраль 2026
 * 
 * @details Реализует двухуровневую фильтрацию выбросов на основе правила N*sigma.
 *          Тип обрабатываемых данных задаётся шаблонным параметром T. Поддерживаются:
 *          - TriaxialData (трёхосные векторы) – фильтрация покоординатно;
 *          - типы с плавающей точкой (float, double) – скалярная фильтрация.
 *          Другие типы (целочисленные, пользовательские) не допускаются.
 *          
 *          Параметр N (коэффициент сигма) передаётся в конструкторе, что позволяет
 *          изменять его во время выполнения для разных экземпляров фильтра.
 *          
 *          Первый уровень – обработка пакетов фиксированной длины, отбрасывание
 *          отсчётов, выходящих за пределы N*sigma от среднего значения пакета.
 *          Второй уровень – накопление очищенных значений из нескольких пакетов
 *          и вычисление итогового среднего (по алгоритму Уэлфорда).
 **************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef N_SIGMA_FILTER_HPP
#define N_SIGMA_FILTER_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>
#include <type_traits>
#include <cmath>

#include "TriaxialData.hpp"
#include "Stats.hpp"

/* Defines -------------------------------------------------------------------*/

/* Global variables ----------------------------------------------------------*/

/** ****************************************************************************
 * @brief   Шаблонный класс фильтра N-сигма.
 * 
 * @tparam T                Тип обрабатываемых данных.
 *                          Должен поддерживать операции, необходимые для работы Stats<T>.
 * @tparam FilterFrameNum   Количество кадров, накапливаемых для итогового результата.
 * @tparam FilterFrameLen   Длина одного кадра (количество отсчётов в пакете).
 * 
 * @details Фильтр работает с потоком данных типа T. Кадры заполняются последовательно,
 *          после заполнения кадра вычисляются его среднее и дисперсия (через Stats),
 *          затем отсчёты, отклоняющиеся от среднего более чем на N * sigma, отбрасываются.
 *          Прошедшие отсчёты используются для обновления скользящего среднего.
 *          Параметр N задаётся в конструкторе и может различаться для разных объектов.
 **************************************************************************** */
template<typename T, uint8_t FilterFrameNum, uint8_t FilterFrameLen>
class NSigmaFilter{
    static_assert(FilterFrameLen > 0, "Frame length must be positive");
    static_assert(FilterFrameNum > 0, "Number of frames must be positive");

private:
    const float N;                      ///< Коэффициент N для правила N*sigma (задаётся в конструкторе)
    T array[FilterFrameLen];            ///< Буфер текущего кадра
    Stats<T, FilterFrameLen> stats;     ///< Объект для статистики кадра
    
    bool data_ready_flag;       ///< Флаг готовности отфильтрованных данных
    uint8_t frame_index;        ///< Счётчик обработанных кадров
    uint8_t data_index;         ///< Индекс заполнения буфера кадра
    
    T filtered_value;       ///< Накопленное отфильтрованное среднее (тип T)
    T counter;              ///< Счётчик прошедших фильтр отсчётов (для каждой координаты/скалярно)

public:
    /**
     * @brief Конструктор по умолчанию запрещён (требуется задать N).
     */
    NSigmaFilter() = delete;

    /**
     * @brief Конструктор с параметром N.
     * @param n   Коэффициент N для правила N*sigma.
     * 
     * Инициализирует N, stats ссылкой на внутренний массив, сбрасывает счётчики,
     * обнуляет filtered_value и counter (через value-инициализацию T).
     */
    NSigmaFilter(float n) : 
        N(n), stats(array), data_ready_flag(false), frame_index(0),
        data_index(0), filtered_value(), counter() {}

    /**
     * @brief Проверка готовности отфильтрованного значения.
     * @return true  – данные готовы (можно вызывать get_filtered_data());
     *         false – данные ещё накапливаются.
     */
    bool is_data_filtered() const{
        return data_ready_flag;
    }

    /**
     * @brief Получить отфильтрованное значение.
     * @return Объект типа T с итоговым средним (покоординатно для TriaxialData,
     *         скалярное значение для плавающих типов).
     * @note После вызова этого метода фильтр переходит в состояние «данные готовы».
     *       Для нового цикла фильтрации необходимо вызвать reset().
     */
    T get_filtered_data(){
        return filtered_value;
    }

    /**
     * @brief Сброс состояния фильтра для нового цикла обработки.
     * 
     * Очищает флаги готовности, обнуляет счётчики кадров и индексы,
     * сбрасывает накопленное среднее и счётчик отсчётов, а также
     * внутреннюю статистику Stats.
     */
    void reset(){
        data_ready_flag = false;
        data_index = 0;
        frame_index = 0;
        filtered_value = T(); 
        counter = T();
        stats.reset();   
    }

    /**
     * @brief Добавление нового значения в фильтр.
     * @param[in] val Очередное измерение типа T.
     * @return true  – значение принято, фильтрация продолжается;
     *         false – данные уже отфильтрованы, значение не добавлено.
     * 
     * @details Если буфер текущего кадра не заполнен, значение сохраняется.
     *          При заполнении кадра вызывается frame_filtering() для его обработки,
     *          счётчик кадров увеличивается, буфер очищается, и текущее значение
     *          становится первым в новом кадре.
     *          Когда количество обработанных кадров достигает FilterFrameNum,
     *          устанавливается флаг готовности.
     */
    bool append_value(const T& val) {
        // Если фильтр уже накопил достаточное количество кадров и результат готов,
        // дальнейшее добавление данных блокируется до вызова reset()
        if (data_ready_flag) {
            return false;
        }

        // Пока текущий кадр не заполнен – просто сохраняем измерение
        if (data_index < FilterFrameLen) {
            array[data_index++] = val;
        }
        // Кадр заполнен – выполняем фильтрацию, увеличиваем счётчик обработанных кадров
        // и помещаем поступившее значение как первый элемент следующего кадра
        else {
            frame_filtering();
            frame_index++;
            data_index = 0;
            array[data_index++] = val;
        }

        // Достигнуто требуемое количество кадров – помечаем, что отфильтрованные данные готовы
        if (frame_index == FilterFrameNum) {
            data_ready_flag = true;
        }

        return true;    // значение успешно добавлено в обработку
    }

private:
    /**
     * @brief Фильтрация одного полного кадра данных.
     * 
     * @details Метод специализирован для двух категорий типов:
     *          - TriaxialData: вычисляет среднее, дисперсию и СКО (через calc_sqrt()),
     *            затем покоординатно проверяет условие N*sigma и обновляет скользящее среднее.
     *          - Плавающие типы (float, double): использует std::sqrt для СКО,
     *            выполняет скалярную проверку и обновление.
     *          Для любых других типов компиляция прерывается статическим утверждением.
     *          После обработки кадра статистика сбрасывается (stats.reset()).
     */
    void frame_filtering() {
        if constexpr (std::is_same_v<T, TriaxialData>) {
            // Специализация для TriaxialData
            TriaxialData mean = stats.get_mean();
            TriaxialData variance = stats.get_variance();
            TriaxialData sigma = variance.calc_sqrt();

            for (uint8_t coord = 0; coord < 3; ++coord) {
                for (uint8_t i = 0; i < FilterFrameLen; ++i) {
                    if ( (array[i][coord] >= mean[coord] - N * sigma[coord]) &&
                         (array[i][coord] <= mean[coord] + N * sigma[coord]) ) {
                        filtered_value[coord] += (array[i][coord] - filtered_value[coord]) / (++counter[coord]);
                    }
                }
            }
        }
        else if constexpr (std::is_floating_point_v<T>) {
            // Обобщённая ветка для типов с плавающей точкой (float, double)
            T mean = stats.get_mean();
            T variance = stats.get_variance();
            T sigma = std::sqrt(variance);

            for (uint8_t i = 0; i < FilterFrameLen; ++i) {
                if ((array[i] >= mean - N * sigma) && (array[i] <= mean + N * sigma)) {
                    filtered_value += (array[i] - filtered_value) / (++counter);
                }
            }
        }
        else {
            // Запрещаем использование целочисленных и других неподдерживаемых типов
            static_assert(sizeof(T) == 0, "NSigmaFilter: type must be TriaxialData or floating point");
        }

        // Сбросим статистику
        stats.reset();
    }
};

#endif /*   N_SIGMA_FILTER_HPP   */