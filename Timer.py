from datetime import datetime as dt

class Timer:
    def __init__(self):
        self.factor=1
        self.startTime=0.0

    def now(self):
        return dt.now().timestamp()

    def start(self, factor=1, offset=0):
        self.factor=factor
        self.startTime=self.now()+offset

    def get(self):
        if self.startTime>0:
            return (self.now()-self.startTime)*self.factor
        else:
            return 0

    def clear(self):
        t=self.get()
        self.startTime=0
        return t


