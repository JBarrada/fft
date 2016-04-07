import math
import numpy
import scipy
import scipy.signal
import scipy.stats

COMPUTE_SIZE = 512


class ProbDensity:
    densities = []
    max = 0

    def __init__(self):
        self.densities = []
        self.max = 0

    def get_spread(self, fft, center):
        int_center = int(center)
        total_mass = sum(fft)
        temp_sum = 0.0
        for i in range(int_center, len(fft)):
            temp_sum += fft[i]
            if temp_sum >= total_mass*0.5:
                return i-int_center
        return 0

    def process_frames(self, fft):
        tmp_fft = numpy.copy(fft)

        # tmp_fft[:135] = 0
        # tmp_fft[165:] = 0

        tmp_fft -= tmp_fft.mean()
        tmp_fft = numpy.clip(tmp_fft, 0, 100)
        center = scipy.ndimage.measurements.center_of_mass(tmp_fft)[0]
        spread = self.get_spread(tmp_fft, center)
        total_mass = sum(tmp_fft)
        self.max = total_mass if total_mass > self.max else self.max
        self.densities += [(center, spread, total_mass)]


class FFTData:
    fft = []
    max = 0
    count = 0

    def __init__(self):
        self.fft = []
        self.max = 0

    def process_frames(self, fft):
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

    def process_frames(self, fft):
        if len(self.prev) != 0:
            sml = self.calc_similarity(fft)
            self.max = sml if sml > self.max else self.max
            self.similarities += [sml]
        else:
            self.similarities += [0]
        self.prev = fft[:]


class Intensities:
    intensities = []
    hits = []
    hits_high = []
    hits_low = []
    max = 0

    def __init__(self):
        self.prev = []
        self.intensities = []
        self.max = 0

    def post_process(self):
        self.hits = [0]*len(self.intensities)
        self.hits_high = [0]*len(self.intensities)
        self.hits_low = [0]*len(self.intensities)

        prev = []

        low = 0.2*self.max
        high = 0.29*self.max
        low_clip = numpy.mean(self.intensities)/self.max

        for i in range(len(self.intensities)):
            val = self.intensities[i]
            if len(prev) != 0:
                t_high = min(((sum(prev)/len(prev))/self.max)-0.02, 1.0)
                t_low = max(t_high-0.02, low_clip)
                t_high = t_high*(1.0-low_clip) + low_clip
                self.hits_high[i] = t_high
                self.hits_low[i] = t_low

                # high = t_high*self.max
                # low = t_low*self.max

            prev += [val]
            if len(prev) > 10:
                del prev[0]

        self.hits_high[0:-5] = self.hits_high[5:]
        self.hits_low[0:-5] = self.hits_low[5:]

        trig = False
        for i in range(len(self.intensities)):
            val = self.intensities[i]

            high = self.hits_high[i]*self.max
            low = self.hits_low[i]*self.max

            if val >= high and not trig:
                trig = True
                self.hits[i] = 1
            elif val >= high and trig:
                self.hits[i] = 0
            elif val <= low:
                trig = False
                self.hits[i] = 0
            else:
                self.hits[i] = 0

    def process_frames(self, fft):
        intensity = sum(fft)
        self.max = intensity if intensity > self.max else self.max
        self.intensities += [intensity]


class ProcessedAudio:
    frames = 0
    rate = 44100
    pbd = ProbDensity()
    sml = Similarity()
    its = Intensities()
    fftd = FFTData()

    def __init__(self, rate, frames):
        self.frames = frames
        self.rate = rate
        self.pbd = ProbDensity()
        self.fftd = FFTData()

    def do_fft(self, data, size, rate):
        fk = numpy.fft.rfft(data)
        norm = 2.0 / size
        fk *= norm
        k = numpy.fft.rfftfreq(size, float(size/float(rate/2.0)))
        numpy.multiply(fk, k, fk)
        return numpy.abs(fk)[:COMPUTE_SIZE/2]

    def post_process(self):
        ratio = numpy.mean(self.fftd.fft) / self.fftd.max
        normalize = 0.05 / ratio
        for i in range(len(self.fftd.fft)):
            self.fftd.fft[i] *= normalize
            numpy.clip(self.fftd.fft[i], 0.0, self.fftd.max, self.fftd.fft[i])

            self.pbd.process_frames(self.fftd.fft[i])
            self.sml.process_frames(self.fftd.fft[i][90:])
            self.its.process_frames(self.fftd.fft[i][90:])

        self.its.post_process()

    def process_samples(self, data, index):
        fft = self.do_fft(data, COMPUTE_SIZE, self.rate)
        # fft *= numpy.linspace(1, 40, len(fft))
        fft /= 16384.0

        self.fftd.process_frames(fft)
