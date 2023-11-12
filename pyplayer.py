import sys,os,pydub,time
import sounddevice as sd
from termcontrol import termcontrol, pyteLogger, boxDraw, widgetScreen, widgetProgressBar

STOP=0
PLAY=1
RECORD=2

class pyplayer:
    def __init__(self):
        self.x=1
        self.y=1
        self.status=STOP
        self.fps=48000
        self.startTime=0
        self.length=0
        self.cursor=0

    def interface(self):
        pass

    def play(self):
        if self.status==STOP:
            self.status=PLAY
            self.startTime=time.time()
            sd.play(self.buffer, self.fps)

    def pause(self):
        sd.stop()
        self.length=time.time()-self.startTime
        self.status=STOP

    def record(self):
        if self.status==STOP:
            self.status=RECORD
            self.startTime=time.time()
            self.buffer=sd.rec(self.fps*60*10, self.fps, channels=2)

    def stop(self):
        self.pause()
        self.cursor=0

    def seek(self, time):
        if time<0:
            time=0
        if time>self.length:
            time=self.length
        self.cursor=time

    def get_cursor(self):
        pass

    def next(self):
        pass

    def prev(self):
        pass

    def load(self, filename):
        pass

def main():
    p=pyplayer()
    p.record()
    time.sleep(10)
    p.pause()
    #print(len(p.buffer)/p.fps)
    p.play()
    time.sleep(p.length)
    p.stop()
    p.seek(5)
    p.play()
    time.sleep(p.length-p.cursor)
    p.stop()
    #sd.wait()
    pass

if __name__ == "__main__":
    main()
