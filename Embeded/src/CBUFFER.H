#ifndef __BUFFER__

#define __BUFFER__

// #include <stdlib.h>
#include <string.h>

/*--------------������� �����  "�����"-------------
    �������� - �� ����� "FILTER.H" ��� SC
--------------------------------------------------*/
class GBuffer
{
public:
    int Init(int size, int place)
    {
        Buff = (void *)place;
        ReadPoint = 0;
        WritePoint = 0;
        BufferSize = size;
        return (int)(Buff);
    };
    void Done() {
    };
    int ReadPoint;
    int WritePoint;

protected:
    int BufferSize;
    void *Buff;
};

template <class Type>
class CBuffer : public GBuffer
{
public:
    CBuffer()
    {
        DataSize = 0;
        Buff = 0;
    }
    int DataSize;
    int Init(int Size, int Place)
    {
        if (!Size)
            Size = 1; // ������������
        if (!GBuffer::Init(Size * sizeof(Type), Place))
            return 0;
        BufferSize = Size;
        DataSize = 0;
        for (unsigned int i = 0; i < Size * sizeof(Type); i++)
            ((char *)Buff)[i] = 0;
        return 1;
    };
    void Done()
    {
        DataSize = 0;
        if (Buff)
            memset(Buff, '\0', BufferSize * sizeof(Type));
        GBuffer::Done();
    };
    // ����������� ������ � �����
    void WriteTo(Type X)
    {
        if (Buff)
            ((Type *)Buff)[WritePoint] = X;
        if (!IsFull())
        {
            WritePoint = (WritePoint + 1) % BufferSize;
            DataSize++;
        }
    };
    // ������ � ����� �� �������
    void Write(Type X, int Index)
    {
        if (Buff)
            ((Type *)Buff)[Index] = X;
    };
    // ������ �� ������ �� �������
    Type Read(int Index)
    {
        return ((Type *)Buff)[Index % BufferSize];
    };
    Type ReadIndex(int Index)
    {
        return ((Type *)Buff)[Index];
    };

    // ����������� ������ �� ������
    Type ReadFrom()
    {
        Type X = ((Type *)Buff)[ReadPoint];
        if (!IsEmpty())
        {
            ReadPoint = (ReadPoint + 1) % BufferSize;
            DataSize--;
        }
        return X;
    };
    bool IsEmpty()
    {
        return DataSize == 0;
    };
    bool IsFull()
    {
        return DataSize >= BufferSize;
    }
    // ������ ���� ��������, ������� ����� ������ ��� ��������� ������
    Type ReadExtra()
    {
        return ((Type *)Buff)[WritePoint];
    };
    // ������ �������� ������������ ����� ������
    Type Delay(int MDelay)
    {
        if (MDelay >= BufferSize)
            return ReadExtra();
        return ((Type *)Buff)[(WritePoint + BufferSize - MDelay - 1) % BufferSize];
    };
    Type Delay_Max(Type X)
    {
        WriteTo(X);
        return ReadExtra();
    };
};

#endif
