from Timer import Timer

try:
    import sounddevice as sd
    import numpy as np
except:
    pass

from pydub import AudioSegment

STOP=0
PLAY=1
RECORD=2

class sounddevice_audio():
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
        buffer=self.audio.get_array_of_samples()
        self.audio_start=self.get_cursor()
        self.timer.start(factor=self.audio.frame_rate, offset=-int(self.get_cursor()/self.audio.frame_rate))
        if end==0:
            return sd.play(buffer[int(start):], self.audio.frame_rate)
        return sd.play(buffer[int(start):int(end)], self.audio.frame_rate)

    def stop(self):
        self.status=STOP
        if self.record_buffer is not None:
            frames=int(self.timer.get())
            self.record_audio=self.setAudio(self.record_buffer[:frames], self.fps, 
                self.sample_width, self.channels)
            record_buffer=None
        self.timer.clear()
        self.audio_start=0
        return sd.stop()

    def rec(self):
        self.status=RECORD
        self.audio_start=self.get_cursor()
        self.timer.start(factor=self.fps)
        len=self.fps*self.channels*60*10
        self.record_audio=None
        self.record_buffer=sd.rec(len, self.fps, channels=self.channels)

    def wait(self):
        return sd.wait()

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

    def noiseFilter(self):
        #self.buffer = audacity_like_filter(self.buffer, self.fps)
        self.buffer = ideal_bandpass_filter(self.buffer, 100, 5000, self.fps).real
        #self.buffer = butterworth_filter(self.buffer, 500, 2, self.fps)
        return self.buffer

def ideal_bandpass_filter(data, f_low, f_high, sample_rate):
    fft_data = np.fft.fft(data)    # Transform data to frequency domain
    fft_data[0] *= 0.5    # Handle DC component
    fft_data[f_low//sample_rate:f_high//sample_rate] = 1    # Pass frequencies in the range
    fft_data[f_high//sample_rate:] = 0    # Attenuate frequencies above the range
    return np.fft.ifft(fft_data).astype('float32')    # Transform back to time domain

def butterworth_filter(data, f_cutoff, order, sample_rate, btype="low"):
    nyq = 0.5 * sample_rate
    Wn = f_cutoff / nyq
    b, a = sp.butter(order, Wn, btype=btype)
    filtered_data, _ = sp.filtfilt(b, a, data)
    return filtered_data.astype('float32')

def get_noise_profile(data, sample_rate, floor_margin=1/3, segment_factor=1):
    """
    Extracts a smoothed noise profile from an audio data array.

    Args:
        data: A NumPy array containing the audio data (float32 or int16).
        sample_rate: The sampling rate of the audio (Hz).
        floor_margin: The percentage margin (0-100) added to the global noise floor threshold.
        segment_factor: A factor dividing the sample_rate to determine the segment size (e.g., 10 for 100ms at 10kHz).

    Returns:
        noise_profile: A NumPy array containing the smoothed noise profile.
    """

    # Pass 1: Find global noise floor threshold and peak
    segment_length = int(sample_rate * segment_factor)
    segment_peaks = [np.max(np.abs(data[i:i+segment_length])) for i in range(0, len(data), segment_length) if np.max(np.abs(data[i:i+segment_length])) > 0.0]
    peak=np.max(segment_peaks)
    if peak==0:
        return []
    global_noise_floor = np.min(segment_peaks) * (1+floor_margin)
    print(segment_peaks/peak)
    print('floor:',global_noise_floor/peak)
    print('peak: ',peak)

    # Pass 2: Extract and smooth noise profile segments
    noise_profile = np.empty(shape=(0,data.shape[1]))
    for i in range(0, len(data), segment_length):
        segment = data[i:i+segment_length]
        print('segment', segment.shape, np.max(np.abs(segment))/peak)
        if np.max(np.abs(segment)) <= global_noise_floor:
            # Apply windowing (e.g., Hann) for smoothing
            window = np.hanning(segment.shape[0])[:,None]
            smoothed_segment = segment * window
            print('    segment', segment.shape, smoothed_segment.shape)
            if len(noise_profile)==0:
                noise_profile=smoothed_segment
            else:
                np.concatenate((noise_profile, smoothed_segment))
    if len(noise_profile)<sample_rate:
        return np.empty(shape=(0,data.shape[1]))
    noise_profile = np.tile(noise_profile, (int(np.ceil(len(data) / len(noise_profile))), 1))[:len(data)]
    #normalize noise profile (fill in hanning dips)
    return (noise_profile)

def audacity_like_filter(data, sample_rate, channels=1):
    """
    Performs noise filtering on a NumPy audio array similar to Audacity.
    Args:
        data: A NumPy array containing the audio data (float32 or int16).
        sample_rate: The sampling rate of the audio (Hz).
        channels: The number of audio channels (1 for mono, 2 for stereo).

    Returns:
        filtered_data: A NumPy array containing the noise-reduced audio data.
    """
    if len(data)==0:
        return data
    # Step 1: Estimate noise floor
    noise_sample=[]
    noise_margin=1/10
    print(data.shape)
    while len(noise_sample)<(sample_rate) and noise_margin<0.7: #find noise floor
        noise_sample = get_noise_profile(data, sample_rate, floor_margin=noise_margin).astype('float32')
        print(noise_sample.shape)
        noise_margin+=1/10
    if len(noise_sample)<=0:
        print('No suitable noise profile found')
        return data
    print(f'noise margin: {noise_margin}')
    print(noise_sample.shape)
    print('playing noise profile')
    au.play(noise_sample, sample_rate)
    au.wait()
    print('done')
    # Convert data and noise sample to frequency domain using FFT
    fft_data = np.fft.fft(data)
    fft_noise = np.fft.fft(noise_sample)
    # Step 2: Spectral subtraction
    # Average the noise spectrum across channels (if stereo)
    if channels == 2:
        fft_noise = np.mean(fft_noise, axis=1)
    # Subtract the noise spectrum from the data spectrum
    fft_filtered = fft_data - fft_noise
    # Step 3: Reconstruction and smoothing
    # Apply a smoothing window function (e.g., Hann) to avoid artifacts
    #hann_window = np.hanning(fft_filtered.shape[0])
    #fft_filtered *= hann_window[:, None]
    #fft_filtered *= np.hanning(len(fft_filtered))
    filtered_data = np.fft.ifft(fft_filtered).real
    # Ensure data format remains unchanged
    if data.dtype == np.int16:
        filtered_data = np.clip(filtered_data, -1.0, 1.0) * np.iinfo(np.int16).max
    else:
        filtered_data = np.clip(filtered_data, -1.0, 1.0)
    return filtered_data.astype('float32')
    pass


