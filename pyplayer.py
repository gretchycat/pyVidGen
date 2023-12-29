import sys,os,pydub,time, random
from datetime import datetime as dt
from optparse import OptionParser
try:
    import sounddevice as sd
except:
    print('missing sounddevice library.')
try:
    import numpy as np
except:
    print('missing numpy library.')
from pydub import AudioSegment

STOP=0
PLAY=1
RECORD=2

class pyplayer:
    def __init__(self):
        self.x=1
        self.y=1
        self.yy=1
        self.status=STOP
        self.fps=48000
        self.factor=self.fps
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
        self.timer_clear()
        self.cursor=0
        self.selected=0
        self.selected_length=0
        self.record_buffer=[]
        audio=AudioSegment.from_file(filename)
        audio_array=np.array(audio.get_array_of_samples())
        self.fps=audio.frame_rate
        self.factor=self.fps
        self.channels=audio.channels
        self.sample_width=0 #audio.sample_width
        self.buffer=audio_array
        if self.status==PLAY:
            self.stop()
            self.play()
        return {'title':filename, 'length':audio.duration_seconds, 'bitrate':self.fps, 'quality':self.sample_width, 'channels':self.channels}

    def timer_now(self):
        return dt.now().timestamp()

    def timer_start(self, factor=1, offset=0):
        self.factor=factor
        self.startTime=self.timer_now()+offset

    def timer_get(self):
        if self.startTime>0:
            return (self.timer_now()-self.startTime)*self.factor
        else:
            return 0

    def timer_clear(self):
        t=self.timer_get()
        self.startTime=0
        return t

    def save(self, filename):
        # Validate audio data
        if not isinstance(self.buffer, np.ndarray):
            raise ValueError("audio_data must be a NumPy array")
        if self.buffer.dtype not in [np.float32, np.int16]:
            raise ValueError("audio data must be float32 or int16")
        buf=self.buffer
        # Normalize audio data to appropriate range
        if self.buffer.dtype == np.float32:
            buf = np.clip(self.buffer, -1.0, 1.0) * np.iinfo(np.int16).max
        #else:
        buf = buf.astype(np.int16)

        # Create a pydub AudioSegment from the NumPy array
        if self.length():
            audio_segment = pydub.AudioSegment(buf.tobytes(),
                frame_rate=self.fps, sample_width=16//8, channels=self.channels)
            audio_segment.export(filename)

        pass

    def callback(self, indata, frames, time, status):
        self.cursor=frames
        self.time=time

    def playpause(self):
        if self.status in [ PLAY, RECORD ]:
            self.pause()
        elif self.status==STOP:
            self.play()

    def record(self):
        if self.status==STOP:
            self.status=RECORD
            self.timer_start(factor=self.fps)
            c=self.cursor
            s=int(self.selected)
            sl=int(self.selected_length)
            if sl>0:
                self.pre=self.buffer[:s]
                self.post=self.buffer[s+sl:]
            else:
                self.pre=self.buffer[:c]
                self.post=self.buffer[c:]
            self.record_buffer=sd.rec(self.fps*60*10, self.fps, channels=self.channels)

    def play(self):
        if self.status==STOP:
            self.status=PLAY
            self.timer_start(factor=self.fps, offset=-int(self.get_cursor()/self.fps))
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
            self.timer_clear()
        elif self.status==RECORD:
            self.status=STOP
            sd.stop()
            length=int(self.timer_get())
            record_buffer=self.record_buffer[:length] #truncate buffer
            self.cursor=len(self.pre)+(len(record_buffer))
            self.selected=0
            self.selected_length=0
            if len(self.pre)==0:
                self.buffer=record_buffer
            else:
                self.buffer=np.concatenate((self.pre, record_buffer))
            if len(self.post)>0:
                self.buffer=np.concatenate((self.buffer, self.post))
            self.pre, self.post = [], []
            self.record_buffer=[]
            self.timer_clear()

    def length_time(self):
        return self.length()/self.fps

    def length(self):
        if self.status==RECORD:
            if self.timer_get():
                return int(self.timer_get()+len(self.buffer)/self.channels)
            return 0
        else:
            return int(len(self.buffer)/self.channels)

    def stop(self):
        self.pause()
        self.selected=0
        self.selected_length=0
        self.cursor=0
        self.timer_clear()

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
        if self.cursor>self.length():
            self.cursor=self.length()
        if playing:
            self.play()

    def seekFwd_time(self, time):
        self.seekFwd(time*self.fps)

    def seekFwd(self, frames):
        self.seek(self.cursor+frames)

    def seekBack_time(self, time):
        self.seekBack(time*self.fps)

    def seekBack(self, frames):
        self.seek(self.cursor-frames)

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

    def get_cursor(self): #TODO FIXME find authoritative value
        if self.cursor>=self.length() and self.status==PLAY:
            if self.endHandler:
                self.endHandler()
        t=self.timer_get()
        if t>0:
            self.cursor=int(t)
            if self.cursor>self.length():
                self.cursor=self.length()
        if self.status==RECORD:
            return self.cursor+len(self.pre)/self.channels
        return self.cursor

    def get_cursor_time(self):
        return self.get_cursor()/self.fps

def main():
    return

if __name__ == "__main__":
    main()
