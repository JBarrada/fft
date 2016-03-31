import math
import numpy
import wave
import struct
import time
from graphics import *

win = GraphWin('!!!', 600, 200)

def do_fft(data, num_samples, nyquist):

    fk = numpy.fft.rfft(data)

    norm = 2.0 / num_samples
    fk *= norm

    # element 0 of fk is the DC component -- we don't want to plot that
    fk_r = fk.real
    fk_i = fk.imag

    # k = numpy.fft.rfftfreq(num_samples)[range(0, num_samples / 2 + 1)]
    k = numpy.fft.rfftfreq(num_samples, float(num_samples/float(nyquist)))

    # the last element is negative, because of the symmetry, but should
    # be positive (see http://docs.scipy.org/doc/numpy-dev/reference/generated/numpy.fft.rfftfreq.html)

    # kfreq = k * num_samples / nyquist

    # Inverse transform: F(k) -> f(x) -- without the normalization
    # fkinv = numpy.fft.irfft(fk / norm)

    fk_abs = numpy.abs(fk)

    maxxx = max(fk_abs)

    for j in range(len(fk_r)):
        # print(str(k[i]).ljust(20) + ": " + str(fk_abs[i]))
        win.plotPixel(j, (fk_abs[j]/maxxx)*200)

    # print
    # print(max(fk_abs))


w = wave.open('test.wav')
fr = w.getframerate()

try:
    while 1:
        frames = w.readframes(512)
        raw_samples = [0]*512
        for i in range(0, 1024, 2):
            sample = struct.unpack('<h', frames[i:i+2])[0]
            raw_samples[i/2] = float(sample/(fr/2))

        do_fft(raw_samples, 512, fr)
        # time.sleep(float(1024/float(fr)))
except Exception as ex:
    pass

