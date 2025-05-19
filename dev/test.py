class A:
    def a(self):
        print('Class A')
        self.b()

    def b(self):
        pass

class B(A):
    def b(self):
        print('Class B')


tmp = B
obj = tmp()
obj.a()