#include "Matrix.hpp"
#include "COM_Port.hpp"

#define PI 3.14159265358979f


#define DATA_FILTERING
// #define DATA_PROCESSING
// #define USING_DPP
// #define ERROR_CALCULATION

#define OFFSET_VALUE    0           // Фиктивный пройденный путь (в метрах) между сигналами от ДПП
// #define OFFSET_VALUE    0.2256      // Пройденный путь (в метрах) между сигналами от ДПП

/*  Фильтрация входного потока данных  */
#define COMPLEX_FILTER
#define FilterSize          64      // ВАЖНО!!! Значение FilterSize должно нацело делиться на FilterFrameSize
#define FilterFrameSize     16
#define rolling_n           4
#define n_sigma             2.0f
// При такой конфигурации время обработки данных составляет 220 мс

#define X_COORD             (int) 0
#define Y_COORD             (int) 1
#define Z_COORD             (int) 2

#define TEMP_DELTA          2.0f  

/*  Отправка данных по com порту  */
#define SENDING_BUFFER          TRUE
#define SEND_RAW_DATA
// #define SEND_RAW_DATA_BUFFERED

extern COM_Port COM_port;

class Measure 
{
    
public:
    // -------------------------------------------------------------------------------
    // Данные, которые будут меняться в вызываемых функциях
    // Вынесем их в статические переменные для избежания переполнения стека процессора
    Data current_Data, zero_Data, buffer_Data;
    Matrix tmp_matrix;    
    // -------------------------------------------------------------------------------
    Matrix rotation_matrix;         // Матрица перехода от СК платы к глобальной СК, у которой ось OY направлена на север, а OZ перпендикулярно поверхности
    Matrix buffer_matrix;           // Матрица поворота от i-1 состояния в исходное
    float latitude;                // Широта места, где будет находиться плата
    // -------------------------------------------------------------------------------
    Frame Coordinates;              // Координаты перемещения по осям XYZ
    Frame Velocity;                 // Скорости по осям XYZ
    Frame Angles;                   // Углы поворота вокруг XYZ
    float shift = 0;                // Погрешность, накапливаемая при работе датчиков, которую необходимо компенсировать
    // -------------------------------------------------------------------------------
    bool new_tick_Flag = FALSE;     // Флаг, отвечающий за наличие нового прерывания от таймера
    bool new_DPP_Flag  = FALSE;     // Флаг, отвечающие за наличие нового кода от ДПП
    bool data_updated  = FALSE;     // Флаг, отвечающий за состояние данных: новые или старые
    // -------------------------------------------------------------------------------
    // Переменные для работы с прерываниями от таймера
    float period;                   // Период изменения TickCounter в секундах
    uint32_t TickCounter;           // Счётчик тиков запущенного таймера с периодом period (см main.cpp --> TimerInit())
    // -------------------------------------------------------------------------------
    // Переменные для работы с прерываниями от USART (канал связи с ДПП)
    uint32_t _DppCode;              // Код от ДПП
    float offset = OFFSET_VALUE;    // Перемещение от прошлого сигнала 
    float displacement[3] = {0};    // Изменение координат от предыдущей посылки ДПП
    // -------------------------------------------------------------------------------
    // Переменные для фильтрации данных
    struct FilterData               // Структура для хранения данных
    {
        float Acc_Buffer[3];        // Буфер для данных с акселерометра
        float Gyro_Buffer[3];       // Буфер для данных с гироскопа
    }FilterFrame[FilterSize];
   
    int temp_counter = 0;
    float temp_buffer[FilterFrameSize];
    bool Full_Temp_Buffer = FALSE;  // Флаг заполнения буфера температуры

    // Вспомогательные буферы для работы фильтра
    float tmp_Buffer[FilterSize];   
    float flt_Buffer[FilterSize];
    float tmp_frame_Buffer[FilterFrameSize];
    float flt_frame_Buffer[FilterFrameSize];
    
    int tmp_size;                   // Размер заполненных данных в tmp_Buffer / tmp_frame_Buffer в определённый момент времени
    int flt_size;                   // Размер заполненных данных в flt_Buffer / flt_frame_Buffer в определённый момент времени
    int frame_counter;              // Счётчик кусков данных

    // -------------------------------------------------------------------------------
    // Переменные для вычисление погрешности
#ifdef ERROR_CALCULATION
    Frame Acc_std;                  // СКО значений акселерометра
    Frame Gyro_std;                 // СКО значений гироскопа
#endif      /* ERROR_CALCULATION */
    // -------------------------------------------------------------------------------
    // Вспомогательные переменные (объявляем здесь чтобы не выделять под них постоянно память в ходе программы) 
    uint16_t index1, index2;        // Индексы для циклов 
    float tmp_float;
    // -------------------------------------------------------------------------------

    // ########################################################################
    // Конструктор класса и другие функции для работы с параметрами класса
    Measure(float phi, float _period) { 
        latitude = phi; 
        period = _period;          
        buffer_matrix.IdentityMatrix();
    }

    // ########################################################################
    // Функции для управления светодиодами    
    friend void LedOn(Led_TypeDef Led);
    friend void LedOff(Led_TypeDef Led);

    // ########################################################################
    // Чтение данных и последующая обработка (основной цикл программы)
    void measuring(){
        // while (1)
        // {
            
#ifdef DATA_FILTERING
            if (new_tick_Flag)       
            {
                LedOn(LED5);
                
                data_collecting();
                data_filtering(); 
#ifdef DATA_PROCESSING
                data_processing();
#endif      /* DATA_PROCESSING */                
                LedOff(LED5);
                data_updated = TRUE;
                new_tick_Flag = FALSE;
            }

            if (Full_Temp_Buffer){
                if (abs(buffer_Data.Temp - zero_Data.Temp) > TEMP_DELTA){
                    zero_Data.Temp = buffer_Data.Temp;
                    zero_Data.update_zero_level(buffer_Data.Temp, zero_Data.Temp);
                }
                Full_Temp_Buffer = FALSE;
            }
#endif      /* DATA_FILTERING */

#ifndef DATA_FILTERING
            buffer_Data.Read_Data();
#endif      /* DATA_FILTERING */

            if (data_updated){
                LedOn(LED8);
#ifdef SEND_RAW_DATA_BUFFERED
                buffer_Data - zero_Data;
                COM_port.sending_data(TickCounter, buffer_Data, SENDING_BUFFER);
#endif  /* SEND_RAW_DATA_BUFFERED */

#ifdef SEND_RAW_DATA
                COM_port.sending_data(TickCounter, buffer_Data);
#endif  /* SEND_RAW_DATA_BUFFERED */
                LedOff(LED8);
                data_updated = FALSE;
            }
        // }
    }

    // ########################################################################
    // Начальная выставка датчиков
    void initial_setting(){
        LedOn(LED4);
        LedOn(LED9);

        set_zero_Data();
        set_rotationMatrix();
        
        rotation_matrix.copying_from_Buffer();
        zero_Data * rotation_matrix;
            
        LedOff(LED4);
        LedOff(LED9);
    }

    // ########################################################################
    // Чтение данных с датчиков без обработки 
    void foo_reading_data(){
        current_Data.Read_Data();
        current_Data.Read_TempPrevious();
        current_Data.Read_Temp();
        buffer_Data.Temp = current_Data.Temp;
    }

private:
    // ########################################################################
    // Нахождение нулевых значений
    void set_zero_Data(){
        zero_Data.Read_TempPrevious();
        zero_Data.set_zero_Values();
        zero_Data.set_zero_Buffer();
        zero_Data.Temp_buffer = zero_Data.Temp_Previous;

        buffer_Data.Temp_Previous  = zero_Data.Temp_Previous;
        current_Data.Temp_Previous = zero_Data.Temp_Previous;

        int FilterFrame_num = pow(2, 8);
        
        // В буфере zero_Data будем хранить смещение нуля из-за температурного нагрева
        // Поэтому в цикле ниже НЕ ИСПОЛЬЗОВАТЬ операции, которые могут изменить zero_Data.Acc|Gyro_Buffer 
        for (int index = 0; index < FilterFrame_num; index++){
            data_collecting();
            data_filtering();            

            if (Full_Temp_Buffer){
                if (abs(buffer_Data.Temp - zero_Data.Temp_buffer) > (TEMP_DELTA / 2)){
                    zero_Data.Temp_buffer = buffer_Data.Temp;
                    zero_Data.update_zero_level_Buffer(buffer_Data.Temp, zero_Data.Temp_buffer);
                }
                Full_Temp_Buffer = FALSE;
            }

            buffer_Data.Acc -= zero_Data.Acc_Buffer;
            buffer_Data.Gyro -= zero_Data.Gyro_Buffer;
            zero_Data += buffer_Data;

            COM_port.sending_data(TickCounter++, buffer_Data);
        }
        zero_Data /= FilterFrame_num;
    }

    // ########################################################################
    // Нахождение матрицы перехода от СК датчиков к СК, связанную с Землей, у которой OY направлена на север, а OZ вертикально
    // Вывод коэффициентов матрицы поворота, а также описание используемых систем координат можно посмотреть в файле Documentation/Rotation_matrix.pdf
    void set_rotationMatrix()
    {        
        /* 
        Координаты векторов G, W в системе координат, связанной с платой

        G_x = zero_Data.Acc.X_coord;
        G_y = zero_Data.Acc.Y_coord;
        G_z = zero_Data.Acc.Z_coord;

        */

        // Получаем значение ускорения свободного падения способом ниже для того, чтобы не переводить значения из системы СИ в систему измерений датчиков.
        float G = sqrt(zero_Data.Acc.X_coord * zero_Data.Acc.X_coord + zero_Data.Acc.Y_coord * zero_Data.Acc.Y_coord + zero_Data.Acc.Z_coord * zero_Data.Acc.Z_coord); 
        float W = sqrt(zero_Data.Gyro.X_coord * zero_Data.Gyro.X_coord + zero_Data.Gyro.Y_coord * zero_Data.Gyro.Y_coord + zero_Data.Gyro.Z_coord * zero_Data.Gyro.Z_coord); 
        
        // Введём вспомогательный вектор А, как векторное произведение векторов W и G (см. документацию)
        float A = G * W * sin(latitude);

        float W_Y, W_Z;    // Координаты вектора W в системе координат, связанной с Землёй (W_X = 0)

        W_Y = W * sin(latitude);
        W_Z = W * cos(latitude);

        // Найдём координаты вектора а в СК датчика
        float a_x, a_y, a_z;
        a_x = zero_Data.Gyro.Y_coord * zero_Data.Acc.Z_coord - zero_Data.Gyro.Z_coord * zero_Data.Acc.Y_coord;
        a_y = zero_Data.Gyro.Z_coord * zero_Data.Acc.X_coord - zero_Data.Gyro.X_coord * zero_Data.Acc.Z_coord;
        a_z = zero_Data.Gyro.X_coord * zero_Data.Acc.Y_coord - zero_Data.Gyro.Y_coord * zero_Data.Acc.X_coord;

        rotation_matrix(0, 0) = a_x / A;
        rotation_matrix(1, 0) = a_y / A;
        rotation_matrix(2, 0) = a_z / A;

        rotation_matrix(0, 1) = (zero_Data.Gyro.X_coord - W_Z * zero_Data.Acc.X_coord / G) / W_Y;
        rotation_matrix(1, 1) = (zero_Data.Gyro.Y_coord - W_Z * zero_Data.Acc.Y_coord / G) / W_Y;
        rotation_matrix(2, 1) = (zero_Data.Gyro.Z_coord - W_Z * zero_Data.Acc.Z_coord / G) / W_Y;

        rotation_matrix(0, 2) = zero_Data.Acc.X_coord / G;
        rotation_matrix(1, 2) = zero_Data.Acc.Y_coord / G;
        rotation_matrix(2, 2) = zero_Data.Acc.Z_coord / G;

        rotation_matrix.Mreverse();
        // rotation_matrix.copying_from_Buffer();
    }

    // ########################################################################
    // Сбор сырых данных
    void data_collecting(){

        // Заполним буферы
        for (index1 = 0; index1 < FilterSize; index1++){
            current_Data.Read_Data();
            for (index2 = 0; index2 < 3; index2++){
                FilterFrame[index1].Acc_Buffer[index2]  = current_Data(0, index2);
                FilterFrame[index1].Gyro_Buffer[index2] = current_Data(1, index2);
            }
        }

        current_Data.Read_Temp();
        temp_buffer[temp_counter++] = current_Data.Temp;

        if (temp_counter == FilterFrameSize){
            mean(temp_buffer, FilterFrameSize);
            buffer_Data.Temp = tmp_float;
            temp_counter = 0;
            Full_Temp_Buffer = TRUE; 
        }
    }

    // ########################################################################
    // Обработка отфильтрованных данных
    void data_processing(){
        buffer_Data - zero_Data;

        // Вычислим угол поворота за время period, опираясь на данные полученные только на части этого промежутка
        // При этом считаем, что за время period не произойдёт сильных изменений ни угловых скоростей, ни ускорений
        for (index1 = 0; index1 < 3; index1++){
            Angles[index1] = buffer_Data.Gyro_Buffer[index1] * period * 1e-3 * PI / 180;    // Данные с гироскопа в mgps   
        }
        
        // Далее считаем, что tmp_matrix - матрица поворота от i-го состояния в i-1 состояние, соответствущее прошлой итерации обработки данных
        // Заполним матрицу tmp_matrix углами поворота вокруг XYZ (https://ru.wikipedia.org/wiki/Матрица_поворота)
        tmp_matrix(0, 0) =  cos(Angles.Y_coord) * cos(Angles.Z_coord);
        tmp_matrix(0, 1) = -sin(Angles.Z_coord) * cos(Angles.Y_coord);
        tmp_matrix(0, 2) =  sin(Angles.Y_coord);

        tmp_matrix(1, 0) =  sin(Angles.X_coord) * sin(Angles.Y_coord) * cos(Angles.Z_coord) + sin(Angles.Z_coord) * cos(Angles.X_coord);
        tmp_matrix(1, 1) = -sin(Angles.X_coord) * sin(Angles.Y_coord) * sin(Angles.Z_coord) + cos(Angles.X_coord) * cos(Angles.Z_coord);
        tmp_matrix(1, 2) = -sin(Angles.X_coord) * cos(Angles.Y_coord);

        tmp_matrix(2, 0) =  sin(Angles.X_coord) * sin(Angles.Z_coord) - sin(Angles.Y_coord) * cos(Angles.X_coord) * cos(Angles.Z_coord);
        tmp_matrix(2, 1) =  sin(Angles.X_coord) * cos(Angles.Z_coord) + sin(Angles.Y_coord) * sin(Angles.Z_coord) * cos(Angles.X_coord);
        tmp_matrix(2, 2) =  cos(Angles.X_coord) * cos(Angles.Y_coord);

        tmp_matrix *= buffer_matrix;       // Получили матрицу поворота в исходное состояние, при котором проводилась выставка
        buffer_matrix = tmp_matrix;        // Сохраним значения tmp_matrix в buffer_matrix, чтобы корректно перейти к i+1 состоянию
        
        tmp_matrix *= rotation_matrix;     // Получили матрицу поворота в СК Земли из i-го состояния

        // Вычислим приращение координат за время period в СК Земли
        buffer_Data.Acc_Buffer *= tmp_matrix;     // Значение ускорений в СК Земли

        // Заполним данные о координатах и скоростях                
        for (index1 = 0; index1 < 3; index1++){
            Coordinates[index1] += Velocity[index1] * period + buffer_Data.Acc_Buffer[index1] * period * period / 2 - shift;    
            Velocity[index1] += buffer_Data.Acc_Buffer[index1] * period;
            // displacement[index1] += Velocity[index1] * period + buffer_Data.Acc[index1] * period * period / 2; 
        }
    }

    // ########################################################################
    // Фильтрация входного потока данных
    /* Описание алгоритма фильтрации данных:
    Будем работать с частями буфера размера FilterFrameSize. Считаем, что данные на этом отрезке распределены нормально.
    Будем учитывать данные, отличающиеся от среднего значения только на n_sigma сигм (см ./Documentation/sigma_rule.jpg).
    Аналогичные действия выполняются со всеми частями буферов.
    
    Затем мы получаем данные без резких выбросов. По этому набору мы вычисляем скользящее среднее и вычисляем его среднее арифметическое.
    Это значение и будет принято за истинное значение на данном промежутке
    */
    void data_filtering(){

        // Получим истинные значения данных с акселерометра по осям
        AccXYZ_filtering(X_COORD);
        AccXYZ_filtering(Y_COORD);
        AccXYZ_filtering(Z_COORD);

        // Получим истинные значения данных с гироскопа по осям
        GyroXYZ_filtering(X_COORD);
        GyroXYZ_filtering(Y_COORD);
        GyroXYZ_filtering(Z_COORD);
    }

#ifdef COMPLEX_FILTER
    // Фильтрация данных одной координаты coord с акселерометра с последующим сохранением полученного значения в buffer_Data.Acc
    void AccXYZ_filtering(int coord){
        frame_counter = 0;
        flt_size = 0;

        // Отфильтруем резкие выбросы из Acc_Buffer[coord] и сохраним эти значения в flt_Buffer. Всего будет flt_size отфильтрованных значений
        for (index1 = 0; index1 < (FilterSize / FilterFrameSize); index1++){
            // Скопируем index1-ую часть буфера
            for (index2 = 0; index2 < FilterFrameSize; index2++){
                flt_frame_Buffer[index2] = FilterFrame[frame_counter * FilterFrameSize + index2].Acc_Buffer[coord];
            }
            tmp_size = 0;       // Размер заполненных данных в tmp_frame_Buffer
            sharp_emission_filter();

            for (index2 = 0; index2 < tmp_size; index2++){
                flt_Buffer[flt_size + index2] = tmp_frame_Buffer[index2];
            }
            
            flt_size += tmp_size;
            frame_counter++;
        }

        rolling_mean();
        mean(tmp_Buffer, tmp_size);

        buffer_Data.Acc[coord] = tmp_float;
    }

    // Фильтрация данных одной координаты coord с гироскопа с последующим сохранением полученного значения в buffer_Data.Gyro
    void GyroXYZ_filtering(int coord){
        frame_counter = 0;
        flt_size = 0;

        // Отфильтруем резкие выбросы из Gyro_Buffer[coord] и сохраним эти значения в flt_Buffer. Всего будет flt_size отфильтрованных значений
        for (index1 = 0; index1 < (FilterSize / FilterFrameSize); index1++){
            // Скопируем index1-ую часть буфера
            for (index2 = 0; index2 < FilterFrameSize; index2++){
                flt_frame_Buffer[index2] = FilterFrame[frame_counter * FilterFrameSize + index2].Gyro_Buffer[coord];
            }
            tmp_size = 0;       // Размер заполненных данных в tmp_frame_Buffer
            sharp_emission_filter();

            for (index2 = 0; index2 < tmp_size; index2++){
                flt_Buffer[flt_size + index2] = tmp_frame_Buffer[index2];
            }
            
            flt_size += tmp_size;
            frame_counter++;
        }

        rolling_mean();
        mean(tmp_Buffer, tmp_size);

        buffer_Data.Gyro[coord] = tmp_float;
    }
#endif  /*  COMPLEX_FILTER  */

#ifndef COMPLEX_FILTER
    // Фильтрация данных просто по среднему арифметическому
    void AccXYZ_filtering(int coord){
        for (index1 = 0; index1 < FilterSize; index1++){
            flt_Buffer[index1] = FilterFrame[index1].Acc_Buffer[coord];
        }
        mean(flt_Buffer, FilterSize);
        buffer_Data.Acc[coord] = tmp_float;
    }

    // Фильтрация данных просто по среднему арифметическому
    void GyroXYZ_filtering(int coord){
        for (index1 = 0; index1 < FilterSize; index1++){
            flt_Buffer[index1] = FilterFrame[index1].Gyro_Buffer[coord];
        }
        mean(flt_Buffer, FilterSize);
        buffer_Data.Gyro[coord] = tmp_float;
    }
#endif  /*  COMPLEX_FILTER  */

    // Фильтр резких выбросов значений из массива flt_frame_Buffer с сохранением в tmp_frame_Buffer
    void sharp_emission_filter(){
        mean(flt_frame_Buffer, FilterFrameSize);
        float mean_value = tmp_float;     
        
        std(flt_frame_Buffer, mean_value, FilterFrameSize);
        float std_value = tmp_float;

        for (index2 = 0; index2 < FilterFrameSize; index2++){
            if ((flt_frame_Buffer[index2] > (mean_value - n_sigma * std_value)) && (flt_frame_Buffer[index2] < (mean_value + n_sigma * std_value))){
                tmp_frame_Buffer[tmp_size++] = flt_frame_Buffer[index2];
            }
        }
    }

    // Вычисление плавающего среднего данных из flt_Buffer с сохранением в tmp_Buffer
    void rolling_mean(){
        tmp_size = flt_size - rolling_n + 1;
        tmp_float = 0;
        for (index2 = 0; index2 < tmp_size; index2++){
            for (int i = 0; i < rolling_n; i++){    tmp_float += flt_Buffer[index2 + i];    }
            tmp_float /= rolling_n;
            tmp_Buffer[index2] = tmp_float;
            tmp_float = 0;
        }
    }

    // Вычисление среднего арифметического с сохранением результата в tmp_float
    void mean(float *arr, int len){
        tmp_float = 0;
        for (index2 = 0; index2 < len; index2++){
            tmp_float += arr[index2];
        }
        tmp_float /= len;
    }

    // Вычисление среднеквадратического отклонения с сохранением результата в tmp_float
    void std(float *arr, float mean_value, int len){
        tmp_float = 0;
        for (index2 = 0; index2 < len; index2++){
            tmp_float += (arr[index2] - mean_value) * (arr[index2] - mean_value);
        }
        tmp_float = sqrt(tmp_float / len);
    }
};