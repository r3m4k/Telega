# ---------------------------
# Makefile
# ---------------------------

include make_args.mk
include make_utils.mk
include make_StmLib.mk
include make_UsbLib.mk
include make_user.mk

# ---------------------------
# Общие правила сборки
# ---------------------------

build_all: __create_dirs build_libs build_user
	@echo # ---------------------------
	@echo The project building is completed
	@echo # ---------------------------

rebuild_all: clean_all build_all

clean_all: clean_user clean_libs
	@echo The project has been cleared

# ---------------------------
# Правила сборки библиотек
# ---------------------------

build_libs: __build_stm32f3x_spl_lib __build_stm32f3x_usb_lib
	@echo # ---------------------------
	@echo The building of libraries is completed
	@echo # ---------------------------

rebuild_lib: __rebuild_stm_std_lib __rebuild_stm_usb_lib

clean_libs: __clean_stm_std_lib __clean_usb_lib

# ---------------------------------
# Правила сборки фалов пользователя
# ---------------------------------

build_user: __build_user __linking

rebuild_user: __rebuild_user __linking

clean_user: __clean_user

# ---------------------------
