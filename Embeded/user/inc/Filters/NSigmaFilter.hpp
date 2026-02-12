/** ****************************************************************************
 * @file    NSigmaFilter.hpp
 * @brief   Фильтр N-сигма для TriaxialData
 * @author  Романовский Роман
 * @date    Февраль 2026
 * 
 * @details Реализует двухуровневую фильтрацию выбросов на основе правила N*sigma.
 *          Первый уровень – обработка пакетов фиксированной длины, отбрасывание
 *          отсчётов, выходящих за пределы N*sigma от среднего значения пакета.
 *          Второй уровень – накопление очищенных значений из нескольких пакетов
 *          и вычисление итогового среднего.
 **************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef N_SIGMA_FILTER_HPP
#define N_SIGMA_FILTER_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

#include "TriaxialData.hpp"
#include "Stats.hpp"

/* Defines -------------------------------------------------------------------*/

/* Global variables ----------------------------------------------------------*/

/** ****************************************************************************
 * @brief Класс для реализации фильтра "N сигма" для 3-х компонентных данных
 * 
 * @tparam N              Коэффициент N для правила N*sigma (порог отбраковки)
 * @tparam FilterFrameNum Количество кадров, накапливаемых для итогового результата
 * @tparam FilterFrameLen Длина одного кадра (количество отсчётов в пакете)
 * 
 * @details Фильтр работает с потоком трёхосных измерений.
 *          Кадры заполняются последовательно, после заполнения кадра
 *          вычисляются его среднее и дисперсия (через Stats), затем отсчёты,
 *          отклоняющиеся от среднего более чем на N * σ, отбрасываются.
 *          Прошедшие отсчёты используются для обновления скользящего среднего
 *          (алгоритм Уэлфорда для среднего). После накопления FilterFrameNum
 *          кадров итоговое среднее становится доступным.
 **************************************************************************** */

template<float N, uint8_t FilterFrameNum, uint8_t FilterFrameLen>
class NSigmaFilter{
    static_assert(FilterFrameLen > 0, "Frame length must be positive");
    static_assert(FilterFrameNum > 0, "Number of frames must be positive");

private:
    TriaxialData array[FilterFrameLen];          ///< Буфер текущего кадра
    Stats<TriaxialData, FilterFrameLen> stats;   ///< Объект для статистики кадра
    
    bool data_ready_flag;      ///< Флаг готовности отфильтрованных данных
    uint8_t frame_index;       ///< Счётчик обработанных кадров
    uint8_t data_index;        ///< Индекс заполнения буфера кадра
    
    TriaxialData filtered_value;    ///< Накопленное отфильтрованное среднее (по осям)
    TriaxialData counter;           ///< Счётчик прошедших фильтр отсчётов (по осям)

public:
    /**
     * @brief Конструктор по умолчанию
     * 
     * Инициализирует stats переданным массивом, сбрасывает счётчики,
     * обнуляет filtered_value и counter.
     */
    NSigmaFilter(): 
        stats(array), data_ready_flag(false), frame_index(0),
        data_index(0), filtered_value(), counter() {}

    /**
     * @brief Проверка готовности отфильтрованного значения
     * @return true  – данные готовы (можно вызывать get_filtered_data());
     *         false – данные ещё накапливаются.
     */
    bool is_data_filtered() const{
        return data_ready_flag;
    }

    /**
     * @brief Получить отфильтрованное значение
     * @return Объект TriaxialData с итоговым средним по каждой оси
     * @note После вызова этого метода фильтр переходит в состояние «данные готовы».
     *       Для нового цикла фильтрации необходимо вызвать reset().
     */
    TriaxialData get_filtered_data(){
        return filtered_value;
    }

    /**
     * @brief Сброс состояния фильтра для нового цикла обработки
     * 
     * Очищает флаги готовности, обнуляет счётчики кадров и индексы,
     * сбрасывает накопленное среднее и счётчик отсчётов, а также
     * внутреннюю статистику Stats.
     */
    void reset(){
        data_ready_flag = false;
        data_index = 0;
        frame_index = 0;
        filtered_value = TriaxialData(); 
        counter = TriaxialData();
        stats.reset();   
    }

    /**
     * @brief Добавление нового значения в фильтр
     * @param[in] val Очередное трёхосное измерение
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
    bool append_value(const TriaxialData& val) {
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
     * @brief Фильтрация одного полного кадра данных
     * 
     * @details Вычисляет среднее и дисперсию кадра (через Stats), затем
     *          СКО = sqrt(дисперсия). Для каждой координаты каждого отсчёта
     *          проверяется условие |x - mean| <= N * sigma. Если условие выполняется,
     *          отсчёт считается «чистым» и используется для обновления
     *          накопленного среднего по алгоритму Уэлфорда:
     *          filtered_value[coord] += (value - filtered_value[coord]) / (++counter[coord]).
     *          После обработки кадра внутренняя статистика сбрасывается (stats.reset()).
     */
    void frame_filtering(){
        // Получим статистические значения
        TriaxialData mean = stats.get_mean();
        TriaxialData variance = stats.get_variance();
        TriaxialData sigma = variance.calc_sqrt();

        // Отфильтруем данные по правилу N*sigma
        for (uint8_t coord = 0; coord < 3; coord++){
            for(uint8_t i = 0; i < FilterFrameLen; i++){
                if ( (array[i][coord] >= (mean[coord] - N * sigma[coord])) && 
                     (array[i][coord] <= (mean[coord] + N * sigma[coord])) ){
                    filtered_value[coord] += (array[i][coord] - filtered_value[coord]) / (++counter[coord]);
                }
            }
        }

        // Сбросим статистику
        stats.reset();
    }
};

#endif /*   N_SIGMA_FILTER_HPP   */