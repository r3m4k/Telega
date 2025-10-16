#ifndef __FRAME_HPP
#define __FRAME_HPP

#include "Matrix.hpp"

extern float sqrt2;
extern float gyro_multiplier;

class Frame
{
public:
    /*
    XYZ - оси платы 
    xyz - оси МЕМС-датчиков
    Будем считать, что оси платы расположены следующим образом:
        OX - от процессора вправо
        OY - от процесора в сторону usb-портов
        OZ - вертикально
    */

    float X_coord;
    float Y_coord;
    float Z_coord;

    float frame_Buffer[3] = {0.0f};     // Буфер, в который будет заполняться временная информация с датчиков

    Frame(){
        X_coord = 0;
        Y_coord = 0;
        Z_coord = 0;
    }

    // ########################################################################
    // Перегрузка операторов

    // Сохранение результата в frame_Buffer первого слагаемого
    void operator+(Frame& frame){
        frame_Buffer[0] = X_coord + frame.X_coord;
        frame_Buffer[1] = Y_coord + frame.Y_coord;
        frame_Buffer[2] = Z_coord + frame.Z_coord;
    }

    // Изменение значений X_coord, Y_coord, Z_coord первого слагаемого
    void operator+=(Frame& frame){
        X_coord += frame.X_coord;
        Y_coord += frame.X_coord;
        Z_coord += frame.X_coord;
    }

    // Сохранение результата в frame_Buffer уменьшаемого
    void operator-(Frame& frame){
        frame_Buffer[0] = X_coord - frame.X_coord;
        frame_Buffer[1] = Y_coord - frame.Y_coord;
        frame_Buffer[2] = Z_coord - frame.Z_coord;
    }

    // Изменение значений X_coord, Y_coord, Z_coord уменьшаемого
    void operator-=(Frame& frame){
        X_coord -= frame.X_coord;
        Y_coord -= frame.X_coord;
        Z_coord -= frame.X_coord;
    }

    // Сохранение результата в frame_Buffer делимого
    void operator/(float num){
        frame_Buffer[0] = X_coord / num;
        frame_Buffer[1] = Y_coord / num;
        frame_Buffer[2] = Z_coord / num;
    }

    // Изменение значений X_coord, Y_coord, Z_coord делимого
    void operator/=(Frame& frame){
        X_coord /= frame.X_coord;
        Y_coord /= frame.X_coord;
        Z_coord /= frame.X_coord;
    }

    void operator=(Frame& frame){
        X_coord = frame.X_coord;
        Y_coord = frame.Y_coord;
        Z_coord = frame.Z_coord;    
    }

    void operator=(float arr[]){
        X_coord = arr[0];
        Y_coord = arr[1];
        Z_coord = arr[2];
    }

    float& operator[](int index){
        if      (index == 0) return X_coord;
        else if (index == 1) return Y_coord;
        else if (index == 2) return Z_coord;
    } 

    // ########################################################################
    // Математические операции с Matrix

    // Умножение frame на матрицу, как умножение вектора на матрицу, с сохранением результата в frame.frame_buffer
    void operator*(Matrix &matrix){
        frame_Buffer[0] = matrix[0] * X_coord + matrix[1] * Y_coord + matrix[2] * Z_coord;
        frame_Buffer[1] = matrix[3] * X_coord + matrix[4] * Y_coord + matrix[5] * Z_coord;
        frame_Buffer[2] = matrix[6] * X_coord + matrix[7] * Y_coord + matrix[8] * Z_coord;
    }

    // Умножение frame на матрицу, как умножение вектора на матрицу, с сохранением результата в frame
    void operator*=(Matrix &matrix){
        *this * matrix;
        copying_from_buffer();
    }

    // ########################################################################
    // Чтение данных с датчиков
    
    friend void ReadAcc(float *pfData);
    friend void ReadGyro(float *pfData);
    friend void ReadMag(float *pfData);

    void Read_Acc()
    {
        /*
        В соответствии с документацией на LSM303DLHC:
        OX =  oy
        OY = -ox
        OZ =  oz
        */
        ReadAcc(frame_Buffer);
        X_coord =  frame_Buffer[1] / 100;
        Y_coord = -frame_Buffer[0] / 100;
        Z_coord =  frame_Buffer[2] / 100;
        // Домножаем на 0.1, чтобы ускорения были в mg
    }

    void Read_Gyro()
    {
        /*
        В соответствии с документацией на L3GD20:
        OX = ox
        OY = oy
        OZ = oz
        */
        ReadGyro(frame_Buffer);
        X_coord = (frame_Buffer[0] / gyro_multiplier);
        Y_coord = (frame_Buffer[1] / gyro_multiplier);
        Z_coord = (frame_Buffer[2] / gyro_multiplier);
        // Домножаем на 100, чтобы передать 2 значащие цифры после запятой,
        // тк данные отправляются в целочисленном виде
    }

    void Read_Mag()
    {
        /*
        В соответствии с документацией на LSM303DLHC:
        OX =  oy
        OY = -ox
        OZ =  oz
        */
        ReadMag(frame_Buffer);
        X_coord =  frame_Buffer[1] * 1000;
        Y_coord = -frame_Buffer[0] * 1000;
        Z_coord =  frame_Buffer[2] * 1000;
        // Домножаем на 1000, чтобы перевести напряжённость магнитного поля в мкГауссы
    }

    // ########################################################################
    // Дополнительный функционал

    void set_zero_frame_Buffer(){
        frame_Buffer[0] = 0;
        frame_Buffer[1] = 0;
        frame_Buffer[2] = 0;
    }

    void set_zero_Frame(){
        X_coord = 0;
        Y_coord = 0;
        Z_coord = 0;
    }

    void copying_from_buffer(){
        X_coord = frame_Buffer[0];
        Y_coord = frame_Buffer[1];
        Z_coord = frame_Buffer[2];
    }
};

#endif /*    __FRAME_HPP    */