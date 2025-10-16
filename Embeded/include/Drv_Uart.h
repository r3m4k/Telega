#include "CBUFFER.H"
#include "stm32f30x_usart.h"

void InitUart(int Speed);// UART configuration
void UartSendChar(int c);
unsigned char UartSendBuff(unsigned char *Buff, int Size);

void Uart_irq_enable (void);
void Uart_irq_disable (void);
void UartSendString(unsigned char *Buff, int Size);
void SendUartNum(int N);
void SendUartByte(unsigned char B);
#define SendUart(A)	UartSendString((unsigned char*)(A),sizeof(A))
#define SendUartB(A)	UartSendBuff((unsigned char*)(A),sizeof((A)))


extern CBuffer<unsigned char> TxBuff;

extern "C" void ProcessInByte(unsigned char Bt);
