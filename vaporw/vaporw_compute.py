import math
import numpy
import scipy
import scipy.signal
import scipy.stats

COMPUTE_SIZE = 1024


class WaveformData:
    avg_index = 0
    avg_rolling = 0
    avg_count = 0
    fpe = 4096
    intensities = {}
    max = 0

    def __init__(self):
        self.avg_index = 0
        self.avg_rolling = 0
        self.avg_count = 0
        self.fpe = 4096*2
        self.intensities = {}
        self.max = 0

    def process_frames(self, data, index):
        self.avg_rolling += numpy.average(numpy.absolute(data))
        self.avg_count += len(data)

        if self.avg_count > self.fpe:
            avg = self.avg_rolling/self.avg_count
            self.max = avg if avg > self.max else self.max
            self.intensities[self.avg_index] = avg
            self.avg_rolling = 0
            self.avg_count = 0
            self.avg_index = index


class ProbDensity:
    avg_index = 0
    avg_rolling = 0
    avg_count = 0
    fpe = 0
    densities = {}

    def __init__(self):
        self.avg_index = 0
        self.avg_rolling = 0
        self.avg_count = 0
        self.fpe = 8
        self.density = {}

    def process_frames(self, fft, index):
        self.avg_rolling = numpy.add(self.avg_rolling, fft)
        self.avg_count += 1

        if self.avg_count > self.fpe:
            self.avg_rolling -= self.avg_rolling.mean()
            self.avg_rolling = numpy.clip(self.avg_rolling, 0, 100)
            # test = scipy.stats.norm.pdf(self.avg_rolling)
            mean = scipy.ndimage.measurements.center_of_mass(self.avg_rolling)[0]
            varience = self.avg_rolling.var()
            self.densities[self.avg_index] = (mean, varience)
            self.avg_rolling = 0
            self.avg_count = 0
            self.avg_index = index


class ProcessedAudio:
    frames = 0
    rate = 44100
    wfd = WaveformData()
    pbd = ProbDensity()

    def __init__(self, rate, frames):
        self.frames = frames
        self.rate = rate
        self.wfd = WaveformData()
        self.pbd = ProbDensity()

    def do_fft(self, data, size, rate):
        fk = numpy.fft.rfft(data)
        norm = 2.0 / size
        fk *= norm
        # k = numpy.fft.rfftfreq(num_samples, float(num_samples/float(nyquist)))
        return numpy.abs(fk)

    def process_samples(self, data, index):
        self.wfd.process_frames(data, index)

        fft = self.do_fft(data, COMPUTE_SIZE, self.rate)
        fft *= numpy.linspace(1, 30, len(fft))
        fft /= 16384.0

        self.pbd.process_frames(fft, index)
