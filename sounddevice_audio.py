import sounddevice as sd
import numpy as np
from pydub import AudioSegment

class sounddevice_audio():
    def __init__(self):
        return None

    def play(self, buffer, fps, channels=1):
        return sd.play(buffer, fps)

    def stop(self):
        return sd.stop()

    def rec(self, len, fps, channels=1):
        return sd.rec(len, fps, channels=channels)

    def wait(self):
        return sd.wait()

    def save(self, filename, buffer, length, fps, channels):
        # Validate audio data
        if not isinstance(buffer, np.ndarray):
            raise ValueError("audio_data must be a NumPy array")
        if buffer.dtype not in [np.float32, np.int16, np.float64]:
            raise ValueError(f"audio data must be float64, float32 or int16 ({buffer.dtype})")
        buf=buffer
        # Normalize audio data to appropriate range
        if buffer.dtype in [ np.float32, np.float64 ]:
            buf = np.clip(buffer, -1.0, 1.0) * np.iinfo(np.int16).max
        buf = buf.astype(np.int16)
        # Create a pydub AudioSegment from the NumPy array
        if length>0:
            audio_segment = AudioSegment(buf.tobytes(),
                frame_rate=fps, sample_width=16//8, channels=channels)
            audio_segment.export(filename)

