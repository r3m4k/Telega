/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef DATA_FRAME_HPP
#define DATA_FRAME_HPP

/* Includes ------------------------------------------------------------------*/
#include <cmath>

/* Defines -------------------------------------------------------------------*/

// -----------------------------------------------------------------------------
// Класс для работы с данными, имеющие три координаты
class TriaxialData{

public:
    float x_coord;
    float y_coord;
    float z_coord;

    // ------------------------------
    // Конструкторы и деструктор
    // ------------------------------
    TriaxialData(): x_coord(0), y_coord(0), z_coord(0) {}
    TriaxialData(float _x, float _y, float _z): x_coord(_x), y_coord(_y), z_coord(_z) {}
    TriaxialData(const TriaxialData& triaxial_data): x_coord(triaxial_data.x_coord), y_coord(triaxial_data.y_coord), z_coord(triaxial_data.z_coord) {}

    ~TriaxialData() {}

    // ------------------------------
    // Перегрузка операторов
    // ------------------------------
    
    TriaxialData& operator=(const TriaxialData& other) {
        x_coord = other.x_coord;
        y_coord = other.y_coord;
        z_coord = other.z_coord;
        return *this;
    }

    float& operator[](int index){
        if      (index == 0) return x_coord;
        else if (index == 1) return y_coord;
        else if (index == 2) return z_coord;
        else return x_coord;
    }

    TriaxialData operator+(const TriaxialData& other) const {
        return TriaxialData(x_coord + other.x_coord, y_coord + other.y_coord, z_coord + other.z_coord);
    }

    TriaxialData operator-(const TriaxialData& other) const {
        return TriaxialData(x_coord - other.x_coord, y_coord - other.y_coord, z_coord - other.z_coord);
    }

    TriaxialData operator*(float scalar) const {
        return TriaxialData(x_coord * scalar, y_coord * scalar, z_coord * scalar);
    }

    TriaxialData operator*(const TriaxialData& other) const {
        return TriaxialData(x_coord * other.x_coord, y_coord * other.y_coord, z_coord * other.z_coord);
    }

    TriaxialData operator/(float scalar) const {
        return TriaxialData(x_coord / scalar, y_coord / scalar, z_coord / scalar);
    }

    TriaxialData operator/(const TriaxialData& other) const {
        return TriaxialData(x_coord / other.x_coord, y_coord / other.y_coord, z_coord / other.z_coord);
    }
    // 2. Составные присваивания
    TriaxialData& operator+=(const TriaxialData& other) {
        x_coord += other.x_coord;
        y_coord += other.y_coord;
        z_coord += other.z_coord;
        return *this;
    }

    TriaxialData& operator-=(const TriaxialData& other) {
        x_coord -= other.x_coord;
        y_coord -= other.y_coord;
        z_coord -= other.z_coord;
        return *this;
    }

    TriaxialData& operator*=(float scalar) {
        x_coord *= scalar;
        y_coord *= scalar;
        z_coord *= scalar;
        return *this;
    }

    TriaxialData& operator*=(const TriaxialData& other) {
        x_coord *= other.x_coord;
        y_coord *= other.y_coord;
        z_coord *= other.z_coord;
        return *this;
    }

    TriaxialData& operator/=(float scalar) {
        x_coord /= scalar;
        y_coord /= scalar;
        z_coord /= scalar;
        return *this;
    }

    TriaxialData& operator/=(const TriaxialData& other) {
        x_coord /= other.x_coord;
        y_coord /= other.y_coord;
        z_coord /= other.z_coord;
        return *this;
    }

    TriaxialData calc_sqrt() const{
        return TriaxialData(sqrtf(x_coord), sqrtf(y_coord), sqrtf(z_coord));
    }
};


#endif /*   DATA_FRAME_HPP   */