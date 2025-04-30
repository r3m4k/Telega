class A:
    def __init__(self):
        self.a = 10

    def printing(self):
        print(self.a)

class B(A):
    def __init__(self):
        super().__init__()
        self.b = 20

    def printing(self):
        print(self.b)
        super().printing()


obj = B()
obj.printing()
