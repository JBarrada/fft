from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import colorsys
import wave
import pyaudio
import numpy

import time

import vaporw_compute


class Display:
    in_audio = None
    out_audio = None
    marker_pos = 0
    playing = False

    fft_tex = []
    pbd_tex = []
    sml_tex = []

    W_WIDTH = 600
    W_HEIGHT = 100

    zoom = 1.0
    offset = 0
    view_grab = False
    view_grab_x = 0
    offset_temp = 0

    track = False

    survey_down = False
    survey_y = 0

    fft_display = True
    pdf_overlay = False
    sml_overlay = False

    pa = vaporw_compute.ProcessedAudio

    def __init__(self, width, height, in_audio, out_audio):
        self.in_audio = in_audio
        self.out_audio = out_audio

        self.W_WIDTH = width
        self.W_HEIGHT = height

    def init(self):
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glColor3f(1.0, 1.0, 1.0)
        glPointSize(1.0)
        glLineWidth(2.0)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0.0, self.W_WIDTH, 0.0, self.W_HEIGHT)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self.fft_gen_tex()
        # self.pbd_gen_tex()
        # self.sml_gen_tex()

    def start_window(self):
        glutInit()

        glutInitWindowSize(self.W_WIDTH, self.W_HEIGHT)
        glutCreateWindow("!!!")
        glutInitDisplayMode(GLUT_SINGLE | GLUT_RGB)
        glutCloseFunc(self.close)
        glutDisplayFunc(self.display)
        glutKeyboardFunc(self.keyboard)
        glutMouseWheelFunc(self.mouse_wheel)
        glutMouseFunc(self.mouse)
        glutMotionFunc(self.motion)
        glutIdleFunc(self.idle)

        self.init()

        glutMainLoop()

    def close(self):
        self.out_audio.stop_stream()
        self.out_audio.close()

    def keyboard(self, key, x, y):
        if key == ' ':
            self.playing = True if not self.playing else False
        if key == '`':
            self.track = True if not self.track else False
        if key == 't':
            self.realupdate()
        if key == '0':
            self.fft_display = True if not self.fft_display else False
        if key == '1':
            self.pdf_overlay = True if not self.pdf_overlay else False
        if key == '2':
            self.sml_overlay = True if not self.sml_overlay else False

    def motion(self, x, y):
        if self.view_grab:
            self.offset = self.offset_temp - (self.view_grab_x-x)
            self.offset = 0 if self.offset > 0 else self.offset

    def mouse(self, button, state, x, y):
        if button == GLUT_LEFT_BUTTON:
            if state == GLUT_DOWN:
                pos = (-self.offset+((float(x)/glutGet(GLUT_WINDOW_WIDTH))*self.W_WIDTH))/(self.W_WIDTH*self.zoom)

                self.marker_pos = pos*self.pa.frames
                self.marker_pos = self.marker_pos - (self.marker_pos % vaporw_compute.COMPUTE_SIZE)

        if button == GLUT_MIDDLE_BUTTON:
            if state == GLUT_DOWN:
                self.view_grab = True
                self.view_grab_x = x
                self.offset_temp = self.offset
            else:
                self.view_grab = False

        if button == GLUT_RIGHT_BUTTON:
            if state == GLUT_DOWN:
                self.survey_down = True
                self.survey_y = glutGet(GLUT_WINDOW_HEIGHT) - y
                print((float(self.survey_y)/glutGet(GLUT_WINDOW_HEIGHT))*(vaporw_compute.COMPUTE_SIZE/2.0))
            else:
                self.survey_down = False

    def mouse_wheel(self, wheel, direction, x, y):
        x = (float(x)/glutGet(GLUT_WINDOW_WIDTH))*self.W_WIDTH
        p_scale = self.zoom
        self.zoom *= (1.0+(direction/5.0))
        self.zoom = max(self.zoom, 1.0)
        self.zoom = min(self.zoom, 100.0)
        i_scale = self.zoom/p_scale

        self.offset -= ((x-self.offset)*i_scale)-(x-self.offset)
        self.offset = 0 if self.offset > 0 else self.offset

    def draw_wfd(self, bottom, height):
        glBegin(GL_LINES)

        glColor3f(1.0, 1.0, 1.0)
        sortedkeys = self.pa.wfd.intensities.keys()
        sortedkeys.sort()
        for key in sortedkeys:
            display_intensity = (self.pa.wfd.intensities[key]/self.pa.wfd.max)*(height/2.0)
            glVertex2f((float(key)/self.pa.frames)*self.W_WIDTH, bottom+(height/2.0)+display_intensity)
            glVertex2f((float(key)/self.pa.frames)*self.W_WIDTH, bottom+(height/2.0)-display_intensity)
        glEnd()
        glDisable(GL_DEPTH_TEST)

    def draw_sml(self, bottom, height):
        t_width, t_height = len(self.pa.fftd.fft), len(self.pa.fftd.fft[0])

        glEnable(GL_TEXTURE_2D)
        glColor4f(0.0, 1.0, 1.0, 1.0)

        tex_n = 0
        for block in range(0, t_width, 256):
            b_width = 256 if block+256 <= t_width else (t_width-block)
            b_width = (4-(b_width % 4))+b_width if b_width % 4 != 0 else b_width

            tex_offset = (float(block)/t_width)*(self.W_WIDTH*self.zoom)
            tex_width = (float(b_width)/t_width)*(self.W_WIDTH*self.zoom)

            if self.offset+tex_offset+tex_width < 0:
                tex_n += 1
                continue
            if self.offset+tex_offset >= self.W_WIDTH:
                tex_n += 1
                continue

            glBindTexture(GL_TEXTURE_2D, self.sml_tex[tex_n])
            glBegin(GL_QUADS)
            glTexCoord2i(0, 0)
            glVertex2f(self.offset+tex_offset, bottom)
            glTexCoord2i(1, 0)
            glVertex2f(self.offset+tex_offset+tex_width, bottom)
            glTexCoord2i(1, 1)
            glVertex2f(self.offset+tex_offset+tex_width, bottom+height)
            glTexCoord2i(0, 1)
            glVertex2f(self.offset+tex_offset, bottom+height)
            glEnd()
            tex_n += 1

        glDisable(GL_TEXTURE_2D)

    def sml_gen_tex(self):
        t_width, t_height = len(self.pa.fftd.fft), len(self.pa.fftd.fft[0])

        for block in range(0, t_width-1, 256):
            b_width = 256 if block+256 <= t_width else (t_width-block)
            b_width_a = (4-(b_width % 4))+b_width if b_width % 4 != 0 else b_width

            bitmap = [0]*((t_height*b_width_a)*2)
            for x in range(block, block+b_width):
                intensity = int((self.pa.sml.similarities[x] / self.pa.sml.max) * 200)

                for y in range(t_height):
                    bitmap[(y*b_width_a+(x-block))*2] = 255
                    bitmap[((y*b_width_a+(x-block))*2)+1] = intensity

            tex_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, tex_id)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_LUMINANCE_ALPHA, b_width_a, t_height, 0, GL_LUMINANCE_ALPHA, GL_UNSIGNED_BYTE, bitmap)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
            self.sml_tex += [tex_id]

    def draw_fft(self, bottom, height):
        t_width, t_height = len(self.pa.fftd.fft), len(self.pa.fftd.fft[0])

        glEnable(GL_TEXTURE_2D)
        glColor3f(1.0, 1.0, 1.0)

        tex_n = 0
        for block in range(0, t_width, 256):
            b_width = 256 if block+256 <= t_width else (t_width-block)
            b_width = (4-(b_width % 4))+b_width if b_width % 4 != 0 else b_width

            tex_offset = (float(block)/t_width)*(self.W_WIDTH*self.zoom)
            tex_width = (float(b_width)/t_width)*(self.W_WIDTH*self.zoom)

            if self.offset+tex_offset+tex_width < 0:
                tex_n += 1
                continue
            if self.offset+tex_offset >= self.W_WIDTH:
                tex_n += 1
                continue

            glBindTexture(GL_TEXTURE_2D, self.fft_tex[tex_n])
            glBegin(GL_QUADS)
            glTexCoord2i(0, 0)
            glVertex2f(self.offset+tex_offset, bottom)
            glTexCoord2i(1, 0)
            glVertex2f(self.offset+tex_offset+tex_width, bottom)
            glTexCoord2i(1, 1)
            glVertex2f(self.offset+tex_offset+tex_width, bottom+height)
            glTexCoord2i(0, 1)
            glVertex2f(self.offset+tex_offset, bottom+height)
            glEnd()
            tex_n += 1

        glDisable(GL_TEXTURE_2D)

    def realupdate(self):
        start = time.time()
        t_width, t_height = len(self.pa.fftd.fft), len(self.pa.fftd.fft[0])

        texn = 0
        for block in range(0, t_width-1, 256):

            b_width = 256 if block+256 <= t_width else (t_width-block)
            b_width_a = (4-(b_width % 4))+b_width if b_width % 4 != 0 else b_width

            bitmap = [0]*(t_height*b_width_a)
            for x in range(block, block+b_width):
                normalized = self.pa.fftd.fft[x] / self.pa.fftd.max
                normalized *= 0xff
                for y in range(t_height):
                    bitmap[y*b_width_a+(x-block)+0] = int(normalized[y])

            tex_id = self.fft_tex[texn]
            glBindTexture(GL_TEXTURE_2D, tex_id)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_LUMINANCE, b_width_a, t_height, 0, GL_LUMINANCE, GL_UNSIGNED_BYTE, bitmap)
            texn += 1

        print(time.time()-start)

    def fft_gen_tex(self):
        start = time.time()
        t_width, t_height = len(self.pa.fftd.fft), len(self.pa.fftd.fft[0])

        for block in range(0, t_width-1, 256):

            b_width = 256 if block+256 <= t_width else (t_width-block)
            b_width_a = (4-(b_width % 4))+b_width if b_width % 4 != 0 else b_width

            bitmap = [0]*(t_height*b_width_a)
            for x in range(block, block+b_width):
                normalized = self.pa.fftd.fft[x] / self.pa.fftd.max
                normalized *= 0xff
                for y in range(t_height):
                    bitmap[y*b_width_a+(x-block)] = int(normalized[y])

            bitmap = [0]*(t_height*b_width_a)

            tex_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, tex_id)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_LUMINANCE, b_width_a, t_height, 0, GL_LUMINANCE, GL_UNSIGNED_BYTE, bitmap)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
            self.fft_tex += [tex_id]

        print(time.time()-start)

    def draw_pbd(self, bottom, height):
        t_width, t_height = len(self.pa.fftd.fft), len(self.pa.fftd.fft[0])

        glEnable(GL_TEXTURE_2D)

        tex_n = 0
        for block in range(0, t_width, 256):
            b_width = 256 if block+256 <= t_width else (t_width-block)
            b_width = (4-(b_width % 4))+b_width if b_width % 4 != 0 else b_width

            tex_offset = (float(block)/t_width)*(self.W_WIDTH*self.zoom)
            tex_width = (float(b_width)/t_width)*(self.W_WIDTH*self.zoom)

            if self.offset+tex_offset+tex_width < 0:
                tex_n += 1
                continue
            if self.offset+tex_offset >= self.W_WIDTH:
                tex_n += 1
                continue

            glBindTexture(GL_TEXTURE_2D, self.pbd_tex[tex_n])
            glBegin(GL_QUADS)
            glTexCoord2i(0, 0)
            glVertex2f(self.offset+tex_offset, bottom)
            glTexCoord2i(1, 0)
            glVertex2f(self.offset+tex_offset+tex_width, bottom)
            glTexCoord2i(1, 1)
            glVertex2f(self.offset+tex_offset+tex_width, bottom+height)
            glTexCoord2i(0, 1)
            glVertex2f(self.offset+tex_offset, bottom+height)
            glEnd()
            tex_n += 1

        glDisable(GL_TEXTURE_2D)

    def pbd_gen_tex(self):
        t_width, t_height = len(self.pa.fftd.fft), len(self.pa.fftd.fft[0])

        largest_mass = 0
        for pbd in self.pa.pbd.densities:
            largest_mass = pbd[2] if pbd[2] > largest_mass else largest_mass

        for block in range(0, t_width-1, 256):
            b_width = 256 if block+256 <= t_width else (t_width-block)
            b_width_a = (4-(b_width % 4))+b_width if b_width % 4 != 0 else b_width

            bitmap = [0]*((t_height*b_width_a)*2)
            for x in range(block, block+b_width):
                i_scale = self.pa.pbd.densities[x][2]/largest_mass
                node_y = (self.pa.pbd.densities[x][0]/(vaporw_compute.COMPUTE_SIZE/2.0))*t_height
                node_i = ((self.pa.pbd.densities[x][1]*i_scale)/(vaporw_compute.COMPUTE_SIZE/2.0))*t_height

                for y in range(int(node_y-node_i), int(node_y+node_i)):
                    bitmap[(y*b_width_a+(x-block))*2] = 255
                    bitmap[((y*b_width_a+(x-block))*2)+1] = 200

            tex_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, tex_id)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_LUMINANCE_ALPHA, b_width_a, t_height, 0, GL_LUMINANCE_ALPHA, GL_UNSIGNED_BYTE, bitmap)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
            self.pbd_tex += [tex_id]

    def display(self):
        glClear(GL_COLOR_BUFFER_BIT)

        if self.fft_display:
            self.draw_fft(0, self.W_HEIGHT)
        if self.pdf_overlay:
            self.draw_pbd(0, self.W_HEIGHT)
        if self.sml_overlay:
            self.draw_sml(0, self.W_HEIGHT)

        if self.track:
            glColor3f(1.0, 0, 1.0)
        else:
            glColor3f(1.0, 0, 0)
        glBegin(GL_LINES)
        markerx = self.offset+(float(self.marker_pos)/self.pa.frames)*(self.W_WIDTH*self.zoom)
        glVertex2f(markerx, 0)
        glVertex2f(markerx, self.W_HEIGHT)
        glEnd()

        glColor3f(1.0, 0, 1.0)
        glBegin(GL_LINES)
        markery = (float(self.survey_y)/glutGet(GLUT_WINDOW_HEIGHT))*self.W_HEIGHT
        glVertex2f(0, markery)
        glVertex2f(self.W_WIDTH, markery)
        glEnd()

        glFlush()

    def idle(self):
        # play
        if self.playing:
            self.in_audio.setpos(self.marker_pos)
            data = self.in_audio.readframes(vaporw_compute.COMPUTE_SIZE)
            self.out_audio.write(data)
            self.marker_pos += vaporw_compute.COMPUTE_SIZE
            if self.marker_pos >= (self.pa.frames-vaporw_compute.COMPUTE_SIZE):
                self.marker_pos = 0
                self.playing = False

        if self.track:
            self.offset = (self.W_WIDTH/2) - (float(self.marker_pos)/self.pa.frames)*(self.W_WIDTH*self.zoom)

        self.display()
