#if !defined(_CFILTER_)
#define _CFILTER_


#include "CBUFFER.H"

template <class Type> class CFilterBF
{
public:
	void Done()
	{
		Summ=0;
		Fp=0;
	};
	int  Init(int Size)
	{
		mask=0;
		Sz=Size;
		shifts=0;
		Summ=0;
		for(;Sz>1;Sz=Sz>>1)
		{
			mask=(mask<<1)|1;
			shifts++;
		}
		if (Fp) Done();
		Fp=1;
		Preset();
		WritePoint=0;
		return 1;
	};
	void Preset()
	{
	    for ( int i=0;i<Sz;i++ ) Buff[i]=0; 
	};
	Type LoCompute(Type X)
	{

		Summ+=X-Buff[WritePoint];
		Buff[WritePoint]=X;
		WritePoint=(WritePoint+1) &mask;
		return Summ>>shifts;
	};
	Type HiCompute(Type X)
	{
		return X-LoCompute(X);
	};
    Type Summ;  
	int Fp;
	int mask;
	int shifts;
	int Sz;
	int WritePoint;
	Type Buff[64];
};


template <class Type> class CFilter: public CBuffer<Type>
{
public:
	CFilter ()
	{
		Fp=1;
		ComputeCounter = 0;
	}
	CFilter (int S)
	{
		Init(S);
	}
	void Done()
	{
		Summ=0;
		Fp=0;
		CBuffer<Type>::Done();
	};
	int  Init(int Size)
	{
		Summ=0;
		if (Fp) Done();
		Fp=1;
		ComputeCounter = 0;
		return CBuffer<Type>::Init(Size);
	};
	void Preset(Type X)
	{
	    for ( int i=0;i<CBuffer<Type>::BufferSize;i++ ) CBuffer<Type>::WriteTo(X); 
	};
	Type LoCompute(Type X, int Num = 0)
	{
		ComputeCounter++;
		if (CBuffer<Type>::BufferSize < 2) return X;
		if (Num)
		{
			if ((ComputeCounter)>(CBuffer<Type>::BufferSize + 1))
				Summ += X - CBuffer<Type>::Delay(Num);
			else
			{
				if (ComputeCounter>Num)
					Summ += X - CBuffer<Type>::Delay(Num);
				else
					Summ += X - CBuffer<Type>::Delay(ComputeCounter);
			}

			CBuffer<Type>::WriteTo(X);
			return Summ / Num;
		}
		else
		{
			if ((ComputeCounter)<(CBuffer<Type>::BufferSize + 1))
			{
				Summ += X;
				CBuffer<Type>::WriteTo(X);
				return Summ / ComputeCounter;
			} else
			{
				Summ += X - CBuffer<Type>::ReadExtra();
				CBuffer<Type>::WriteTo(X);
				return Summ / CBuffer<Type>::BufferSize;
			}
		}
	};
	Type HiCompute(Type X)
	{
		return X-LoCompute(X);
	};
    Type Summ;  
	int Fp,ComputeCounter;
};

template <class Type> class SkoFilter 
{
	public:
		CFilter<Type> Diff,Mean;
		void Done()
		{
			Diff.Done();
			Mean.Done();
		};
		int  Init(int Size)
		{
			return Diff.Init(Size) && Mean.Init(Size*100);
		};

		Type Compute(Type X)
		{
			return Mean.LoCompute(fabs(Diff.HiCompute(X)));
		};
};

template <class Type> class DriftFilter
{
public:
	CFilter<Type> Diff, Mean;
	void Done()
	{
		Diff.Done();
		Mean.Done();
	};
	int  Init(int Size,int MeanSize=0)
	{
		if (MeanSize == 0)
			MeanSize = Size / 10;
		Counter = MeanSize;
		return Diff.Init(Size) && Mean.Init(MeanSize);
	};

	Type Compute(Type X,bool Enable=true)
	{
		if (Enable && Counter)
		{
			Counter--;
			Offset = Mean.LoCompute(X);
			Diff.HiCompute(X-Offset);
			return X;
		}
		Type tmp = X - Offset;
		tmp = Diff.HiCompute(tmp);
		tmp += Offset;
		return  tmp;// Mean.LoCompute(fabs(Diff.HiCompute(X)));
	};
	int Ready()	{	return Counter == 0;	}
	int Counter;
	Type Offset;
};

template <class Type> class PR_Filter // // Prasoloff filter
{
	public:
		CFilter<Type> F1,F2;
public:
	PR_Filter ()
	{
	}
	PR_Filter (int S)
	{
		Init(S);
	}
	void Done()
	{
		F1.Done();
		F2.Done();
	};
	int  Init(int Size)
	{
		return F1.Init(Size) && F2.Init((Size*139)/100);
	};
	Type LoCompute(Type X)
	{
		return F2.LoCompute(F1.LoCompute(X));
	};
	Type HiCompute(Type X)
	{
		return X-LoCompute(X);
	};
};



#endif

