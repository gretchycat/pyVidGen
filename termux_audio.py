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

    def play(self, buffer, fps, channels=1):
        if self.lastaction=='':
            audio_segment = pydub.AudioSegment(buffer,
                frame_rate=fps, sample_width=16//8, channels=channels)
            audio_segment.export(play_temp_file)
            self.play_file(play_temp_file)
            self.lastaction='play'

    def play_file(self, fn):
        termux.Media.play(fn)

    def rec(self, size, fps, channels=1):
        if self.lastaction=='':
            self.rec_file(record_temp_file, fps=fps)
            self.lastaction='record'
        return self.record_buffer

    def rec_file(self, fn, fps=44100):
        termux.Microphone.record(fn, rate=44100)

    def stop(self):
        if self.lastaction=='play':
            termux.Media.stop()
            os.remove(play_temp_file)
            #rm play_temp_file
            self.lastaction=''
        elif self.lastaction=='record':
            termux.Microphone.stop()
            #rm record_temp_file
            self.record_buffer=AudioSegment.from_file(record_temp_file)
            #os.remove(record_temp_file)
            self.lastaction=''

