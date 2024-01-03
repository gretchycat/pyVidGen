import sys,os,pydub,time, random
from datetime import datetime as dt
from optparse import OptionParser
try:
    import sounddevice as sd
except:
    print('missing sounddevice library.')
    from termux_audio import termux_audio as sd
try:
    import numpy as np
except:
    print('missing numpy library.')
from pydub import AudioSegment

STOP=0
PLAY=1
RECORD=2

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
    sd.play(noise_sample, sample_rate)
    sd.wait()
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

class pymms:
    def __init__(self):
        self.x=1
        self.y=1
        self.yy=1
        self.status=STOP
        self.fps=48000
        self.factor=self.fps
        self.channels=1
        self.cursor=0
        self.startTime=0
        self.selected=0
        self.selected_length=0
        self.buffer=[]
        self.record_buffer=[]
        self.stream=None
        self.stop()

    def load(self, filename):
        sd.stop()
        self.timer_clear()
        self.cursor=0
        self.selected=0
        self.selected_length=0
        self.record_buffer=[]
        audio=AudioSegment.from_file(filename)
        audio_array=audio.get_array_of_samples()
        self.fps=audio.frame_rate
        self.factor=self.fps
        self.channels=audio.channels
        self.sample_width=0 #audio.sample_width
        self.buffer=audio_array
        if self.status==PLAY:
            self.stop()
            self.play()
        return {'title':filename, 'length':audio.duration_seconds, 'bitrate':self.fps, 'quality':self.sample_width, 'channels':self.channels}

    def timer_now(self):
        return dt.now().timestamp()

    def timer_start(self, factor=1, offset=0):
        self.factor=factor
        self.startTime=self.timer_now()+offset

    def timer_get(self):
        if self.startTime>0:
            return (self.timer_now()-self.startTime)*self.factor
        else:
            return 0

    def timer_clear(self):
        t=self.timer_get()
        self.startTime=0
        return t

    def save(self, filename):
        # Validate audio data
        #if not isinstance(self.buffer, np.ndarray):
        #    raise ValueError("audio_data must be a NumPy array")
        #if self.buffer.dtype not in [np.float32, np.int16]:
        #    raise ValueError("audio data must be float32 or int16")
        buf=self.buffer
        # Normalize audio data to appropriate range
        #if self.buffer.dtype == np.float32:
        #    buf = np.clip(self.buffer, -1.0, 1.0) * np.iinfo(np.int16).max
        #buf = buf.astype(np.int16)
        # Create a pydub AudioSegment from the NumPy array
        if self.length():
            audio_segment = pydub.AudioSegment(buf.tobytes(),
                frame_rate=self.fps, sample_width=16//8, channels=self.channels)
            audio_segment.export(filename)

    def playpause(self):
        if self.status in [ PLAY, RECORD ]:
            self.pause()
        elif self.status==STOP:
            self.play()

    def record(self):
        if self.status==STOP:
            self.status=RECORD
            self.timer_start(factor=self.fps)
            c=self.cursor
            s=int(self.selected)
            sl=int(self.selected_length)
            if sl>0:
                self.pre=self.buffer[:s]
                self.post=self.buffer[s+sl:]
            else:
                self.pre=self.buffer[:c]
                self.post=self.buffer[c:]
            self.record_buffer=sd.rec(self.fps*60*10, self.fps, channels=self.channels)


    def play(self):
        if self.status==STOP:
            self.status=PLAY
            self.timer_start(factor=self.fps, offset=-int(self.get_cursor()/self.fps))
            c=self.get_cursor()
            s=int(self.selected)
            sl=int(self.selected_length)
            if sl==0:
                sd.play(self.buffer[c:], self.fps)
            else:
                sd.play(self.buffer[c:s+sl], self.fps)

    def pause(self):
        if self.status==PLAY:
            self.status=STOP
            sd.stop()
            self.timer_clear()
        elif self.status==RECORD:
            self.status=STOP
            sd.stop()
            length=int(self.timer_get())
            record_buffer=self.record_buffer[:length] #truncate buffer
            #window = np.hanning(self.record_buffer.shape[0])[:,None]
            #self.record_buffer=self.record_buffer * window
            self.cursor=len(self.pre)+(len(record_buffer))
            self.selected=0
            self.selected_length=0
            if len(self.pre)==0:
                self.buffer=record_buffer
            else:
                self.buffer=self.pre+record_buffer #np.concatenate((self.pre, record_buffer))
            if len(self.post)>0:
                self.buffer=self.buffer+self.post #np.concatenate((self.buffer, self.post))
            self.pre, self.post = [], []
            self.record_buffer=[]
            self.timer_clear()

    def length_time(self):
        return self.length()/self.fps

    def length(self):
        if self.status==RECORD:
            if self.timer_get():
                return int(self.timer_get()+len(self.buffer)/self.channels)
            return 0
        else:
            return int(len(self.buffer)/self.channels)

    def stop(self):
        self.pause()
        self.selected=0
        self.selected_length=0
        self.cursor=0
        self.timer_clear()

    def seek_time(self, time):
        self.seek(time*self.fps)

    def seek(self, frame):
        playing=self.status==PLAY
        if playing:
            self.pause()
        if self.status==STOP:
            if frame<0:
                frame=0
            if frame>self.length():
                time=self.length()
            self.cursor=frame
        if self.cursor>self.length():
            self.cursor=self.length()
        if playing:
            self.play()

    def seekFwd_time(self, time):
        self.seekFwd(time*self.fps)

    def seekFwd(self, frames):
        self.seek(self.cursor+frames)

    def seekBack_time(self, time):
        self.seekBack(time*self.fps)

    def seekBack(self, frames):
        self.seek(self.cursor-frames)

    def select_time(self, s, sl):
        self.select(s*self.fps, sl*self.fps)

    def select(self, s, sl):
        if self.status==STOP:
            if s<0:
                s=0
            if sl<0:
                sl=0
            if sl>0:
                if s<self.length():
                    s=self.length()
                if s+sl>self.length():
                    sl=self.length()-s
                self.selected=s
                self.selected_length=sl

    def clear(self):
        if self.selected_length==0:
            self.buffer=[]
        else:
            self.clear_selected()

    def clear_selected(self):
        self.seek(self.selected)
        s=int(self.selected)
        sl=int(self.selected_length
               )
        pre=self.buffer[:s]
        post=self.buffer[s+sl:]
        if len(pre)>0:
            if len(post)>0:
                self.buffer=pre+post #np.concatenate((pre, post))
            else:
                self.buffer=pre
        else:
            if len(post)>0:
                self.buffer=post
            else:
                self.buffer=[]

    def get_cursor(self): #TODO FIXME find authoritative value
        if self.cursor>=self.length() and self.status==PLAY:
            if self.endHandler:
                self.endHandler()
        t=self.timer_get()
        if t>0:
            self.cursor=int(t)
            if self.cursor>self.length():
                self.cursor=self.length()
        if self.status==RECORD:
            return self.cursor+len(self.pre)/self.channels
        return self.cursor

    def get_cursor_time(self):
        return self.get_cursor()/self.fps

    def denoise(self):
        self.buffer = audacity_like_filter(self.buffer, self.fps)
        #self.buffer = ideal_bandpass_filter(self.buffer, 100, 500, self.fps).real
        #self.buffer = butterworth_filter(self.buffer, 500, 2, self.fps)

    def normalize(self):
        pass

def main():
    return

if __name__ == "__main__":
    main()
