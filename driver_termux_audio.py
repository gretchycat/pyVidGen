import sys,os,shutil,pydub
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
else:
    import termux
if not termux_play:
    err=True
    print('Missing termux-media-player')
if not termux_record:
    err=True
    print('Missing termux-microphone-record')
if not err:
    print('termux OK')

 
from pydub import AudioSegment

from driver_audio import driver_audio

class driver_termux_audio(driver_audio):
    def __init__(self):
        super().__init__()
        self.lastaction=''

    def play_file(self, fn):
        termux.Media.play(fn)

    def rec_file(self, fn, fps=24000):
        self.fps=fps
        termux.Microphone.record(fn, rate=fps)

    def play(self, start=0, end=0):
        super().play(start=start, end=end)
        buffer=self.audio.get_array_of_samples()
        if self.lastaction=='':
            if end==0:
                buf=buffer[int(start):]
            else:
                buf=buffer[int(start):int(end)]
            audio_segment = pydub.AudioSegment(buf,
                frame_rate=self.audio.frame_rate, 
                sample_width=self.audio.sample_width, 
                channels=self.audio.channels)
            audio_segment.export(play_temp_file)
            self.lastaction='play'
            self.play_file(play_temp_file)

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
        super().stop()

    def rec(self):
        super().rec()
        if self.lastaction=='':
            self.rec_file(record_temp_file, fps=self.fps)
            self.lastaction='record'
        return self.record_buffer

    def wait(self):
        super().wait()
        return sd.wait()

    def setAudio(self, buffer, fps, sample_width, channels):
        buf=buffer
        # Create a pydub AudioSegment 
        return AudioSegment(buf.get_array_of_samples().tobytes(),
            frame_rate=fps, sample_width=sample_width, channels=channels)


