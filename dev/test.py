from multiprocessing import Process, Queue
from multiprocessing.managers import NamespaceProxy, BaseManager

from random import random
from time import sleep

class MyManager(BaseManager):
    pass

class MyAwesomeClass:
    def __init__(self):
         pass

    def  __del__(self):
        print('Завершение процесса')

    def working(self, data_container: Queue):
        while True:
            data_container.put(str(random() * 100))
            sleep(0.1)

class MyAwesomeClassProxy(NamespaceProxy):
    pass


class Decoder:
    def __init__(self):
        pass

    def reading(self, data_collector: Queue):
        while True:
            if not data_collector.empty():
                data = data_collector.get()
                print(type(data), data)

class DecoderProxy(NamespaceProxy):
    pass


class Foo:
    MyManager.register('MyAwesomeClass', MyAwesomeClass, MyAwesomeClassProxy)
    MyManager.register('DecoderRegisteres', Decoder, DecoderProxy)

    def __init__(self):
        self.M = MyManager()
        self.M.start()
        self.MAC = self.M.MyAwesomeClass()
        self.decoder = self.M.DecoderRegisteres()
        self.queue = Queue()

        self.p1 = Process(target=self.MAC.working, args=(self.queue, ), daemon=True)
        self.p2 = Process(target=self.decoder.reading, args=(self.queue, ), daemon=True)


    def start_filling(self):
        self.p1.start()

    def start_reading(self):
        self.p2.start()

    def stop(self):
        self.p1.terminate()
        self.p1.join()

        self.p2.terminate()
        self.p2.join()