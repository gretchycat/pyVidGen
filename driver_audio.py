from Timer import Timer

from pydub import AudioSegment

STOP=0
PLAY=1
RECORD=2

class driver_audio():
    def __init__(self):
        self.endHandler=None
        self.status=STOP
        self.timer=Timer()
        self.cursor=0
        self.fps=44100
        self.channels=1
        self.sample_width=16//8
        self.record_buffer=None
        self.audio=None
        self.audio_start=0
        self.record_audio=None
        return None

    def load(self, filename):
        self.timer.clear()
        self.audio=AudioSegment.from_file(filename)
        self.setAudioProperties(fps=self.audio.frame_rate,
            channels=self.audio.channels, sample_width=self.audio.sample_width)
        self.audio_start=0
        return self.audio

    def play(self, start=0, end=0):
        self.status=PLAY
        #buffer=self.audio.get_array_of_samples()
        self.audio_start=self.get_cursor()
        self.timer.start(factor=self.audio.frame_rate, offset=-int(self.get_cursor()/self.audio.frame_rate))
        if end==0:
            pass
            #return sd.play(buffer[int(start):], self.audio.frame_rate)
        #return sd.play(buffer[int(start):int(end)], self.audio.frame_rate)

    def stop(self):
        #sd.stop()
        self.status=STOP
        if self.record_buffer is not None:
            frames=int(self.timer.get())
            self.record_audio=self.setAudio(self.record_buffer[:frames],
                self.fps,
                self.sample_width, self.channels)
            record_buffer=None
        self.timer.clear()
        self.audio_start=0

    def rec(self):
        self.status=RECORD
        self.audio_start=self.get_cursor()
        self.timer.start(factor=self.fps)
        len=self.fps*self.channels*60*10
        self.record_audio=None
        #self.record_buffer=sd.rec(len, self.fps, channels=self.channels)

    def wait(self):
        pass
        #return sd.wait()

    def save(self, filename):
        # Validate audio data
        if self.audio:
            self.audio.export(filename)

    def length_time(self):
        if self.audio:
            return self.length()/self.audio.frame_rate
        return 0

    def length(self):
        if self.audio:
            if self.status==RECORD:
                if self.timer.get():
                    return int(self.timer.get()+self.audio.frame_count())
            else:
                return int(self.audio.frame_count())
        else:
            if self.status==RECORD:
                return int(self.timer.get())
        return 0

    def get_cursor(self): #TODO FIXME find authoritative value
        if self.cursor>=self.length() and self.status==PLAY:
            if self.endHandler:
                self.endHandler()
        t=int(self.timer.get())
        if t>0:
            self.cursor=t
            if self.status==RECORD:
                self.cursor = t+self.audio_start
            if self.cursor>self.length():
                self.cursor=self.length()
        return self.cursor

    def get_cursor_time(self):
        fps=self.fps
        if self.audio:
            fps=self.audio.frame_rate
        if fps:
            return self.get_cursor()/fps #au.audio.frame_rate
        return 0

    def setAudio(self, buffer, fps, sample_width, channels):
        #return AudioSegment from buffer
        raise NotImplementedError(f"you must implement setAudio in {type(self)}")

    def setAudioProperties(self, fps=24000, channels=1, sample_width=16//8):
        self.fps=fps
        self.sample_width=sample_width
        self.channels=channels

    def concatenate(self, audiolist):
        full=None
        for a in audiolist:
            if full==None:
                full=a
            else:full=full+a
        return full

    def crop(self, start=None, end=None):
        fps=self.fps
        channels=self.channels
        sample_width=16//8
        if self.audio:
            fps=self.audio.frame_rate
            channels=self.audio.channels
            sample_width=self.audio.sample_width
        else:
            return None
        sf,ef=None, None
        if start is not None:
            sf=int(start)
        if end is not None:
            ef=int(end)
        if sf is not None and ef is not None:
            clip_frames=self.audio.get_array_of_samples()[sf:ef]
        elif sf is not None:
            clip_frames=self.audio.get_array_of_samples()[sf:]
        elif ef is not None:
            clip_frames=self.audio.get_array_of_samples()[:ef]
        else:
            clip_frames=self.audio.get_array_of_samples()
        #convert to AudioSegment
        audio_segment = AudioSegment(clip_frames.tobytes(), frame_rate=fps, 
            sample_width=sample_width, channels=channels)
        if audio_segment.frame_count()>0:
            return audio_segment
        return None

