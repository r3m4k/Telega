import sys
from test2 import test

# Open file for writing
f = open("output.txt", "w")

# Redirect stdout and stderr to file
sys.stdout = f
sys.stderr = f

test()

# Close file
f.close()





"""
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
        
"""


"""
match stage:
                case int(Want7E):
                    if bt == 126:
                        stage = WantE7
                        con_sum = bt
                        # Обнулим накопленные значения
                        index = 0
                        data = {}
                        bytes_buffer = []
                    else:
                        stage = Want7E

                case int(WantE7):
                    if bt == 231:
                        stage = WantSize
                        con_sum += bt
                    else:
                        stage = Want7E

                case int(WantSize):
                    size = bt
                    con_sum += bt
                    stage = WantFormat

                case int(WantFormat):
                    _ = bt
                    con_sum += bt
                    stage = WantPacketBody

                case int(WantPacketBody):
                    if index < size:
                        index += 1
                        bytes_buffer.append(bt)

                    if index == size:
                        stage = WantConSum

                case int(WantConSum):
                    Con_Sum = bt
                    # Сравним Con_Sum и младшие 8 бит con_sum
                    if Con_Sum == (con_sum & 255):
                        for i in range(size // 2):
                            # Сохраним полученные данные, полученные в LittleEndianMode в словарь
                            value = self.mod_code(bytes_buffer[2 * i], bytes_buffer[2 * i + 1])
                            if index in range(1, size // 2 - 1):
                                # Для Acc_XYZ и Gyro_XYZ
                                data[titles[i]] = value / 1000
                            else:
                                # Для Time и Temp
                                data[titles[i]] = value / 100
                        output_queue.put(data)

                    else:
                        stage = Want7E
"""