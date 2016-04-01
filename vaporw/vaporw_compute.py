import math
import numpy
import scipy
import scipy.signal
import scipy.stats

COMPUTE_SIZE = 512


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
    avg_rolling = None
    avg_count = 0
    fpe = 0
    densities = {}

    def __init__(self):
        self.avg_index = 0
        self.avg_rolling = None
        self.avg_count = 0
        self.fpe = 0
        self.density = {}

    def get_spread(self, center):
        int_center = int(center)
        total_mass = sum(self.avg_rolling)
        temp_sum = 0.0
        for i in range(int_center, len(self.avg_rolling)):
            temp_sum += self.avg_rolling[i]
            if temp_sum >= total_mass*0.5:
                return i-int_center
        return 0

    def process_frames(self, fft, index):
        self.avg_rolling = fft if self.avg_rolling is None else numpy.add(self.avg_rolling, fft)
        self.avg_rolling[:135] = 0
        self.avg_rolling[165:] = 0
        self.avg_count += 1

        if self.avg_count > self.fpe:
            self.avg_rolling -= self.avg_rolling.mean()
            self.avg_rolling = numpy.clip(self.avg_rolling, 0, 100)
            center = scipy.ndimage.measurements.center_of_mass(self.avg_rolling)[0]
            spead = self.get_spread(center)
            total_mass = sum(self.avg_rolling)
            self.densities[self.avg_index] = (center, spead, total_mass)
            self.avg_rolling = 0
            self.avg_count = 0
            self.avg_index = index


class FFTData:
    avg_index = 0
    avg_rolling = 0
    avg_count = 0
    fpe = 0
    fft = {}

    def __init__(self):
        self.avg_index = 0
        self.avg_rolling = 0
        self.avg_count = 0
        self.fpe = 1
        self.fft = {}
        self.max = 0

    def process_frames(self, fft, index):
        self.avg_rolling = numpy.add(self.avg_rolling, fft)
        self.avg_count += 1

        if self.avg_count > self.fpe:
            self.max = max(self.avg_rolling) if max(self.avg_rolling) > self.max else self.max
            self.fft[self.avg_index] = self.avg_rolling
            self.avg_rolling = 0
            self.avg_count = 0
            self.avg_index = index


class Similarity:
    prev = []
    similarities = {}
    max = 0

    def __init__(self):
        self.prev = []
        self.similarities = {}
        self.max = 0

    def calc_similarity(self, fft):
        difference = 0
        for i in range(len(fft)):
            difference += abs(fft[i]-self.prev[i])
        return difference

    def process_frames(self, fft, index):
        if len(self.prev) != 0:
            sml = self.calc_similarity(fft)
            self.max = sml if sml > self.max else self.max
            self.similarities[index] = sml
        self.prev = fft[:]


class ProcessedAudio:
    frames = 0
    rate = 44100
    wfd = WaveformData()
    pbd = ProbDensity()
    sml = Similarity()
    fftd = FFTData()

    def __init__(self, rate, frames):
        self.frames = frames
        self.rate = rate
        self.wfd = WaveformData()
        self.pbd = ProbDensity()
        self.fftd = FFTData()

    def do_fft(self, data, size, rate):
        fk = numpy.fft.rfft(data)
        norm = 2.0 / size
        fk *= norm
        # k = numpy.fft.rfftfreq(num_samples, float(num_samples/float(nyquist)))
        return numpy.abs(fk)[:COMPUTE_SIZE/2]

    def process_samples(self, data, index):
        self.wfd.process_frames(data, index)

        fft = self.do_fft(data, COMPUTE_SIZE, self.rate)
        fft *= numpy.linspace(1, 40, len(fft))
        fft /= 16384.0

        self.fftd.process_frames(fft, index)
        self.pbd.process_frames(fft, index)
        self.sml.process_frames(fft[135:165], index)
