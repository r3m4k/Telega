import enum

class Decoder:
    STM_Stages = enum.Enum(
        value='STM_Stages',
        names=['Want7E', 'self.Stages.WantE7', 'self.Stages.WantSize', 'self.Stages.WantFormat',
               'self.Stages.WantPacketBody', 'self.Stages.WantConSum']
    )

    def __init__(self):
        pass

    def foo(self):
        stages = self.STM_Stages
        # print('Member: {}'.format(stages.new))

        print(stages.Want7E)

        print('\nAll members:')
        for status in stages:
            print('{:15} = {}'.format(status.name, status.value))


decoder = Decoder()
decoder.foo()