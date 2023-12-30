import sys,os,shutil,pydub,termux
class termux_audio():
    def __init__(self):
        self.termux_play=shutil.which('termux-media-player')
        self.termux_record=shutil.which('termux-microphone-record')
        self.termux_api=os.environ.get('TERMUX_API_VERSION')
        err=False
        if not self.termux_api:
            err=True
            print('termux api is not installed.')
        if not self.termux_play:
            err=True
            print('Missing termux-media-player')
        if not self.termux_record:
            err=True
            print('Missing termux-microphone-record')
        lastaction=''
        if not err:
            print('termux OK')
        else:
            lastaction='ERROR'
        buffer=[]
        record_buffer=[]

    def play(self, buffer, fps, channels=1):
        if lastaction=='':
            lastaction='play'

    def play_file(self, fn):
        if lastaction=='':
            lastaction='play'

    def rec(self, size, fps, channels=1):
        if lastaction=='':
            lastaction='record'

    def stop(self):
        if lastaction=='play':
            lastaction=''
        elif lastaction=='record':
            lastaction=''

    def pause(self):
        if lastaction=='play':
            lastaction=''
        elif lastaction=='record':
            self.stop()

    def load(self, fn):
        pass

    def save(self, fn):
        pass

    def merge(buffer, add_buffer, time):
        pass

