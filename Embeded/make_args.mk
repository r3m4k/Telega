# ----------------------------------
# Используемые переменные в Makefile
# ----------------------------------

# ОС, на которой собирается проект
# SYSTEM - переменная, задаваемая при запуске makefile
# Зададим её тут, чтобы при запуске makefile из командной строки не задавать её
SYSTEM := windows	

PROGRAM_NAME = STM_ACC_GIRO_FILTERED

# Название итогового исполняемого файла
BINARY = ${PROGRAM_NAME}.elf

# Место хранения полученных объектных файлов
ifeq ($(SYSTEM), windows)
	BIN_PLACE = Debug_Win
else ifeq ($(SYSTEM), linux)
	BIN_PLACE = Debug_Lin
else
    $(error The OS is not specified)
endif

ifeq ($(SYSTEM), windows)
	GCC_PLACE = c:/SysGCC/arm-eabi
else ifeq ($(SYSTEM), linux)
	GCC_PLACE = /home/mike/gcc-arm-none-eabi-8-2019-q3-update/
else
    $(error The OS is not specified)
endif

# Исполняемый файл компиллятора-компоновщика
CC = ${GCC_PLACE}/bin/arm-none-eabi-gcc
CP = ${GCC_PLACE}/bin/arm-none-eabi-g++

# Флаги компиллятора
COMPILER_FLAGS = \
-mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16 -O0 -fmessage-length=0 -fsigned-char \
-ffunction-sections -fdata-sections -ffreestanding -fno-move-loop-invariants -Wall -Wextra -g3

# Предопределенные константы
DEFINES= \
-DUSE_STDPERIPH_DRIVER \
-DDEBUG \
-DSTM32F30X \
-DHSE_VALUE=8000000

# флаги для gcc - не перепутывать!!! только gnu11 разрешает пользоваться
# директивами встроенного ассемблера "asm" -они могут встречаться в стандартной библиотеке

GCC_FLAGS = -std=gnu11 ${COMPILER_FLAGS} -c

# флаги для g++
# GPP_FLAGS = -std=gnu++11 ${COMPILER_FLAGS} -c -fabi-version=0 -fno-exceptions -fno-rtti -fno-use-cxa-atexit -fno-threadsafe-statics
GPP_FLAGS = -std=gnu++11 ${COMPILER_FLAGS} -c -fno-exceptions -fno-rtti -fno-use-cxa-atexit -fno-threadsafe-statics

# библиотеки компоновщика - должны быть последними в списке команды компоновщика
# C:\SysGCC\arm-eabi\arm-none-eabi\lib\libm.a
# LIBS = -L${GCC_PLACE}arm-none-eabi/lib/arm/v5te/hard -lm 

INCLUDES = \
-I"${GCC_PLACE}arm-none-eabi/include" \
-I"include" \
-I"src" \
-I"system/include" \
-I"system/include/cmsis" \
-I"system/include/stm32f3-stdperiph" \
-I"system/include/additionally" \
-I"system/USB_LIB/include"

# флаги для линковщика
LINK_FLAGS = ${COMPILER_FLAGS} \
-T "ldscripts/mem.ld" \
-T "ldscripts/libs.ld" \
-T "ldscripts/sections.ld" \
-L"${PROJ}ldscripts" \
-nostartfiles -Xlinker --gc-sections -Wl,-Map,${BIN_PLACE}/${PROGRAM_NAME}.map # --specs=nano.specs 

# Список используемых поддиректорий для сборки проекта
SUBDIRS_OBJ =

# Используемые в проекте библиотеки
LIBS = -L${GCC_PLACE}/arm-none-eabi/arm/v5te/hard -lm

# Список всех объектных файлов проекта
OBJECTS =