# System imports

# External imports

# User imports
from async_mc_controller.byte_source import AsyncBytesSource
from async_mc_controller.decoding import BaseDecoder
from async_mc_controller.controller import Controller

#########################

class McSession:

    def __init__(self,
                 decoding: BaseDecoder,
                 byte_source: AsyncBytesSource,
                 controller: Controller):

        # Проверим корректность типа переданных параметров
        if not isinstance(decoding, BaseDecoder):
            raise TypeError("decoding должен быть наследником BaseDecoder!")

        if not isinstance(byte_source, AsyncBytesSource):
            raise TypeError("byte_source должен быть наследником AsyncBytesSource!")

        if not isinstance(controller, Controller):
            raise TypeError("controller должен быть наследником Controller!")

        # ------------------------------

        self.decoding: BaseDecoder = decoding
        self.byte_source: AsyncBytesSource = byte_source
        self.controller: Controller = controller

    async def __aenter__(self) -> 'McSession':
        # Вызовем __aenter__ для декодера, com порта и контроллера
        await self.decoding.__aenter__()
        await self.byte_source.__aenter__()
        await self.controller.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        # Вызовем __aexit__ для декодера, com порта и контроллера
        await self.controller.__aexit__(exc_type, exc_val, exc_tb)
        await self.byte_source.__aexit__(exc_type, exc_val, exc_tb)
        await self.decoding.__aexit__(exc_type, exc_val, exc_tb)

        return False

