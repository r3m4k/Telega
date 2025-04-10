from threading import Thread
from time import sleep
from multiprocessing import Process, freeze_support



def pause_print():
    while True:
        sleep(1)
        print('+')


class Foo:
    def __init__(self):
        freeze_support()
        self.process = Process(target=self.infinite_loop, args=(), daemon=True)

    def infinite_loop(self):
        print('Infinite loop')
        while True:
            continue

    def start(self):
        self.process.start()


if __name__ == '__main__':
    foo = Foo()
    foo.start()

    pause_print()