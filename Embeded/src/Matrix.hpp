#ifndef __MATRIX_HPP
#define __MATRIX_HPP

#include "Data.hpp"

class Matrix{
    float matrix[9] = {0.0f};
    float matrix_Buffer[9] = {0.0f};
    short matrix_Index = 0;

public:

    // ########################################################################
    // Перегрузка операторов

    // Умножение матриц с сохранением информации в matrix_Buffer первой матрицы
    void operator*(Matrix& mult_matrix){
        matrix_Buffer[0] = matrix[0] * mult_matrix.matrix[0] + matrix[1] * mult_matrix.matrix[3] + matrix[2] * mult_matrix.matrix[6];
        matrix_Buffer[1] = matrix[0] * mult_matrix.matrix[1] + matrix[1] * mult_matrix.matrix[4] + matrix[2] * mult_matrix.matrix[7];
        matrix_Buffer[2] = matrix[0] * mult_matrix.matrix[2] + matrix[1] * mult_matrix.matrix[5] + matrix[2] * mult_matrix.matrix[8];
        
        matrix_Buffer[3] = matrix[3] * mult_matrix.matrix[0] + matrix[4] * mult_matrix.matrix[3] + matrix[5] * mult_matrix.matrix[6];
        matrix_Buffer[4] = matrix[3] * mult_matrix.matrix[1] + matrix[4] * mult_matrix.matrix[4] + matrix[5] * mult_matrix.matrix[7];
        matrix_Buffer[5] = matrix[3] * mult_matrix.matrix[2] + matrix[4] * mult_matrix.matrix[5] + matrix[5] * mult_matrix.matrix[8];

        matrix_Buffer[6] = matrix[6] * mult_matrix.matrix[0] + matrix[7] * mult_matrix.matrix[3] + matrix[8] * mult_matrix.matrix[6];
        matrix_Buffer[7] = matrix[6] * mult_matrix.matrix[1] + matrix[7] * mult_matrix.matrix[4] + matrix[8] * mult_matrix.matrix[7];
        matrix_Buffer[8] = matrix[6] * mult_matrix.matrix[2] + matrix[7] * mult_matrix.matrix[5] + matrix[8] * mult_matrix.matrix[8];
    }

    // Умножение матриц с изменением значений элементов первой матрицы
    void operator*=(Matrix& mult_matrix){
        *this * mult_matrix;
        copying_from_Buffer();
    }

    // Присваивание значений другой матрицы
    void operator=(Matrix& _matrix){
        for (matrix_Index = 0; matrix_Index < 9; matrix_Index++){ matrix[matrix_Index] = _matrix[matrix_Index]; }
    }

    // Итераторы
    float& operator[](int index){ return matrix[index]; }    
    
    float& operator()(int index_1, int index_2){ return matrix[3 * index_1 + index_2]; }

    // ########################################################################
    // Копирование значений из matrix_Buffer
    void copying_from_Buffer(){
        for (matrix_Index = 0; matrix_Index < 9; matrix_Index++){ matrix[matrix_Index] = matrix_Buffer[matrix_Index]; }
    }

    // ########################################################################
    // Математические операции

    // Вычисление определителя
    float Determinant()
    {
        return matrix[0] * (matrix[4] * matrix[8] - matrix[7] * matrix[5]) - matrix[1] * (matrix[3] * matrix[8] - matrix[6] * matrix[5]) + matrix[2] * (matrix[3] * matrix[7] - matrix[6] * matrix[4]);
    }

    // Нахождение обратной матрицы и последующим сохранением в matrix_Buffer
    void Mreverse(){
        float det = Determinant();
        
        // Заполним matrix_Buffer алгебраическими дополнениями матрицы matrix и транспонируем её
        matrix_Buffer[0] =  (matrix[4] * matrix[8] - matrix[7] * matrix[5]) / det;    //matrix_Buffer[0][0]
        matrix_Buffer[3] = -(matrix[3] * matrix[8] - matrix[6] * matrix[5]) / det;    //matrix_Buffer[1][0]
        matrix_Buffer[6] =  (matrix[3] * matrix[7] - matrix[6] * matrix[4]) / det;    //matrix_Buffer[2][0]

        matrix_Buffer[1] = -(matrix[1] * matrix[8] - matrix[7] * matrix[2]) / det;    //matrix_Buffer[0][1]
        matrix_Buffer[4] =  (matrix[0] * matrix[8] - matrix[6] * matrix[2]) / det;    //matrix_Buffer[1][1]
        matrix_Buffer[7] = -(matrix[0] * matrix[7] - matrix[6] * matrix[1]) / det;    //matrix_Buffer[2][1]

        matrix_Buffer[2] =  (matrix[1] * matrix[5] - matrix[4] * matrix[2]) / det;    //matrix_Buffer[0][2]
        matrix_Buffer[5] = -(matrix[0] * matrix[5] - matrix[3] * matrix[2]) / det;    //matrix_Buffer[1][2]
        matrix_Buffer[8] =  (matrix[0] * matrix[4] - matrix[3] * matrix[1]) / det;    //matrix_Buffer[2][2]
    }

    // Заполнение матрицы значениями, соответствущие единичной матрице
    void IdentityMatrix(){
        matrix[0] = 1;
        matrix[1] = 0;
        matrix[2] = 0;
        matrix[3] = 0;
        matrix[4] = 1;
        matrix[5] = 0;
        matrix[6] = 0;
        matrix[7] = 0;
        matrix[8] = 1;
    }
};

#endif /*   __MATRIX_HPP    */