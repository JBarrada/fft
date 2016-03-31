import math
import numpy
import scipy
import scipy.signal
import struct
import time
import opengl
import threading
from operator import itemgetter

import wave
import pyaudio

SAMPLE_RATE = 44100
FFT_SIZE = 1024


def do_fft(data, size, rate):
    fk = numpy.fft.rfft(data)
    norm = 2.0 / size
    fk *= norm

    # k = numpy.fft.rfftfreq(num_samples, float(num_samples/float(nyquist)))
    return numpy.abs(fk)


def peak_has_neighbor(pos, fft_data):
    global peaks
    neighbors = [(x, y, z) for (x, y, z) in peaks if (x in range(pos-2, pos+2))]
    if len(neighbors):
        return pos, max(neighbors, key=itemgetter(1))[1]+1, (max(neighbors, key=itemgetter(1))[2]+fft_data[pos]) / 2.0
    else:
        return pos, 1, fft_data[pos]


def process_peaks(fft_data, fft_avg):
    fft_data_clipped = numpy.clip(fft_data, max(fft_avg, 0.06), 10)

    peaks_raw = scipy.signal.argrelmax(fft_data_clipped)[0]

    peaks_n = [peak_has_neighbor(x, fft_data) for x in peaks_raw]

    return peaks_n


p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=FFT_SIZE, input_device_index=2)

loop = threading.Thread(target=opengl.start_window)
loop.start()

peaks = []

while True:
    frames = stream.read(FFT_SIZE)
    samples = struct.unpack('<%dh' % FFT_SIZE, frames)

    fft = do_fft(samples, FFT_SIZE, SAMPLE_RATE)
    fft *= numpy.linspace(1, 30, len(fft))
    fft /= 16384.0

    avg += numpy.average(fft[8:FFT_SIZE/8])
    avg /= 2

    peaks = process_peaks(fft[0:FFT_SIZE/8], avg)
    if len(peaks):
        max_sustain = max(peaks, key=itemgetter(1))[1]
        peaks_clean = [(x, y, z) for (x, y, z) in peaks if y > min(5, max_sustain*0.75)]
        opengl.peaks = peaks_clean
    else:
        opengl.peaks = []

    opengl.avg = avg
    opengl.fft_data = fft

