import struct
import threading
import wave
import pyaudio

import vaporw_compute
import vaporw_display

in_audio = wave.open('test2chan.wav', 'rb')

IN_SAMPLEWIDTH = in_audio.getsampwidth()
IN_CHANNELS = in_audio.getnchannels()
IN_FRAMERATE = in_audio.getframerate()
IN_NFRAMES = in_audio.getnframes()

p = pyaudio.PyAudio()
out_audio = p.open(format=p.get_format_from_width(IN_SAMPLEWIDTH), channels=IN_CHANNELS, rate=IN_FRAMERATE, output=True)

pa = vaporw_compute.ProcessedAudio(IN_FRAMERATE, IN_NFRAMES)

display = vaporw_display.Display(600, 300, in_audio, out_audio)
display.pa = pa

data = in_audio.readframes(vaporw_compute.COMPUTE_SIZE)
while data != '' and len(data) == vaporw_compute.COMPUTE_SIZE*2*IN_CHANNELS:
    raw = struct.unpack('<%dh' % (vaporw_compute.COMPUTE_SIZE*IN_CHANNELS), data)
    samples_l = raw[0::2]
    samples_r = raw[1::2]
    pa.process_samples(samples_l, samples_r)

    data = in_audio.readframes(vaporw_compute.COMPUTE_SIZE)

pa.post_process()

loop = threading.Thread(target=display.start_window)
loop.start()
