/** ****************************************************************************
 * @file    Stats.hpp
 * @brief   Шаблонный класс для вычисления статистических величин массива данных
 * @author  Романовский Роман
 * @date    Февраль 2026
 **************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef STATS_HPP
#define STATS_HPP

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

/* Defines -------------------------------------------------------------------*/

/* Global variables ----------------------------------------------------------*/

/** ****************************************************************************
 * @brief   Шаблонный класс для статистических вычислений
 * @tparam  T Тип элементов массива
 * @tparam  N Размер массива данных
 * 
 * @class   Stats
 * @brief   Вычисляет статистические характеристики массива
 * 
 * @details Класс предоставляет ленивое вычисление статистических характеристик
 *          массива данных фиксированного размера. Используется алгоритм Уэлфорда
 *          для численно устойчивого вычисления среднего и дисперсии за один проход.
 * 
 * @warning При использовании целочисленных типов возможно переполнение при вычислениях.
 *          Рекомендуется использовать типы с плавающей точкой для точных результатов.
 **************************************************************************** */
template<typename T, uint32_t N>
class Stats{
    static_assert(N > 0, "Stats: N must be greater than 0");

private:
    // Указатель на массив данных 
    T* data_ptr;

    // Флаги выполненных рассчётов
    bool is_mean_counted = false;
    bool is_variance_counted = false;

    // Рассчитываемые величины
    T mean_value;
    T variance;
    
public:
    /**
     * @brief Удаленный конструктор по умолчанию
     * @details Класс требует инициализации с указателем на данные
     */
    Stats() = delete;
    
    /**
     * @brief Конструктор класса Stats
     * @param[in] _data_ptr Указатель на массив данных для анализа
     * 
     * @pre     _data_ptr != nullptr
     * @pre     Массив должен содержать не менее N элементов
     */
    Stats(T* _data_ptr): data_ptr(_data_ptr), mean_value(), variance() {}
    
    /**
     * @brief Получить среднее значение массива
     * @return Среднее арифметическое элементов массива
     */
    T get_mean(){
        if(!is_mean_counted){
            count_mean_and_variance();
        }
        return mean_value;
    }
    
    /**
     * @brief Получить дисперсию массива
     * @return Дисперсия элементов массива
     */
    T get_variance(){
        if(!is_variance_counted){
            count_mean_and_variance();
        }
        return variance;
    }

    /**
     * @brief Сбросить кэш вычисленных значений
     */
    void reset(){
        is_mean_counted = false;
        is_variance_counted = false;
    }

private:
    /**
     * @brief Вычисление среднего значения и дисперсии
     */
    void count_mean_and_variance(){
        T mean = T();
        T M2 = T();  // Сумма квадратов отклонений
        
        for (uint32_t i = 0; i < N; i++){
            T delta = data_ptr[i] - mean;
            mean += delta / (i + 1);
            T delta2 = data_ptr[i] - mean;
            M2 += delta * delta2;
        }
        
        mean_value = mean;
        variance = M2 / N;
        
        is_mean_counted = true;
        is_variance_counted = true;
    }

};

#endif /*   STATS_HPP   */