# куда кладем результат сборки проекта и где будут объектные файлы
BIN_PLACE = Debug_Lin/

PROGRAM_NAME = STM_IMIT_DPP_RA

# как будет называться исполняемый файл - итог сборки
BINARY = ${PROGRAM_NAME}.elf

#GCC_PLACE=/home/mike/gcc-arm-none-eabi-8-2019-q3-update/
GCC_PLACE=/usr/
#исполняемый файл компиллятора-компоновщика
CC = ${GCC_PLACE}bin/arm-none-eabi-gcc
CP = ${GCC_PLACE}bin/arm-none-eabi-g++

#включаемые директории
INCLUDES = \
-I"include" \
-I"system/include" \
-I"system/include/cmsis" \
-I"system/include/stm32f3-stdperiph"

# общие флаги компиллятора
COMPILER_FLAGS = \
-mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16 -O0 -fmessage-length=0 -fsigned-char \
-ffunction-sections -fdata-sections -ffreestanding -fno-move-loop-invariants -Wall -Wextra -g3

# предопределенные константы
DEFINES= \
-DUSE_STDPERIPH_DRIVER \
-DDEBUG \
-DSTM32F30X \
-DHSE_VALUE=8000000 \

# флаги для gcc  - не перепутывать!!! только gnu11 разрешает пользоваться
# директивами встроенного ассемблера "asm" -они могут встречаться в стандартной библиотеке

GCC_FLAGS = -std=gnu11 ${COMPILER_FLAGS} -c

# флаги для g++
GPP_FLAGS = -std=gnu++11 ${COMPILER_FLAGS} -c -fabi-version=0 -fno-exceptions -fno-rtti -fno-use-cxa-atexit -fno-threadsafe-statics

# флаги для линковщика
LINK_FLAGS = ${COMPILER_FLAGS} \
-T mem.ld -T libs.ld -T sections.ld -L"${PROJ}ldscripts" \
-nostartfiles -Xlinker --gc-sections -Wl,-Map,${BIN_PLACE}${PROGRAM_NAME}.map # --specs=nano.specs 

# библиотеки компоновщика - должны быть последними в списке команды компоновщика
#LIBS = ${GCC_PLACE}arm-none-eabi/lib/thumb/v7e-m+fp/hard/libm.a
#LIBS = -L${GCC_PLACE}arm-none-eabi/lib/thumb/v7e-m+fp/hard -lm
#/home/mike/gcc-arm-none-eabi-8-2019-q3-update/arm-none-eabi/lib/thumb/v7e-m+dp/hard/libm.a

OBJECTS = \
${BIN_PLACE}system_stm32f30x.o \
${BIN_PLACE}vectors_stm32f30x.o  \
${BIN_PLACE}_initialize_hardware.o \
${BIN_PLACE}_reset_hardware.o \
${BIN_PLACE}exception_handlers.o \
${BIN_PLACE}Trace.o \
${BIN_PLACE}trace_impl.o  \
${BIN_PLACE}_exit.o \
${BIN_PLACE}_sbrk.o \
${BIN_PLACE}_startup.o \
${BIN_PLACE}_syscalls.o \
${BIN_PLACE}stm32f30x_can.o \
${BIN_PLACE}stm32f30x_gpio.o  \
${BIN_PLACE}stm32f30x_misc.o \
${BIN_PLACE}stm32f30x_rcc.o  \
${BIN_PLACE}stm32f30x_tim.o \
${BIN_PLACE}stm32f30x_usart.o \
${BIN_PLACE}_write.o \
${BIN_PLACE}Drv_Gpio.opp \
${BIN_PLACE}Drv_Uart.opp \
${BIN_PLACE}main.opp

${BIN_PLACE}$(BINARY) : $(OBJECTS)
	echo "СБОРКА "${BIN_PLACE}${BINARY}", КАРТА ПАМЯТИ "${BIN_PLACE}${PROGRAM_NAME}.map
	$(CC) ${LINK_FLAGS} -o ${BIN_PLACE}$(BINARY) $(OBJECTS) ${LIBS}
	${GCC_PLACE}bin/arm-none-eabi-size --format=berkeley ${BIN_PLACE}${BINARY}
	@echo "ФОРМИРОВАНИЕ "${BIN_PLACE}${PROGRAM_NAME}.hex 
	${GCC_PLACE}bin/arm-none-eabi-objcopy -O ihex ${BIN_PLACE}${BINARY} ${BIN_PLACE}${PROGRAM_NAME}.hex 

%.o:
	echo "gcc "$<
	$(CC) ${GCC_FLAGS} ${DEFINES} ${INCLUDES}  $< -o $@

%.opp:
	echo "g++ "$<
	$(CP) ${GPP_FLAGS} ${DEFINES} ${INCLUDES} $< -o $@

${BIN_PLACE}stm32f30x_usart.o : system/src/stm32f3-stdperiph/stm32f30x_usart.c
${BIN_PLACE}stm32f30x_tim.o : system/src/stm32f3-stdperiph/stm32f30x_tim.c
${BIN_PLACE}stm32f30x_rcc.o : system/src/stm32f3-stdperiph/stm32f30x_rcc.c
${BIN_PLACE}stm32f30x_misc.o : system/src/stm32f3-stdperiph/stm32f30x_misc.c
${BIN_PLACE}stm32f30x_gpio.o : system/src/stm32f3-stdperiph/stm32f30x_gpio.c
${BIN_PLACE}stm32f30x_can.o : system/src/stm32f3-stdperiph/stm32f30x_can.c
${BIN_PLACE}_cxx.opp : system/src/newlib/_cxx.cpp
${BIN_PLACE}_exit.o : system/src/newlib/_exit.c
${BIN_PLACE}_sbrk.o : system/src/newlib/_sbrk.c
${BIN_PLACE}_startup.o : system/src/newlib/_startup.c
${BIN_PLACE}_syscalls.o : system/src/newlib/_syscalls.c
${BIN_PLACE}assert.o  : system/src/newlib/assert.c
${BIN_PLACE}Trace.o : system/src/diag/Trace.c
${BIN_PLACE}trace_impl.o  : system/src/diag/trace_impl.c
${BIN_PLACE}_initialize_hardware.o : system/src/cortexm/_initialize_hardware.c
${BIN_PLACE}_reset_hardware.o : system/src/cortexm/_reset_hardware.c
${BIN_PLACE}exception_handlers.o  : system/src/cortexm/exception_handlers.c
${BIN_PLACE}system_stm32f30x.o : system/src/cmsis/system_stm32f30x.c
${BIN_PLACE}vectors_stm32f30x.o  : system/src/cmsis/vectors_stm32f30x.c
${BIN_PLACE}_write.o : src/_write.c
${BIN_PLACE}Drv_Gpio.opp : src/Drv_Gpio.cpp
${BIN_PLACE}Drv_Uart.opp : src/Drv_Uart.cpp
${BIN_PLACE}main.opp : src/main.cpp

clean:
	@echo "ОЧИСТКА ПРОЕКТА"
	rm -f ${BIN_PLACE}${BINARY} ${OBJECTS} ${BIN_PLACE}${PROGRAM_NAME}.hex ${BIN_PLACE}${PROGRAM_NAME}.map
 
