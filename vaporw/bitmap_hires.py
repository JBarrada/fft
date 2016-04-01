import struct
import threading
import wave

import math
import numpy
import scipy
import scipy.signal
import scipy.stats

from PIL import Image, ImageDraw, ImageOps

COMPUTE_SIZE = 512

in_audio = wave.open('test2.wav', 'rb')
image = Image.new('RGBA', (in_audio.getnframes()/COMPUTE_SIZE, COMPUTE_SIZE/2), color=(0, 0, 0, 255))
draw = ImageDraw.Draw(image)


def do_fft(raw_samples, size):
        fk = numpy.fft.rfft(raw_samples)
        norm = 2.0 / size
        fk *= norm

        # fk += min(fk)
        return numpy.abs(fk)

testdata = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
ffttest = do_fft(testdata, 10)

xpos = 0
data = in_audio.readframes(COMPUTE_SIZE)
while data != '' and len(data) == COMPUTE_SIZE*2:
    samples = struct.unpack('<%dh' % COMPUTE_SIZE, data)

    fft = do_fft(samples, COMPUTE_SIZE)
    fft /= 32768.0
    fft *= numpy.linspace(1, 30, len(fft))

    for y in range(COMPUTE_SIZE/2):
        value = int(fft[y]*255) & 0xff
        draw.point([xpos, y], (value, value, value, 255))

    xpos += 1
    data = in_audio.readframes(COMPUTE_SIZE)

image = ImageOps.flip(image)
image.save('test.png')
