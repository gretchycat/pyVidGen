import sys,os,pydub,time, random
from optparse import OptionParser
np=None
try:
    from driver_sounddevice_audio import driver_sounddevice_audio
    au=driver_sounddevice_audio()
    import numpy as np
    from scipy import signal as sp
except:
    print('missing sounddevice, numpy or scipy libraries.')
    from driver_termux_audio import driver_termux_audio
    au=driver_termux_audio()
from pydub import AudioSegment

STOP=0
PLAY=1
RECORD=2

class pymms:
    def __init__(self):
        self.record_fps=24000
        self.record_channels=1
        self.record_sample_width=16//8
        self.selected=0
        self.selected_length=0
        self.stop()
        self.au=au

    def load(self, filename):
        self.stop()
        audio=au.load(filename)
        return {'title':filename, 'length':audio.duration_seconds, 
                'bitrate':audio.frame_rate, 'quality':audio.sample_width, 
                'channels':audio.channels}

    def save(self, filename):
        return au.save(filename)

    def playpause(self):
        if au.status in [ PLAY, RECORD ]:
            self.pause()
        elif au.status==STOP:
            self.play()

    def record(self):
        if au.status==STOP:
            au.setAudioProperties(fps=self.record_fps,
                channels=self.record_channels,
                sample_width=self.record_sample_width)
            c=au.cursor
            print(f'\nCursor={c/self.record_fps}')
            s=int(self.selected)
            sl=int(self.selected_length)
            if sl>0:
                self.pre=au.crop(None, s)
                self.post=au.crop(s+sl, None)
            else:
                self.pre=au.crop(None, c)
                self.post=au.crop(c, None) 
            if self.pre:
                print('\npre exists.')
            if self.post:
                print('post exists')
            au.rec()

    def play(self):
        if au.status==STOP and au.audio:
            c=self.get_cursor()
            s=int(self.selected)
            sl=int(self.selected_length)
            if sl==0:
                au.play(start=c)
            else:
                au.play(start=c, end=s+sl)

    def pause(self):
        if au.status==PLAY:
            au.stop()
        elif au.status==RECORD:
            length=int(au.timer.get())
            au.stop()
            if au.record_audio:
                #au.record_audio.get_array_of_samples()
                self.record_fps=au.record_audio.frame_rate
                self.record_sample_width=au.record_audio.sample_width
                self.record_channels=au.record_audio.channels
            else:
                print(f'\n\nMissing record audio')
                return
            print(f"Length:{length}")
            if self.pre:
                au.cursor=self.pre.frame_count()+au.record_audio.frame_count()
            else:
                au.cursor=au.record_audio.frame_count()
            self.selected=0
            self.selected_length=0
            ca=None
            if self.pre and self.post:
                print('\n\n\npre+rec+post')
                ca=au.concatenate((self.pre, au.record_audio, self.post))
            elif self.pre:
                ca=au.concatenate((self.pre, au.record_audio))
                print('\n\n\npre+rec     ')
            elif self.post:
                ca=au.concatenate((au.record_audio, self.post))
                print('\n\n\nrec+post    ')
            else:
                ca=au.record_audio
                print('\n\n\nrec         ')
            au.audio=ca
            self.pre, self.post = None, None

    def stop(self):
        self.pause()
        self.selected=0
        self.selected_length=0
        au.cursor=0

    def seek_time(self, time):
        if au.audio:
            self.seek(time*au.audio.frame_rate)

    def seek(self, frame):
        playing=au.status==PLAY
        if playing:
            self.pause()
        l=au.length()
        if au.status==STOP:
            if frame<0:
                frame=0
            if frame>l:
                time=l
            au.cursor=frame
        if au.cursor>l:
            au.cursor=l
        if playing:
            self.play()

    def seekFwd_time(self, time):
        if au.audio:
            self.seekFwd(time*au.audio.frame_rate)

    def seekFwd(self, frames):
        self.seek(au.cursor+frames)

    def seekBack_time(self, time):
        if au.audio:
            self.seekBack(time*au.audio.frame_rate)

    def seekBack(self, frames):
        self.seek(au.cursor-frames)

    def select_time(self, s, sl):
        self.select(s*au.audio.frame_rate, sl*au.audio.frame_rate)

    def select(self, s, sl):
        if au.status==STOP:
            if s<0:
                s=0
            if sl<0:
                sl=0
            if sl>0:
                l=au.length()
                if s<l:
                    s=l
                if s+sl>l:
                    sl=l-s
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
        sl=int(self.selected_length)
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

    def get_cursor_time(self):
        return au.get_cursor_time()

    def get_cursor(self):
        return au.get_cursor()

    def length(self):
        return au.length()

    def length_time(self):
        return au.length_time()

    def denoise(self):
        au.noiseFilter()

    def normalize(self):
        pass

def main():
    return

if __name__ == "__main__":
    main()
