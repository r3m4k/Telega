#if !defined(_MFILTER_)
#define _MFILTER_
#ifdef _WIN32
#include <afx.h>
#endif
template <class Type> class MFilter
{
	typedef struct
	{
		Type Data;
		 int Index;
	} IDAT;
   public:
	MFilter(int Size)
	{
		Init(Size);
	}
	MFilter()
	{
		Counter=0;
		ID=0;
		Length=0;
		MiddlePoint=0;
	}
	~MFilter()
	{
		Done(); 
	}
	int  Init(int Size)
	{
		Length= Size;
		Counter=0;
		ID=(IDAT*)malloc(Size*sizeof(IDAT)); 
		MiddlePoint=((Length +1)/2)-1;
		if (ID)
		{
			for(int j=0; j < Size ; j++)
			{
				ID[j].Index=0;
				ID[j].Data=0;
			}
			return 1;
		} else return 0;
	};
	void Done()
	{
		if (ID) free(ID);
		ID=(IDAT*)NULL;
	};

	Type Compute(Type V)
	{
		int i,ipl;
		Counter++;
		for (i=0;i<Length;i++) // èùåì ñàìîãî ñòàðîãî ÷ëåíà Îí îòñòàåò íà Length îò ñ÷åò÷èêà
			if(ID[i].Index==(int)(Counter-Length))
				break;
		for (;i<Length-1;i++) ID[i]=ID[i+1]; // âûêèäûâàåì åãî èç ïîñëåäîâàòåëüíîñòè èçìåðåíèé ñäâèãàíèåì â ñòîðîíó íà÷àëà áóôåðà
		if (Counter>=(unsigned int)Length)
		{
			for (i=0;i<Length-1;i++) // èùåì ìåñòî äëÿ âñòàâêè íîâîãî èçìåðåíèÿ
				if (ID[i].Data<V)
					break; 
			ipl=i;
			for (i=Length-2;(i>=ipl)&&(ipl<Length-1);i--) ID[i+1]=ID[i];// ðàçäâèãàåì áóôåð â ñòîðîíó êîíöà, îñâîáîæäàÿ ìåñòî äëÿ íîâîãî èçìåðåíèÿ
			ID[ipl].Data=V;ID[ipl].Index=Counter;
		} else ipl=Counter;
		ID[ipl].Data=V;ID[ipl].Index=Counter;
		return ID[MiddlePoint].Data;
	}
	IDAT *ID;
    int    Length;
    unsigned int    MiddlePoint;
 	unsigned int Counter;
};

#endif
