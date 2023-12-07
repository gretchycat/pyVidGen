import sys,os,pydub,time, random
from optparse import OptionParser
import sounddevice as sd
import numpy as np
from pydub import AudioSegment

STOP=0
PLAY=1
RECORD=2

class pyplayer:
    def __init__(self):
        self.x=1
        self.y=1
        self.status=STOP
        self.fps=48000
        self.channels=1
        self.cursor=0
        self.startTime=0
        self.selected=0
        self.selected_length=0
        self.buffer=[]
        self.record_buffer=[]
        self.stream=None
        self.stop()

    def load(self, filename):
        sd.stop()
        self.cursor=0
        audio=AudioSegment.from_file(filename)
        audio_array=np.array(audio.get_array_of_samples())
        self.fps=audio.frame_rate
        self.channels=audio.channels
        self.sample_width=0 #audio.sample_width
        self.buffer=audio_array
        if self.status==PLAY:
            sd.play(self.buffer, self.fps)
        return {'title':filename, 'length':audio.duration_seconds, 'bitrate':self.fps, 'quality':self.sample_width, 'channels':self.channels}

    def save(self, filename):
        pass

    def callback(self, indata, frames, time, status):
        self.cursor=frames
        self.time=time

    def playpause(self):
        if self.status in [ PLAY, RECORD ]:
            self.pause()
        elif self.status==STOP:
            self.play()

    def play(self):
        if self.status==STOP:
            self.status=PLAY
            self.startTime=time.time()
            c=self.get_cursor()
            s=int(self.selected)
            sl=int(self.selected_length)
            if sl==0:
                sd.play(self.buffer[c:], self.fps)
            else:
                sd.play(self.buffer[c:s+sl], self.fps)

    def pause(self):
        if self.status==PLAY:
            self.status=STOP
            sd.stop()
        elif self.status==RECORD:
            self.status=STOP
            sd.stop()
            length=(time.time()-self.startTime)
            record_buffer=self.record_buffer[:int(length*self.fps)]
            self.startTime=0
            c=self.get_cursor()
            s=int(self.selected*self.fps)
            sl=int(self.selected_length*self.fps)
            pre, post = [], []
            if sl>0:
                pre=self.buffer[:s]
                post=self.buffer[s+sl:]
            else:
                pre=self.buffer[:c]
                post=self.buffer[c:]
            self.cursor=s+(len(record_buffer))
            self.selected=0
            self.selected_length=0
            if len(pre)==0:
                self.buffer=record_buffer
            else:
                self.buffer=np.concatenate((pre, record_buffer))
            if len(post)>0:
                self.buffer=np.concatenate((self.buffer, post))
            self.record_buffer=[]

    def length_time(self):
        return self.length/self.fps

    def length(self):
        return len(self.buffer)

    def stop(self):
        self.pause()
        self.selected=0
        self.cursor=0
        self.startTime=0

    def record(self):
        if self.status==STOP:
            self.status=RECORD
            self.startTime=time.time()
            self.record_buffer=sd.rec(self.fps*60*10, self.fps, channels=2)

    def seek_time(self, time):
        self.seek(time*self.fps)

    def seek(self, frame):
        playing=self.status==PLAY
        if playing:
            self.pause()
        if self.status==STOP:
            if frame<0:
                frame=0
            if frame>self.length():
                time=self.length()
            self.cursor=frame
        if playing:
            self.play()

    def seekFwd_time(self, time):
        self.seekFwd(time*self.fps)

    def seekFwd(self, frames):
        self.seek(self.cursor-frames)

    def seekBack_time(self, time):
        self.seekBack(time*self.fps)

    def seekBack(self, frames):
        self.seek(self.cursor+frames)

    def select_time(self, s, sl):
        self.select(s*self.fps, sl*self.fps)

    def select(self, s, sl):
        if self.status==STOP:
            if s<0:
                s=0
            if sl<0:
                sl=0
            if sl>0:
                if s<self.length():
                    s=self.length()
                if s+sl>self.length():
                    sl=self.length()-s
                self.selected=s
                self.selected_length=sl

    def clear(self):
        if self.selected_length==0:
            self.buffer=[]
        else:
            self.clear_selected()

    def clear_selected(self):
        self.seek(self.selected)
        s=int(self.selected)
        sl=int(self.selected_length
               )
        pre=self.buffer[:s]
        post=self.buffer[s+sl:]
        if len(pre)>0:
            if len(post)>0:
                self.buffer=np.concatenate((pre, post))
            else:
                self.buffer=pre
        else:
            if len(post)>0:
                self.buffer=post
            else:
                self.buffer=[]

    def get_cursor(self): #TODO FIXME 
        self.cursor=time.time()-self.startTime
        if self.cursor>self.length():
            self.cursor=self.length()
            #self.pause()
        return int(self.cursor*self.fps)

    def get_cursor_time(self):
        return self.get_cursor()/self.fps

def main():
    return

if __name__ == "__main__":
    main()
