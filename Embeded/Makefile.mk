# ---------------------------
# STM_ACC_GIRO_FILTERED
# ---------------------------

include make_args.mk
include make_StmLib.mk
include make_UsbLib.mk
include make_user.mk

# ---------------------------

build_all: info create_dirs STM_LIBS build_user
	@echo # ---------------------------
	@echo The project building is completed
	@echo # ---------------------------

clean_all: clean_user clean_libs
	@echo The project has been cleared

rebuild_all: clean_all build_all

# ---------------------------

linking: info
	@echo Building "${BIN_PLACE}/${BINARY}", Memory card "${BIN_PLACE}/${PROGRAM_NAME}.map"
	@$(CC) ${LINK_FLAGS} -o ${BIN_PLACE}/$(BINARY) $(OBJECTS) ${LIBS}
	@echo $(CC) LINK_FLAGS -o ${BIN_PLACE}/$(BINARY) OBJECTS LIBS
	@echo # ---------------------------
	@echo ${BIN_PLACE}/${BINARY} info:
	@${GCC_PLACE}/bin/arm-none-eabi-size --format=berkeley ${BIN_PLACE}/${BINARY}
	@echo # ---------------------------
	@echo Forming "${BIN_PLACE}/${PROGRAM_NAME}.hex"
	@${GCC_PLACE}/bin/arm-none-eabi-objcopy -O ihex ${BIN_PLACE}/${BINARY} ${BIN_PLACE}/${PROGRAM_NAME}.hex 

# ---------------------------

STM_LIBS: STM32_STD_LIB STM32_USB_LIB
	@echo # ---------------------------
	@echo The building of libraries is completed
	@echo # ---------------------------

clean_libs: clean_stm_std_lib clean_usb_lib

# --------------------------------
# Создание необходимых директорий
# --------------------------------

create_dirs: create_bin_dir create_subdirs
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

create_subdirs: create_bin_dir
	$(foreach dir, ${SUBDIRS_OBJ}, $(call ensure_dir,$(dir)))

create_bin_dir:
	$(call ensure_dir,Debug_Win)

# --------------------------------

info:
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

# ---------------------------