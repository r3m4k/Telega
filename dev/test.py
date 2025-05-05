# class A:
#     def __init__(self):
#         self.a = 10
#
#     def printing(self):
#         print(self.a)
#
# class B(A):
#     def __init__(self):
#         super().__init__()
#         self.b = 20
#
#     def printing(self):
#         print(self.b)
#         super().printing()
#
#
# obj = B()
# obj.printing()

import multiprocessing as mp
from time import sleep

def foo(q):
    q.put(f'{q.get()} __ foo')

class Foo:
    def __init__(self):
        pass



if __name__ == '__main__':
    # mp.set_start_method('spawn')
    q = mp.Queue()
    p = mp.Process(target=foo, args=(q,))
    p.start()
    q.put('hello')
    sleep(0.5)
    print(q.get())
    p.join()