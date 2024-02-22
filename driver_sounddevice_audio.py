try:
    import sounddevice as sd
    import numpy as np
except:
    pass
from pydub import AudioSegment

from driver_audio import driver_audio

class driver_sounddevice_audio(driver_audio):
    def __init__(self):
        super().__init__()

    def play(self, start=0, end=0):
        super().play(start=start, end=end)
        buffer=self.audio.get_array_of_samples()
        if end==0:
            return sd.play(buffer[int(start):], self.audio.frame_rate)
        return sd.play(buffer[int(start):int(end)], self.audio.frame_rate)

    def stop(self):
        sd.stop()
        super().stop()

    def rec(self):
        super().rec()
        len=self.fps*self.channels*60*10
        self.record_buffer=sd.rec(len, self.fps, channels=self.channels)

    def wait(self):
        super().wait()
        return sd.wait()

    def setAudio(self, buffer, fps, sample_width, channels):
        if not isinstance(buffer, np.ndarray):
            return
            raise ValueError("audio_data must be a NumPy array")
        if buffer.dtype not in [np.float32, np.int16, np.float64]:
            return
            raise ValueError(f"audio data must be float64, float32 or int16 ({buffer.dtype})")
        buf=buffer
        # Normalize audio data to appropriate range
        if buffer.dtype in [ np.float32, np.float64 ]:
            buf = np.clip(buffer, -1.0, 1.0) * np.iinfo(np.int16).max
        buf = buf.astype(np.int16)
        # Create a pydub AudioSegment from the NumPy array
        return AudioSegment(buf.tobytes(),
            frame_rate=fps, sample_width=sample_width, channels=channels)


