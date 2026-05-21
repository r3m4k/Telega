# System imports

# External imports

# User imports

#############################################

# ------------------------------------------

class FooLogger:
    """
    Класс-заглушка для сохранения семантики логгера через простой print всех сообщений
    """
    def debug(self, msg: str, *args, **kwargs):
        print(msg)

    def info(self, msg: str, *args, **kwargs):
        print(msg)

    def warning(self, msg: str, *args, **kwargs):
        print(msg)

    def error(self, msg: str, *args, **kwargs):
        print(msg)

    def critical(self, msg: str, *args, **kwargs):
        print(msg)

    def exception(self, msg: str, *args, **kwargs):
        print(msg)