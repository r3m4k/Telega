# ---------------------------
# User files
# ---------------------------

SUBDIRS_OBJ += ${USER_OBJ_DIR}
OBJECTS += ${USER_OBJ}

USER_DEFINES =

# ----------------------------
# Исходные файлы пользователя
# ----------------------------

USER_DIR = ${SOURCE_DIR}/user/src

USER_SRC_C = \

USER_SRC_CPP = \
${USER_DIR}/main.cpp \
 
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

__build_user: ${USER_OBJ}

__rebuild_user: __clean_user __build_user

__clean_user:
	@echo Deleting user's object files and generated files
	@rm -f ${USER_OBJ} ${BIN_PLACE}/${BINARY} ${BIN_PLACE}/${PROGRAM_NAME}.hex ${BIN_PLACE}/${PROGRAM_NAME}.map

# --------------------------------