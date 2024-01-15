import sys,os,shutil,pydub,termux
from pydub import AudioSegment

termux_play=shutil.which('termux-media-player')
termux_record=shutil.which('termux-microphone-record')
termux_api=os.environ.get('TERMUX_API_VERSION')
record_temp_file='._rec.wav'
play_temp_file='._play.wav'
err=False
if not termux_api:
    err=True
    print('termux api is not installed.')
if not termux_play:
    err=True
    print('Missing termux-media-player')
if not termux_record:
    err=True
    print('Missing termux-microphone-record')
if not err:
    print('termux OK')

else:
    lastaction='ERROR'
 
class termux_audio():
    def __init__(self):
        self.lastaction=''
        self.buffer=[]
        self.record_buffer=[]
        self.fps=24000
        self.channels=1

    def play_file(self, fn):
        termux.Media.play(fn)

    def rec_file(self, fn, fps=24000):
        self.fps=fps
        termux.Microphone.record(fn, rate=fps)

    def play(self, buffer, fps, channels=1):
        if self.lastaction=='':
            audio_segment = pydub.AudioSegment(buffer,
                frame_rate=fps, sample_width=16//8, channels=channels)
            audio_segment.export(play_temp_file)
            self.play_file(play_temp_file)
            self.lastaction='play'

    def rec(self, size, fps, channels=1):
        if self.lastaction=='':
            self.rec_file(record_temp_file, fps=fps)
            self.lastaction='record'
        return self.record_buffer

    def stop(self):
        if self.lastaction=='play':
            termux.Media.control("stop")
            os.remove(play_temp_file)
            self.lastaction=''
        elif self.lastaction=='record':
            termux.Microphone.stop()
            self.record_buffer=AudioSegment.from_file(record_temp_file)
            #os.remove(record_temp_file)
            self.lastaction=''

    def save(self, filename, buffer, length):
        pass

    def setAudioProperties(self, buffer, fps, channels):
        self.buffer=buffer
        self.fps=fps
        self.channels=channels

    def concatenate(self, buf1, buf2):
        return buf1+buf2

    def noiseFilter(self):
        return self.bufffer
