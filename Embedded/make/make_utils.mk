# ---------------------------
# Building utils
# ---------------------------

__info:
	@echo # ---------------------------
	@echo # Building information
	@echo # ---------------------------
	@echo DEFINES: ${DEFINES}
	@echo User_Defines: ${USER_DEFINES}
	@echo Includes: ${INCLUDES}
	@echo GCC_FLAGS: ${GCC_FLAGS}
	@echo GPP_FLAGS: ${GPP_FLAGS}
	@echo LINK_FLAGS: ${LINK_FLAGS}
	@echo LIBS: ${LIBS}
	@echo Obj dirs: ${SUBDIRS_OBJ}
	@echo # ---------------------------


# --------------------------------
# Линковка проекта
# --------------------------------

__linking: __info
	@echo Building "${BIN_PLACE}/${BINARY}", Memory card "${BIN_PLACE}/${PROGRAM_NAME}.map"
	@$(CC) ${LINK_FLAGS} -o ${BIN_PLACE}/$(BINARY) $(OBJECTS) ${LIBS}
	@echo $(CC) LINK_FLAGS -o ${BIN_PLACE}/$(BINARY) OBJECTS LIBS
	@echo # ---------------------------
	@echo ${BIN_PLACE}/${BINARY} info:
	@${GCC_PLACE}/bin/arm-none-eabi-size --format=berkeley ${BIN_PLACE}/${BINARY}
	@echo # ---------------------------
	@echo Forming "${BIN_PLACE}/${PROGRAM_NAME}.hex"
	@${GCC_PLACE}/bin/arm-none-eabi-objcopy -O ihex ${BIN_PLACE}/${BINARY} ${BIN_PLACE}/${PROGRAM_NAME}.hex 


# --------------------------------
# Создание необходимых директорий
# --------------------------------

__create_dirs: __create_bin_dir __create_subdirs
	@echo # ---------------------------
	@echo All directories are created
	@echo # ---------------------------

# Функция для создания директории с проверкой её наличие перед этим
ensure_dir =
ifeq ($(SYSTEM), windows)
	ensure_dir = $(if $(wildcard $(1)/.),$(info Directory "$(1)" already exists),$(shell mkdir $(subst /,\,$(1))))
else ifeq ($(SYSTEM), linux)
	ensure_dir = $(if $(wildcard $(1)/.),$(info Directory "$(1)" already exists),$(shell mkdir $(1)))
endif

__create_subdirs: __create_bin_dir
	$(foreach dir, ${SUBDIRS_OBJ}, $(call ensure_dir,$(dir)))

__create_bin_dir:
	$(call ensure_dir,Debug_Win)


# --------------------------------
