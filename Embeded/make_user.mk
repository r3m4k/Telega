# ---------------------------
# User files
# ---------------------------

SUBDIRS_OBJ += ${USER_OBJ_DIR}
OBJECTS += ${USER_OBJ}

USER_DEFINES =

# ----------------------------
# Исходные файлы пользователя
# ----------------------------

USER_DIR = src

USER_SRC_C = \
${USER_DIR}/Sensors.c \
${USER_DIR}/_write.c

USER_SRC_CPP = \
${USER_DIR}/main.cpp \
${USER_DIR}/Drv_Gpio.cpp \
${USER_DIR}/Drv_Uart.cpp \
${USER_DIR}/COM_IO.cpp
 
# ----------------------------
# Объектные файлы пользователя
# ----------------------------

USER_OBJ_DIR = ${BIN_PLACE}/user
USER_OBJ = \
$(patsubst ${USER_DIR}/%.c, ${USER_OBJ_DIR}/%.o,${USER_SRC_C}) \
$(patsubst ${USER_DIR}/%.cpp, ${USER_OBJ_DIR}/%.opp,${USER_SRC_CPP}) \

# ----------------------------

${USER_OBJ_DIR}/%.o: ${USER_DIR}/%.c
	@echo Compiling $@ from $<
	@${CC} ${GCC_FLAGS} ${DEFINES} ${USER_DEFINES} ${INCLUDES} $< -o $@

${USER_OBJ_DIR}/%.opp: ${USER_DIR}/%.cpp
	@echo Compiling $@ from $<
	@${CP} ${GPP_FLAGS} ${DEFINES} ${USER_DEFINES} ${INCLUDES} $< -o $@

# ---------------------------

build_user: ${USER_OBJ} linking

clean_user:
	@echo Deleting user's object files and generated files
	@rm -f ${USER_OBJ} ${BIN_PLACE}/${BINARY} ${BIN_PLACE}/${PROGRAM_NAME}.hex ${BIN_PLACE}/${PROGRAM_NAME}.map

rebuild_user: clean_user build_user

# --------------------------------