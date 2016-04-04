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
    densities = []

    def __init__(self):
        self.densities = []

    def get_spread(self, fft, center):
        int_center = int(center)
        total_mass = sum(fft)
        temp_sum = 0.0
        for i in range(int_center, len(fft)):
            temp_sum += fft[i]
            if temp_sum >= total_mass*0.5:
                return i-int_center
        return 0

    def process_frames(self, fft, index):
        tmp_fft = numpy.copy(fft)

        # tmp_fft[:135] = 0
        # tmp_fft[165:] = 0

        tmp_fft -= tmp_fft.mean()
        tmp_fft = numpy.clip(tmp_fft, 0, 100)
        center = scipy.ndimage.measurements.center_of_mass(tmp_fft)[0]
        spread = self.get_spread(tmp_fft, center)
        total_mass = sum(tmp_fft)
        self.densities += [(center, spread, total_mass)]


class FFTData:
    fft = []
    max = 0
    count = 0

    def __init__(self):
        self.fft = []
        self.max = 0

    def process_frames(self, fft, index):
        self.max = max(fft) if max(fft) > self.max else self.max
        self.fft += [fft]
        self.count = len(self.fft)


class Similarity:
    prev = []
    similarities = []
    max = 0

    def __init__(self):
        self.prev = []
        self.similarities = []
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
            self.similarities += [sml]
        else:
            self.similarities += [0]
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
        self.sml.process_frames(fft[80:], index)
