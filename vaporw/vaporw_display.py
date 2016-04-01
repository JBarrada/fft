from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import colorsys
import wave
import pyaudio
import numpy

import vaporw_compute


class Display:
    in_audio = None
    out_audio = None
    marker_pos = 0
    playing = False

    fft_tex = None
    fft_tex_made = False

    W_WIDTH = 600
    W_HEIGHT = 100

    zoom = 1.0
    offset = 0
    view_grab = False
    view_grab_x = 0
    offset_temp = 0

    survey_down = False
    survey_y = 0

    pdf_overlay = False
    sml_overlay = False

    display_pa = vaporw_compute.ProcessedAudio

    def __init__(self, width, height, in_audio, out_audio):
        self.in_audio = in_audio
        self.out_audio = out_audio

        self.W_WIDTH = width
        self.W_HEIGHT = height

    def init(self):
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glColor3f(1.0, 1.0, 1.0)
        glPointSize(1.0)
        glLineWidth(1.0)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0.0, self.W_WIDTH, 0.0, self.W_HEIGHT)

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

        self.fft_gen_tex()

        glutMainLoop()

    def close(self):
        self.out_audio.stop_stream()
        self.out_audio.close()

    def keyboard(self, key, x, y):
        if key == ' ':
            self.playing = True if not self.playing else False
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

                self.marker_pos = pos*self.display_pa.frames
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
        self.zoom += direction/5.0
        self.zoom = max(self.zoom, 1.0)
        self.zoom = min(self.zoom, 100.0)
        i_scale = self.zoom/p_scale

        self.offset -= ((x-self.offset)*i_scale)-(x-self.offset)
        self.offset = 0 if self.offset > 0 else self.offset

    def draw_wfd(self, bottom, height):
        glBegin(GL_LINES)

        glColor3f(1.0, 1.0, 1.0)
        sortedkeys = self.display_pa.wfd.intensities.keys()
        sortedkeys.sort()
        for key in sortedkeys:
            display_intensity = (self.display_pa.wfd.intensities[key]/self.display_pa.wfd.max)*(height/2.0)
            glVertex2f((float(key)/self.display_pa.frames)*self.W_WIDTH, bottom+(height/2.0)+display_intensity)
            glVertex2f((float(key)/self.display_pa.frames)*self.W_WIDTH, bottom+(height/2.0)-display_intensity)
        glEnd()
        glDisable(GL_DEPTH_TEST)

    def draw_pbd(self, bottom, height):
        glBegin(GL_LINES)

        glColor3f(1.0, 1.0, 1.0)
        largest_mass = 0
        for k, v in self.display_pa.pbd.densities.items():
            largest_mass = v[2] if v[2] > largest_mass else largest_mass

        sortedkeys = self.display_pa.pbd.densities.keys()
        sortedkeys.sort()
        for key in sortedkeys:
            xloc = self.offset+((float(key)/self.display_pa.frames)*(self.W_WIDTH*self.zoom))
            if 0 <= xloc <= self.W_WIDTH:
                i_scale = self.display_pa.pbd.densities[key][2]/largest_mass
                node_y = (self.display_pa.pbd.densities[key][0]/(vaporw_compute.COMPUTE_SIZE/2.0))*height
                node_i = ((self.display_pa.pbd.densities[key][1]*i_scale)/(vaporw_compute.COMPUTE_SIZE/2.0))*height
                glVertex2f(xloc, bottom+node_y+node_i)
                glVertex2f(xloc, bottom+node_y-node_i)
        glEnd()
        glDisable(GL_DEPTH_TEST)

    def draw_sml(self, bottom, height):
        glBegin(GL_LINES)
        sortedkeys = self.display_pa.sml.similarities.keys()
        sortedkeys.sort()

        for key in sortedkeys:
            xloc = self.offset+((float(key)/self.display_pa.frames)*(self.W_WIDTH*self.zoom))
            if 0 <= xloc <= self.W_WIDTH:
                intensity = self.display_pa.sml.similarities[key] / self.display_pa.sml.max
                if intensity > 0.1:
                    glColor3f(intensity, intensity, intensity)
                    glVertex2f(xloc, bottom)
                    glVertex2f(xloc, bottom+height)
        glEnd()
        glDisable(GL_DEPTH_TEST)

    def draw_fftd(self, bottom, height):
        glEnable(GL_TEXTURE_2D)

        glBindTexture(GL_TEXTURE_2D, self.fft_tex)
        glBegin(GL_QUADS)

        glTexCoord2i(0, 0)
        glVertex2f(self.offset, bottom)

        glTexCoord2i(1, 0)
        glVertex2f(self.offset+(self.W_WIDTH*self.zoom), bottom)

        glTexCoord2i(1, 1)
        glVertex2f(self.offset+(self.W_WIDTH*self.zoom), bottom+height)

        glTexCoord2i(0, 1)
        glVertex2f(self.offset, bottom+height)

        glEnd()
        glDisable(GL_TEXTURE_2D)

    def fft_gen_tex(self):
        width, height = len(self.display_pa.fftd.fft), len(self.display_pa.fftd.fft[0])
        width = (4-(width % 4))+width if width % 4 != 0 else width
        bitmap = [0] * (width*height)

        sortedkeys = self.display_pa.fftd.fft.keys()
        sortedkeys.sort()

        for x in range(width):
            adjusted = self.display_pa.fftd.fft[sortedkeys[x]] / self.display_pa.fftd.max
            adjusted *= 0xff

            if x < len(self.display_pa.fftd.fft):
                for y in range(height):
                    # value = int((self.display_pa.fftd.fft[sortedkeys[x]][y] / self.display_pa.fftd.max)*255) & 0xff
                    bitmap[y*width+x] = int(adjusted[y])

        self.fft_tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.fft_tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_LUMINANCE, width, height, 0, GL_LUMINANCE, GL_UNSIGNED_BYTE, bitmap)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

        self.fft_tex_made = True

    def display(self):
        glClear(GL_COLOR_BUFFER_BIT)

        glColor3f(1.0, 1.0, 1.0)
        self.draw_fftd(0, self.W_HEIGHT)

        if self.pdf_overlay:
            self.draw_pbd(0, self.W_HEIGHT)
        if self.sml_overlay:
            self.draw_sml(0, self.W_HEIGHT)

        glColor3f(1.0, 0, 0)
        glBegin(GL_LINES)
        markerx = self.offset+(float(self.marker_pos)/self.display_pa.frames)*(self.W_WIDTH*self.zoom)
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
            if self.marker_pos >= (self.display_pa.frames-vaporw_compute.COMPUTE_SIZE):
                self.marker_pos = 0
                self.playing = False
        self.display()
