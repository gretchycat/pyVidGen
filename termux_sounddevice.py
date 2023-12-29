import sys,os,pydub
class tsd():
    def __init__(self):
        self.tmux_play=''
        self.tmux_record=''
        lastaction=''

    def play(self, buffer, fps, channels=1):
        if lastaction=='':
            lastaction='play'
        pass

    def record(self, size, fps, channels=1):
        if lastaction=='':
            lastaction='record'
        pass

    def stop(self):
        if lastaction=='play':
            pass
        elif lastaction=='record':
            pass
        lastaction=''
        pass
