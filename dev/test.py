from random import random

class A:
    def __init__(self):
        self.val = random()

    def a(self):
        print('Class A')
        self.b()

    def b(self):
        pass

class B(A):
    def b(self):
        print(f'Class B, val = {self.val}')

class C(A):
    def b(self):
        print(f'Class C, val = {self.val}')


b = B()
b.a()

c = C()
c.a()