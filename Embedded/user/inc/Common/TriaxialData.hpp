/** *************************************************************************** 
 * @file    TriaxialData.hpp
 * @author  Романовский Роман
 * @brief   Класс для представления трёхосных данных и арифметических операций
 * @details Содержит класс TriaxialData, хранящий три координаты типа float,
 *          и перегруженные операторы для векторной (поэлементной) арифметики,
 *          доступа по индексу и вычисления квадратного корня.
 *************************************************************************** */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef TRIAXIAL_DATA_HPP
#define TRIAXIAL_DATA_HPP

/* Includes ------------------------------------------------------------------*/
#include <cmath>

/* Defines -------------------------------------------------------------------*/

// -----------------------------------------------------------------------------
/**
 * @brief Класс для работы с трёхосными данными (x, y, z)
 * @details Предоставляет открытые поля x_coord, y_coord, z_coord,
 *          конструкторы, деструктор, операторы доступа по индексу,
 *          арифметические операторы (+, -, *, /) как с другим объектом,
 *          так и со скаляром, составные присваивания, а также метод
 *          вычисления квадратного корня из каждой координаты.
 */
class TriaxialData{

public:
    float x_coord;      /**< Координата X */
    float y_coord;      /**< Координата Y */
    float z_coord;      /**< Координата Z */

    // ------------------------------
    // Конструкторы и деструктор
    // ------------------------------
    /** 
     * @brief Конструктор по умолчанию, инициализирует координаты нулями 
     */
    TriaxialData(): x_coord(0), y_coord(0), z_coord(0) {}

    /** 
     * @brief Конструктор с заданным общим значением для координат
     * @param val Общее значение координат
     */
    TriaxialData(float val): x_coord(val), y_coord(val), z_coord(val) {}
    
    /** 
     * @brief Конструктор с заданными координатами
     * @param _x Значение координаты X
     * @param _y Значение координаты Y
     * @param _z Значение координаты Z
     */
    TriaxialData(float _x, float _y, float _z): x_coord(_x), y_coord(_y), z_coord(_z) {}
    
    /**
     * @brief Конструктор копирования 
     */
    TriaxialData(const TriaxialData& triaxial_data): 
        x_coord(triaxial_data.x_coord), y_coord(triaxial_data.y_coord), z_coord(triaxial_data.z_coord) {}
    
    /**
     * @brief Деструктор по умолчанию 
     */
    ~TriaxialData() = default;

    // ------------------------------
    // Перегрузка операторов
    // ------------------------------
    
    /** 
     * @brief Оператор присваивания 
     */
    TriaxialData& operator=(const TriaxialData& other) {
        x_coord = other.x_coord;
        y_coord = other.y_coord;
        z_coord = other.z_coord;
        return *this;
    }

    /** 
     * @brief   Неконстантный оператор доступа по индексу
     * @param   index Индекс (0 – x, 1 – y, 2 – z)
     * @return  Неконстантная ссылка на соответствующую координату
     * @note    При некорректном индексе возвращается ссылка на x_coord
     */
    float& operator[](int index) {
        if      (index == 0) return x_coord;
        else if (index == 1) return y_coord;
        else if (index == 2) return z_coord;
        else return x_coord;
    }

    /** 
     * @brief   Константный оператор доступа по индексу
     * @param   index Индекс (0 – x, 1 – y, 2 – z)
     * @return  Константная ссылка на соответствующую координату
     * @note    При некорректном индексе возвращается ссылка на x_coord
     */
    const float& operator[](int index) const {
        if      (index == 0) return x_coord;
        else if (index == 1) return y_coord;
        else if (index == 2) return z_coord;
        else return x_coord;
    }

    /** 
     * @brief Поэлементное сложение двух векторов 
     */
    TriaxialData operator+(const TriaxialData& other) const {
        return TriaxialData(x_coord + other.x_coord, y_coord + other.y_coord, z_coord + other.z_coord);
    }

    /**
     * @brief Поэлементное вычитание двух векторов 
     */
    TriaxialData operator-(const TriaxialData& other) const {
        return TriaxialData(x_coord - other.x_coord, y_coord - other.y_coord, z_coord - other.z_coord);
    }

    /**
     * @brief Умножение вектора на скаляр 
     */
    TriaxialData operator*(float scalar) const {
        return TriaxialData(x_coord * scalar, y_coord * scalar, z_coord * scalar);
    }

    /** 
     * @brief Поэлементное умножение двух векторов 
     */
    TriaxialData operator*(const TriaxialData& other) const {
        return TriaxialData(x_coord * other.x_coord, y_coord * other.y_coord, z_coord * other.z_coord);
    }

    /** 
     * @brief   Деление вектора на скаляр 
     * @warning Отсутствует проверка деления на ноль
     */
    TriaxialData operator/(float scalar) const {
        return TriaxialData(x_coord / scalar, y_coord / scalar, z_coord / scalar);
    }

    /**
     * @brief Поэлементное деление двух векторов 
     */
    TriaxialData operator/(const TriaxialData& other) const {
        return TriaxialData(x_coord / other.x_coord, y_coord / other.y_coord, z_coord / other.z_coord);
    }

    /**
     * @brief Составное сложение с присваиванием 
     */
    TriaxialData& operator+=(const TriaxialData& other) {
        x_coord += other.x_coord;
        y_coord += other.y_coord;
        z_coord += other.z_coord;
        return *this;
    }

    /**
     * @brief Составное вычитание с присваиванием 
     */
    TriaxialData& operator-=(const TriaxialData& other) {
        x_coord -= other.x_coord;
        y_coord -= other.y_coord;
        z_coord -= other.z_coord;
        return *this;
    }

    /**
     * @brief Составное умножение на скаляр 
     */
    TriaxialData& operator*=(float scalar) {
        x_coord *= scalar;
        y_coord *= scalar;
        z_coord *= scalar;
        return *this;
    }

    /**
     * @brief Составное поэлементное умножение 
     */
    TriaxialData& operator*=(const TriaxialData& other) {
        x_coord *= other.x_coord;
        y_coord *= other.y_coord;
        z_coord *= other.z_coord;
        return *this;
    }

    /**
     * @brief   Составное деление на скаляр 
     * @warning Отсутствует проверка деления на ноль
     */
    TriaxialData& operator/=(float scalar) {
        x_coord /= scalar;
        y_coord /= scalar;
        z_coord /= scalar;
        return *this;
    }

    /**
     * @brief   Составное поэлементное деление
     * @warning Отсутствует проверка деления на ноль 
     */
    TriaxialData& operator/=(const TriaxialData& other) {
        x_coord /= other.x_coord;
        y_coord /= other.y_coord;
        z_coord /= other.z_coord;
        return *this;
    }

    /**
     * @brief Возвращает новый вектор с квадратными корнями из координат 
     */
    TriaxialData calc_sqrt() const{
        return TriaxialData(std::sqrt(x_coord), std::sqrt(y_coord), std::sqrt(z_coord));
    }
    
    /**
     * @brief   Проверка на равенство двух векторов
     * @param   other   Вектор для сравнения
     * @return  true, если векторы равны (все координаты совпадают)
     */
    bool operator==(const TriaxialData& other) const {
        return x_coord == other.x_coord &&
            y_coord == other.y_coord &&
            z_coord == other.z_coord;
    }
    
    /**
     * @brief   Проверка на неравенство двух векторов
     * @param   other   Вектор для сравнения
     * @return  true, если векторы не равны (хотя бы одна координата отличается)
     */
    bool operator!=(const TriaxialData& other) const { return !(*this == other); }
};

#endif /*   TRIAXIAL_DATA_HPP   */