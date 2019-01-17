import time

class Timing:

    def __init__(self, name=None):
        self.t = time.time()
        self.step = 1
        self.name = name

    def log(self):
        t2 = time.time()
        print(f'{self.name}: Шаг {self.step} занял {t2 - self.t}')
        self.t = t2
        self.step += 1