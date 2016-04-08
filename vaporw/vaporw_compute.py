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

        tmp_fft -= tmp_fft.mean()
        tmp_fft = numpy.clip(tmp_fft, 0, 100)
        center = scipy.ndimage.measurements.center_of_mass(tmp_fft)[0]
        spread = self.get_spread(tmp_fft, center)
        total_mass = sum(tmp_fft)
        self.max = total_mass if total_mass > self.max else self.max
        self.densities += [(center, spread, total_mass)]


class FFTData:
    fft_l = []
    fft_r = []
    max_l = 0
    max_r = 0
    count = 0

    def __init__(self):
        self.fft_l = []
        self.fft_r = []
        self.max_l = 0
        self.max_r = 0

    def post_process(self):
        lr_max = max(self.max_l,  self.max_r)
        ratio_l = numpy.mean(self.fft_l) / lr_max
        ratio_r = numpy.mean(self.fft_r) / lr_max
        normalize = 0.05 / ((ratio_l+ratio_r)/2.0)
        for i in range(len(self.fft_l)):
            numpy.clip(self.fft_l[i]*normalize, 0.0, lr_max, self.fft_l[i])
            self.max_l = max(self.fft_l[i]) if max(self.fft_l[i]) > self.max_l else self.max_l

            numpy.clip(self.fft_r[i]*normalize, 0.0, lr_max, self.fft_r[i])
            self.max_r = max(self.fft_r[i]) if max(self.fft_r[i]) > self.max_r else self.max_r

    def process_frames(self, fft_l, fft_r):
        self.max_l = max(fft_l) if max(fft_l) > self.max_l else self.max_l
        self.fft_l += [fft_l]
        self.max_r = max(fft_r) if max(fft_r) > self.max_r else self.max_r
        self.fft_r += [fft_r]
        self.count = len(self.fft_l)


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
    def __init__(self):
        self.intensities_l = []
        self.hits_l = []
        self.hits_high_l = []
        self.hits_low_l = []
        self.max_l = 0
        self.intensities_r = []
        self.hits_r = []
        self.hits_high_r = []
        self.hits_low_r = []
        self.max_r = 0

        self.clip_low = 90
        self.clip_high = 255

    def post_process(self):
        self.hits_l = [0]*len(self.intensities_l)
        self.hits_high_l = [0]*len(self.intensities_l)
        self.hits_low_l = [0]*len(self.intensities_l)

        self.hits_r = [0]*len(self.intensities_r)
        self.hits_high_r = [0]*len(self.intensities_r)
        self.hits_low_r = [0]*len(self.intensities_r)

        averaging = 40

        prev_l, prev_r = [], []
        low_clip_l, low_clip_r = numpy.mean(self.intensities_l)/self.max_l, numpy.mean(self.intensities_r)/self.max_r
        for i in range(len(self.intensities_l)):
            val_l, val_r = self.intensities_l[i], self.intensities_r[i]
            if len(prev_l) != 0 and len(prev_r) != 0:
                t_high_l = min(((sum(prev_l)/len(prev_l))/self.max_l)-0.03, 1.0)
                t_high_r = min(((sum(prev_r)/len(prev_r))/self.max_r)-0.03, 1.0)
                self.hits_high_l[i] = numpy.clip(t_high_l*(1.0-low_clip_l) + low_clip_l, 0, 0.34)
                self.hits_low_l[i] = max(t_high_l-0.02, low_clip_l)
                self.hits_high_r[i] = numpy.clip(t_high_r*(1.0-low_clip_r) + low_clip_r, 0, 0.34)
                self.hits_low_r[i] = max(t_high_r-0.02, low_clip_r)
            prev_l += [val_l]
            prev_r += [val_r]
            if len(prev_l) > averaging:
                del prev_l[0]
            if len(prev_r) > averaging:
                del prev_r[0]

        avg_2 = averaging/2
        self.hits_high_l[0:-avg_2] = self.hits_high_l[avg_2:]
        self.hits_low_l[0:-avg_2] = self.hits_low_l[avg_2:]
        self.hits_high_r[0:-avg_2] = self.hits_high_r[avg_2:]
        self.hits_low_r[0:-avg_2] = self.hits_low_r[avg_2:]

        trig_l, trig_r = False, False
        cool_l, cool_r = 0, 0
        for i in range(len(self.intensities_l)):
            val_l, val_r = self.intensities_l[i], self.intensities_r[i]

            high_l, high_r = self.hits_high_l[i]*self.max_l, self.hits_high_r[i]*self.max_r
            low_l, low_r = self.hits_low_l[i]*self.max_l, self.hits_low_r[i]*self.max_r

            if val_l > high_l and not trig_l and cool_l > 4:
                trig_l = True
                self.hits_l[i] = 1
                cool_l = 0
            elif val_l <= low_l or (val_l <= low_l and trig_l):
                trig_l = False
                self.hits_l[i] = 0
                
            if val_r > high_r and not trig_r and cool_r > 4:
                trig_r = True
                self.hits_r[i] = 1
                cool_r = 0
            elif val_r <= low_r or (val_r <= low_r and trig_r):
                trig_r = False
                self.hits_r[i] = 0

            cool_l += 1
            cool_r += 1

    def process_frames(self, fft_l, fft_r):
        intensity_l = sum(fft_l[self.clip_low:self.clip_high])
        self.max_l = intensity_l if intensity_l > self.max_l else self.max_l
        self.intensities_l += [intensity_l]
        intensity_r = sum(fft_r[self.clip_low:self.clip_high])
        self.max_r = intensity_r if intensity_r > self.max_r else self.max_r
        self.intensities_r += [intensity_r]


class ProcessedAudio:
    frames = 0
    rate = 0

    pbd = ProbDensity()
    sml = Similarity()
    its = Intensities()
    fftd = FFTData()

    def __init__(self, rate, frames):
        self.frames = frames
        self.rate = rate
        self.pbd = ProbDensity()
        self.fftd = FFTData()

    @staticmethod
    def do_fft(data, size, rate):
        fk = numpy.fft.rfft(data)
        norm = 2.0 / size
        fk *= norm
        k = numpy.fft.rfftfreq(size, float(size/float(rate/2.0)))
        numpy.multiply(fk, k, fk)
        return numpy.abs(fk)[:COMPUTE_SIZE/2]

    def post_process(self):
        self.fftd.post_process()
        for i in range(len(self.fftd.fft_l)):
            self.its.process_frames(self.fftd.fft_l[i], self.fftd.fft_r[i])
        self.its.post_process()

    def process_samples(self, samples_l, samples_r):
        fft_l = self.do_fft(samples_l, COMPUTE_SIZE, self.rate)
        fft_l /= 16384.0
        fft_r = self.do_fft(samples_r, COMPUTE_SIZE, self.rate)
        fft_r /= 16384.0

        self.fftd.process_frames(fft_l, fft_r)
