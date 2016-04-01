import struct
import threading
import wave
import pyaudio

import vaporw_compute
import vaporw_display

in_audio = wave.open('test2.wav', 'rb')

IN_SAMPLEWIDTH = in_audio.getsampwidth()
IN_CHANNELS = in_audio.getnchannels()
IN_FRAMERATE = in_audio.getframerate()
IN_NFRAMES = in_audio.getnframes()

p = pyaudio.PyAudio()
out_audio = p.open(format=p.get_format_from_width(IN_SAMPLEWIDTH), channels=IN_CHANNELS, rate=IN_FRAMERATE, output=True)

pa = vaporw_compute.ProcessedAudio(IN_FRAMERATE, IN_NFRAMES)

display = vaporw_display.Display(600, 300, in_audio, out_audio)
display.display_pa = pa


index = vaporw_compute.COMPUTE_SIZE
data = in_audio.readframes(vaporw_compute.COMPUTE_SIZE)
while data != '' and len(data) == vaporw_compute.COMPUTE_SIZE*2:
    samples = struct.unpack('<%dh' % vaporw_compute.COMPUTE_SIZE, data)
    pa.process_samples(samples, index)

    data = in_audio.readframes(vaporw_compute.COMPUTE_SIZE)
    index += vaporw_compute.COMPUTE_SIZE


loop = threading.Thread(target=display.start_window)
loop.start()

# display.fft_gen_tex()

# in_audio.rewind()
# index = 0
# data = in_audio.readframes(vaporw_compute.COMPUTE_SIZE)
# while data != '':
#     out_audio.write(data)
#     display.marker_pos = index
#     data = in_audio.readframes(vaporw_compute.COMPUTE_SIZE)
#     index += vaporw_compute.COMPUTE_SIZE


# out_audio.stop_stream()
# out_audio.close()

# p.terminate()
