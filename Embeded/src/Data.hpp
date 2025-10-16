#ifndef __DATA_HPP
#define __DATA_HPP

#include "Frame.hpp"
#include "VCP_F3.h"

#define MAX_TEMP_DIFF       4           // Максимальное изменение температуры между снятиями показаний 
                                        // (4 сигм для MAX_TEMP_DIFF = 10 при тепловом равновесии датчика и окружающей среды)
#define MAX_TEMP_COUNTER    16          // Раз в какое количество шагов будет считываться температура. Лучше использовать FilterFrameSize


class Data
{
public:
    Frame Acc;      // Класс для хранения данных с акселерометра
    Frame Gyro;     // Класс для хранения данных с гироскопа
    
    // Буферы, в которые будет сохраняться временная информация
    Frame Acc_Buffer, Gyro_Buffer;

    float Temp, Temp_buffer, Temp_Previous;        // Значения температуры

    // см. D:\Job\STM reading data\temp_coefficients.json
    // d(u) = a(temp) * d(temp), a(temp) = Acc|Gyro_coeff[_][0] * temp + Acc|Gyro_coeff[_][1]
    // double Acc_coeff[3][2] = {
    //     {-0.000012182535295, -0.000388057852213},
    //     {-0.000004738017290, 0.001753094951160},
    //     {0.000003711110736, 0.001713383764375}
    // };         // Коэффициенты изменения ускорений от изменения температуры
    // double Gyro_coeff[3][2] = {
    //     {-0.000269236998542, 0.057015150088188},
    //     {0.000162277323684, -0.015148759220088},
    //     {0.000159065090423, -0.037555983340566}
    // };        // Коэффициенты изменения угловых скоростей от изменения температуры
    double Acc_coeff[3][2] = {0.0f};
    double Gyro_coeff[3][2] = {0.0f};
    uint8_t i;  

    // ########################################################################
    // Перегрузка операторов

    // Сохранение результата в Acc_Buffer, Gyro_Buffer, Mag_Buffer первого слагаемого
    void operator+(Data &data)
    {
        Acc + data.Acc;
        Acc_Buffer = Acc.frame_Buffer;

        Gyro + data.Gyro;
        Gyro_Buffer = Gyro.frame_Buffer;

        Temp_buffer += data.Temp;

    }

    // Изменение значений Acc, Gyro, Mag первого слагаемого
    void operator+=(Data &data)
    {
        Acc + data.Acc;
        Acc = Acc.frame_Buffer;

        Gyro + data.Gyro;
        Gyro = Gyro.frame_Buffer;

        Temp += data.Temp;
    }

    // Сохранение результата в Acc_Buffer, Gyro_Buffer, Mag_Buffer уменьшаемого
    void operator-(Data &data)
    {
        Acc - data.Acc;
        Acc_Buffer = Acc.frame_Buffer;

        Gyro - data.Gyro;
        Gyro_Buffer = Gyro.frame_Buffer;

        Temp_buffer -= data.Temp;
    }

    // Изменение значений Acc, Gyro, Mag уменьшаемого
    void operator-=(Data &data)
    {
        Acc - data.Acc;
        Acc = Acc.frame_Buffer;

        Gyro - data.Gyro;
        Gyro = Gyro.frame_Buffer;

        Temp -= data.Temp;
    }

    // Сохранение результата в Acc_Buffer, Gyro_Buffer, Mag_Buffer делимого
    void operator/(float num)
    {
        Acc / num;
        Acc_Buffer = Acc.frame_Buffer;

        Gyro / num;
        Gyro_Buffer = Gyro.frame_Buffer;

        Temp_buffer /= num;
    }

    // Изменение значений Acc, Gyro, Mag делимого
    void operator/=(float num)
    {
        Acc / num;
        Acc = Acc.frame_Buffer;

        Gyro / num;
        Gyro = Gyro.frame_Buffer;

        Temp /= num;
    }

    void operator=(Data &data)
    {
        Acc = data.Acc;
        Gyro = data.Gyro;
        Temp = data.Temp;
    }

    Frame& operator[](int index)
    {
        if (index == 0)
            return Acc;
        else if (index == 1)
            return Gyro;
    }

    float operator()(int index1, int index2){
        if      (index1 == 0){
            if      (index2 == 0) return Acc.X_coord;
            else if (index2 == 1) return Acc.Y_coord;
            else if (index2 == 2) return Acc.Z_coord;
        }
        else if (index1 == 1){
            if      (index2 == 0) return Gyro.X_coord;
            else if (index2 == 1) return Gyro.Y_coord;
            else if (index2 == 2) return Gyro.Z_coord;
        }
    }

    // ########################################################################
    // Математические операции с Matrix

    // Умножение data.Acc, data.Gyro на матрицу, поэлементно, как умножение векторов на матрицу, с сохранением 
    // результата в data.Acc_Buffer, data.Gyro_Buffer
    void operator*(Matrix &matrix){
        Acc * matrix;
        Acc_Buffer = Acc.frame_Buffer;

        Gyro * matrix;
        Gyro_Buffer = Gyro.frame_Buffer;
    }

    // Умножение data.Acc, data.Gyro на матрицу с изменением значений data.Acc, data.Gyro
    // Сделано именно так, чтобы избежать повторного include из Data.h
    // Более того, в Data.h не используется функционал из Matrix.h, поэтому делать include Matrix.h в Data.h нецелесообразно 
    void operator*=(Matrix &matrix){
        *this * matrix;

        Acc = Acc_Buffer;
        Gyro = Gyro_Buffer;
    }
    // ########################################################################
    // Чтение данных с датчиков
    void Read_Data()
    {
        Acc.Read_Acc();
        Gyro.Read_Gyro();
    }

    friend void ReadMagTemp(float *pfTData);
    void Read_Temp(){
        // Перед вызовом функции необходимо вызвать Read_TempPrevious !!!
        // Проверка не сделана для оптимизации кода
        ReadMagTemp(&Temp);
        if (abs(Temp - Temp_Previous) > MAX_TEMP_DIFF){
            // Если разница между прошлой температурой и текущей больше MAX_TEMP_DIFF единиц,
            // то считаем, что полученное значение температуры неверное и заполним его предыдущим значением
            Temp = Temp_Previous;
        }
        Temp_Previous = Temp;
    }

    void Read_TempPrevious(){
        Temp_Previous = 0;
        for (i = 0; i < 32; i++){
            ReadMagTemp(&Temp_buffer);
            Temp_Previous += Temp_buffer;
            for (uint8_t j = 0; j < 255; j++){   continue;   }      // Задержка
        }
        Temp_Previous /= 32;
    }

    // ########################################################################
    // Функционал для Data

    // Установка нулевых значений
    void set_zero_Values()
    {
        Acc.set_zero_Frame();
        Gyro.set_zero_Frame();

        Temp = 0.0f;
    }

    void set_zero_Buffer()
    {
        Acc_Buffer.set_zero_Frame();
        Gyro_Buffer.set_zero_Frame();

        Temp_buffer = 0.0f;
    }

    void update_zero_level(float temp_current, float temp_previous){
        for (i = 0; i < 3; i++){
            Acc[i] -= (Acc_coeff[i][0] * (double)temp_current + Acc_coeff[i][1]) * (temp_current - temp_previous);
            Gyro[i] -= (Gyro_coeff[i][0] * (double)temp_current + Gyro_coeff[i][1]) * (temp_current - temp_previous);
        }
    }

    void update_zero_level_Buffer(float temp_current, float temp_previous){
        for (i = 0; i < 3; i++){
            Acc_Buffer[i] -= (Acc_coeff[i][0] * (double)temp_current + Acc_coeff[i][1]) * (temp_current - temp_previous);
            Gyro_Buffer[i] -= (Gyro_coeff[i][0] * (double)temp_current + Gyro_coeff[i][1]) * (temp_current - temp_previous);
        }
    }
};

#endif /*    __DATA_HPP    */