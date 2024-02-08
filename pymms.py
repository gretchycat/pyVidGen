import sys,os,pydub,time, random
from datetime import datetime as dt
from optparse import OptionParser
np=None
try:
    from sounddevice_audio import sounddevice_audio
    au=sounddevice_audio()
    import numpy as np
    from scipy import signal as sp
except:
    print('missing sounddevice, numpy or scipy libraries.')
    from termux_audio import termux_audio
    au=termux_audio()
from pydub import AudioSegment

STOP=0
PLAY=1
RECORD=2

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

class pymms:
    def __init__(self):
        self.timer=Timer()
        self.status=STOP
        self.record_fps=24000
        self.record_channels=1
        self.record_sample_width=16//8
        self.cursor=0
        self.selected=0
        self.selected_length=0
        self.record_buffer=[]
        self.stream=None
        self.stop()

    def load(self, filename):
        au.stop()
        self.timer.clear()
        self.cursor=0
        self.selected=0
        self.selected_length=0
        audio=au.load(filename)
        if self.status==PLAY:
            self.stop()
            self.play()
        return {'title':filename, 'length':audio.duration_seconds, 
                'bitrate':audio.frame_rate, 'quality':audio.sample_width, 
                'channels':audio.channels}

    def save(self, filename):
        return au.save(filename)

    def playpause(self):
        if self.status in [ PLAY, RECORD ]:
            self.pause()
        elif self.status==STOP:
            self.play()

    def record(self):
        if self.status==STOP:
            au.setAudioProperties(self.buffer, self.record_fps, self.record_channels)
            self.status=RECORD
            c=self.cursor
            s=int(self.selected)
            sl=int(self.selected_length)
            if sl>0:
                self.pre=self.buffer[:s]
                self.post=self.buffer[s+sl:]
            else:
                self.pre=self.buffer[:c]
                self.post=self.buffer[c:]
            self.timer,start(factor=self.record_fps)
            self.record_buffer=au.rec(self.record_fps*60*10, self.record_fps, channels=self.record_channels)

    def play(self):
        if self.status==STOP and au.audio:
            self.status=PLAY
            self.timer.start(factor=au.audio.frame_rate, offset=-int(self.get_cursor()/au.audio.frame_rate))
            c=self.get_cursor()
            s=int(self.selected)
            sl=int(self.selected_length)
            if sl==0:
                au.play(au.audio.get_array_of_samples()[c:], au.audio.frame_rate)
            else:
                au.play(au.audio.get_array_of_samples()[c:s+sl], au.audio.frame_rate)

    def pause(self):
        if self.status==PLAY:
            self.status=STOP
            au.stop()
            self.timer.clear()
        elif self.status==RECORD:
            self.status=STOP
            au.stop()
            if au.record_audio:
                self.record_buffer=au.record_audio.get_array_of_samples()
                self.record_fps=au.record_audio.frame_rate
                self.record_channels=au.record_audio.channels
            length=int(self.timer.get())
            print(f"Length:{length}")
            record_buffer=self.record_buffer[:length] #truncate buffer
            self.cursor=len(self.pre)+(len(record_buffer))
            self.selected=0
            self.selected_length=0
            if len(self.pre)==0:
                au.setAudio(record_buffer, self.record_fps, self.record_sample_width, self.record_channels)
            else:
                ca=au.concatenate((self.pre, record_buffer))
                au.setAudio(ca, self.record_fps, self.record_sample_width, self.record_channels)
            if len(self.post)>0:
                ca=au.concatenate((au.audio.get_array_of_samples(), self.post))
                au.setAudio(ca, self.record_fps, self.record_sample_width, self.record_channels)
            self.pre, self.post = [], []
            self.record_buffer=[]
            self.timer.clear()

    def length_time(self):
        if au.audio:
            return self.length()/au.audio.frame_rate
        return 0

    def length(self):
        if self.status==RECORD:
            if self.timer.get():
                return int(self.timer.get()+len(au.audio.get_array_of_samples())/self.record_channels)
        else:
            if au.audio:
                return int(len(au.audio.get_array_of_samples())/au.audio.channels)
        return 0

    def stop(self):
        self.pause()
        self.selected=0
        self.selected_length=0
        self.cursor=0
        self.timer.clear()

    def seek_time(self, time):
        if au.audio:
            self.seek(time*au.audio.frame_rate)

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
        if self.cursor>self.length():
            self.cursor=self.length()
        if playing:
            self.play()

    def seekFwd_time(self, time):
        if au.audio:
            self.seekFwd(time*au.audio.frame_rate)

    def seekFwd(self, frames):
        self.seek(self.cursor+frames)

    def seekBack_time(self, time):
        if au.audio:
            self.seekBack(time*au.audio.frame_rate)

    def seekBack(self, frames):
        self.seek(self.cursor-frames)

    def select_time(self, s, sl):
        self.select(s*au.audio.frame_rate, sl*au.audio.frame_rate)

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
                self.buffer=au.concatenate((pre, post))
            else:
                self.buffer=pre
        else:
            if len(post)>0:
                self.buffer=post
            else:
                self.buffer=[]

    def get_cursor(self): #TODO FIXME find authoritative value
        if self.cursor>=self.length() and self.status==PLAY:
            if self.endHandler:
                self.endHandler()
        t=self.timer.get()
        if t>0:
            self.cursor=int(t)
            if self.cursor>self.length():
                self.cursor=self.length()
        if self.status==RECORD:
            return self.cursor+len(self.pre)/self.record_channels
        return self.cursor

    def get_cursor_time(self):
        fps=self.record_fps
        if au.audio:
            au.audio.frame_rate
        if fps:
            return self.get_cursor()/fps #au.audio.frame_rate
        return 0

    def denoise(self):
        au.noiseFilter()

    def normalize(self):
        pass

def main():
    return

if __name__ == "__main__":
    main()
