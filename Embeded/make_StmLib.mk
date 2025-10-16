# ---------------------------
# STM_STD_LIB
# ---------------------------

STM_STD_LIB_NAME = libstm_std_lib.a
# LIBS += -L./${BIN_PLACE} -lstm_std_lib
OBJECTS += ${STM_STD_LIB_OBJ}

SUBDIRS_OBJ += \
${STM32_PERIPH_OBJ_DIR} \
${CMSIS_OBJ_DIR} \
${NEWLIB_OBJ_DIR} \
${DIAG_OBJ_DIR} \
${CORTEXM_OBJ_DIR}

# ---------------------------
# Исходные файлы
# ---------------------------

# stm32f3-stdperiph
STM32_PERIPH_DIR = system/src/stm32f3-stdperiph

STM32_PERIPH_SRC = \
${STM32_PERIPH_DIR}/stm32f30x_adc.c \
${STM32_PERIPH_DIR}/stm32f30x_can.c \
${STM32_PERIPH_DIR}/stm32f30x_comp.c \
${STM32_PERIPH_DIR}/stm32f30x_crc.c \
${STM32_PERIPH_DIR}/stm32f30x_dac.c \
${STM32_PERIPH_DIR}/stm32f30x_dbgmcu.c \
${STM32_PERIPH_DIR}/stm32f30x_dma.c \
${STM32_PERIPH_DIR}/stm32f30x_exti.c \
${STM32_PERIPH_DIR}/stm32f30x_flash.c \
${STM32_PERIPH_DIR}/stm32f30x_gpio.c \
${STM32_PERIPH_DIR}/stm32f30x_i2c.c \
${STM32_PERIPH_DIR}/stm32f30x_it.c \
${STM32_PERIPH_DIR}/stm32f30x_iwdg.c \
${STM32_PERIPH_DIR}/stm32f30x_misc.c \
${STM32_PERIPH_DIR}/stm32f30x_opamp.c \
${STM32_PERIPH_DIR}/stm32f30x_pwr.c \
${STM32_PERIPH_DIR}/stm32f30x_rcc.c \
${STM32_PERIPH_DIR}/stm32f30x_rtc.c \
${STM32_PERIPH_DIR}/stm32f30x_spi.c \
${STM32_PERIPH_DIR}/stm32f30x_syscfg.c \
${STM32_PERIPH_DIR}/stm32f30x_tim.c \
${STM32_PERIPH_DIR}/stm32f30x_usart.c \
${STM32_PERIPH_DIR}/stm32f30x_wwdg.c \
${STM32_PERIPH_DIR}/stm32f3_discovery.c \
${STM32_PERIPH_DIR}/stm32f3_discovery_l3gd20.c \
${STM32_PERIPH_DIR}/stm32f3_discovery_lsm303dlhc.c

# cmsis
CMSIS_DIR = system/src/cmsis

CMSIS_SRC = \
${CMSIS_DIR}/system_stm32f30x.c \
${CMSIS_DIR}/vectors_stm32f30x.c

# newlib
NEWLIB_DIR = system/src/newlib

NEWLIB_SRC_C = \
${NEWLIB_DIR}/assert.c \
${NEWLIB_DIR}/_exit.c \
${NEWLIB_DIR}/_sbrk.c \
${NEWLIB_DIR}/_startup.c \
${NEWLIB_DIR}/_syscalls.c

NEWLIB_SRC_CPP = \
${NEWLIB_DIR}/_cxx.cpp

# diag
DIAG_DIR = system/src/diag

DIAG_SRC = \
${DIAG_DIR}/trace_impl.c \
${DIAG_DIR}/Trace.c

# cortexm
CORTEXM_DIR = system/src/cortexm

CORTEXM_SRC = \
${CORTEXM_DIR}/exception_handlers.c \
${CORTEXM_DIR}/_initialize_hardware.c \
${CORTEXM_DIR}/_reset_hardware.c

# ---------------------------
# Объектные файлы
# ---------------------------
STM32_PERIPH_OBJ_DIR = ${BIN_PLACE}/stm32f3-stdperiph
CMSIS_OBJ_DIR = ${BIN_PLACE}/cmsis
NEWLIB_OBJ_DIR = ${BIN_PLACE}/newlib
DIAG_OBJ_DIR = ${BIN_PLACE}/diag
CORTEXM_OBJ_DIR = ${BIN_PLACE}/cortexm

STM_STD_LIB_OBJ := \
$(patsubst ${STM32_PERIPH_DIR}/%.c, ${STM32_PERIPH_OBJ_DIR}/%.o,${STM32_PERIPH_SRC}) \
$(patsubst ${CMSIS_DIR}/%.c, ${CMSIS_OBJ_DIR}/%.o,${CMSIS_SRC}) \
$(patsubst ${NEWLIB_DIR}/%.c, ${NEWLIB_OBJ_DIR}/%.o,${NEWLIB_SRC_C}) \
$(patsubst ${NEWLIB_DIR}/%.cpp, ${NEWLIB_OBJ_DIR}/%.opp,${NEWLIB_SRC_CPP}) \
$(patsubst ${DIAG_DIR}/%.c, ${DIAG_OBJ_DIR}/%.o,${DIAG_SRC}) \
$(patsubst ${CORTEXM_DIR}/%.c, ${CORTEXM_OBJ_DIR}/%.o,${CORTEXM_SRC})

# ---------------------------
# Правила
# ---------------------------

rebuild_stm_std_lib: clean_stm_std_lib info_stm_std_lib STM32_STD_LIB
	@echo # ---------------------------
	@echo Rebuilding ${STM_USB_LIB_NAME} completed successfully
	@echo # ---------------------------

# ---------------------------

STM32_STD_LIB: ${STM_STD_LIB_OBJ}

# @echo # ---------------------------
# @echo Building static library ${STM_STD_LIB_NAME}
# @echo ar rcs ${BIN_PLACE}/${STM_STD_LIB_NAME} $${STM_STD_LIB_OBJ}"
# @ar rcs ${BIN_PLACE}/${STM_STD_LIB_NAME} ${STM_STD_LIB_OBJ}
# @echo # ---------------------------

# ---------------------------

${STM32_PERIPH_OBJ_DIR}/%.o: ${STM32_PERIPH_DIR}/%.c
	@echo Compiling $@ from $<
	@${CC} ${GCC_FLAGS} ${DEFINES} ${INCLUDES} $< -o $@

${CMSIS_OBJ_DIR}/%.o: ${CMSIS_DIR}/%.c
	@echo Compiling $@ from $<
	@${CC} ${GCC_FLAGS} ${DEFINES} ${INCLUDES} $< -o $@

${NEWLIB_OBJ_DIR}/%.o: ${NEWLIB_DIR}/%.c
	@echo Compiling $@ from $<
	@${CC} ${GCC_FLAGS} ${DEFINES} ${INCLUDES} $< -o $@

${NEWLIB_OBJ_DIR}/%.opp: ${NEWLIB_DIR}/%.cpp
	@echo Compiling $@ from $<
	@${CP} ${GPP_FLAGS} ${DEFINES} ${INCLUDES} $< -o $@

${DIAG_OBJ_DIR}/%.o: ${DIAG_DIR}/%.c
	@echo Compiling $@ from $<
	@${CC} ${GCC_FLAGS} ${DEFINES} ${INCLUDES} $< -o $@

${CORTEXM_OBJ_DIR}/%.o: ${CORTEXM_DIR}/%.c
	@echo Compiling $@ from $<
	@${CC} ${GCC_FLAGS} ${DEFINES} ${INCLUDES} $< -o $@

# ---------------------------
clean_stm_std_lib:
	@echo # ---------------------------
	@echo Deleting ${STM_STD_LIB_NAME} and its object files
	@rm -f ${STM_STD_LIB_OBJ} ${BIN_PLACE}/${STM_STD_LIB_NAME}
	@echo # ---------------------------

# ---------------------------