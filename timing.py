import time

class Timing:

    def __init__(self, name=None):
        self.t = time.time()
        self.steps = 1
        self.name = name or 'Timing'

    def step(self, log=False):
        t2 = time.time()
        elapse = t2 - self.t
        if log:
            print(f'{self.name}: Шаг {self.steps} занял {elapse}')
        self.t = t2
        self.steps += 1
        return elapse