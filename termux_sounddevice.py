import sys,os,pydub
class termux_sd():
    def __init__(self):
        self.tmux_play=''
        self.tmux_record=''
        lastaction=''

    def play(self, buffer, fps, channels=1):
        if lastaction=='':
            lastaction='play'
        pass

    def rec(self, size, fps, channels=1):
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
