from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from ctypes import sizeof, memmove, addressof, create_string_buffer
import colorsys
import wave
import pyaudio
import numpy

import time

import vaporw_compute


class Texture:
    def __init__(self):
        empty = 0

    @staticmethod
    def upload_texture(width, height, bitmap):
        tex_buf = glGenBuffers(1)
        glBindBuffer(GL_PIXEL_UNPACK_BUFFER, tex_buf)
        glBufferData(GL_PIXEL_UNPACK_BUFFER, width*height, None, GL_STREAM_DRAW)
        datapointer = glMapBuffer(GL_PIXEL_UNPACK_BUFFER, GL_WRITE_ONLY)
        memmove(datapointer, addressof(bitmap), width*height)
        glUnmapBuffer(GL_PIXEL_UNPACK_BUFFER)

        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glBindBuffer(GL_PIXEL_UNPACK_BUFFER, tex_buf)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_ALPHA, width, height, 0, GL_ALPHA, GL_UNSIGNED_BYTE, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glDeleteBuffers(1, [tex_buf])
        return tex_id

    @staticmethod
    def update_texture(width, height, bitmap, tex_id):
        tex_buf = glGenBuffers(1)
        glBindBuffer(GL_PIXEL_UNPACK_BUFFER, tex_buf)
        glBufferData(GL_PIXEL_UNPACK_BUFFER, width*height, None, GL_STREAM_DRAW)
        datapointer = glMapBuffer(GL_PIXEL_UNPACK_BUFFER, GL_WRITE_ONLY)
        memmove(datapointer, addressof(bitmap), width*height)
        glUnmapBuffer(GL_PIXEL_UNPACK_BUFFER)

        glBindTexture(GL_TEXTURE_2D, tex_id)
        glBindBuffer(GL_PIXEL_UNPACK_BUFFER, tex_buf)
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, width, height, GL_ALPHA, GL_UNSIGNED_BYTE, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glDeleteBuffers(1, [tex_buf])

    @staticmethod
    def draw_texture_block(bottom, s_height, tex_width, offset, tex_offset, tex_id):
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glBegin(GL_QUADS)
        glTexCoord2i(0, 0)
        glVertex2f(offset+tex_offset, bottom)
        glTexCoord2i(1, 0)
        glVertex2f(offset+tex_offset+tex_width, bottom)
        glTexCoord2i(1, 1)
        glVertex2f(offset+tex_offset+tex_width, bottom+s_height)
        glTexCoord2i(0, 1)
        glVertex2f(offset+tex_offset, bottom+s_height)
        glEnd()


class FFTDisplay:
    def __init__(self, pa):
        self.tex_ids_l = []
        self.tex_ids_r = []
        self.pa = pa

    def draw(self, offset, scale, w_width, w_height, r, g, b, a=1.0):
        half_h = w_height/2.0
        t_width = self.pa.fftd.count
        glEnable(GL_TEXTURE_2D)
        glColor4f(r, g, b, a)

        tex_id_n = 0
        for block in range(0, t_width, 256):
            b_width = 256 if block+256 <= t_width else (t_width-block)
            b_width = (4-(b_width % 4))+b_width if b_width % 4 != 0 else b_width

            tex_offset = (float(block)/t_width)*(w_width*scale)
            tex_width = (float(b_width)/t_width)*(w_width*scale)

            if 0-tex_width < offset+tex_offset < w_width:
                Texture.draw_texture_block(half_h, half_h, tex_width, offset, tex_offset, self.tex_ids_l[tex_id_n])
                Texture.draw_texture_block(0, half_h, tex_width, offset, tex_offset, self.tex_ids_r[tex_id_n])

            tex_id_n += 1

        glDisable(GL_TEXTURE_2D)

    def create_tex(self):
        t_width, t_height = len(self.pa.fftd.fft_l), len(self.pa.fftd.fft_l[0])
        for block in range(0, t_width-1, 256):
            b_width = 256 if block+256 <= t_width else (t_width-block)
            b_width_a = (4-(b_width % 4))+b_width if b_width % 4 != 0 else b_width
            bitmap_l = self.bitmap_gen_l(block, b_width_a, b_width, t_height)
            bitmap_r = self.bitmap_gen_r(block, b_width_a, b_width, t_height)
            tex_id_l = Texture.upload_texture(b_width_a, t_height, bitmap_l)
            tex_id_r = Texture.upload_texture(b_width_a, t_height, bitmap_r)
            self.tex_ids_l += [tex_id_l]
            self.tex_ids_r += [tex_id_r]

    def recreate_tex(self):
        t_width, t_height = len(self.pa.fftd.fft_l), len(self.pa.fftd.fft_l[0])
        tex_id_n = 0
        for block in range(0, t_width-1, 256):
            b_width = 256 if block+256 <= t_width else (t_width-block)
            b_width_a = (4-(b_width % 4))+b_width if b_width % 4 != 0 else b_width
            bitmap_l = self.bitmap_gen_l(block, b_width_a, b_width, t_height)
            bitmap_r = self.bitmap_gen_l(block, b_width_a, b_width, t_height)
            Texture.update_texture(b_width_a, t_height, bitmap_l, self.tex_ids_l[tex_id_n])
            Texture.update_texture(b_width_a, t_height, bitmap_r, self.tex_ids_r[tex_id_n])
            tex_id_n += 1

    def bitmap_gen_l(self, block, width_a, width, height):
        bitmap = create_string_buffer(height*width_a)

        for x in range(block, block+width):
            normalized = (self.pa.fftd.fft_l[x] / self.pa.fftd.max_l) * 0xff
            for y in range(height):
                bitmap[y*width_a+(x-block)] = chr(int(normalized[y]))

        return bitmap

    def bitmap_gen_r(self, block, width_a, width, height):
        bitmap = create_string_buffer(height*width_a)

        for x in range(block, block+width):
            normalized = (self.pa.fftd.fft_r[x] / self.pa.fftd.max_r) * 0xff
            for y in range(height):
                bitmap[y*width_a+(x-block)] = chr(int(normalized[y]))

        return bitmap


class IntensityDisplay:
    def __init__(self, pa):
        self.tex_ids_l = []
        self.tex_ids_r = []
        self.tex_ids_hits_l = []
        self.tex_ids_hits_r = []
        self.tex_ids_high_l = []
        self.tex_ids_high_r = []
        self.tex_ids_low_l = []
        self.tex_ids_low_r = []

        self.pa = pa

    def draw(self, offset, scale, w_width, w_height, r, g, b, a=1.0, its=True, hits=True, high=True, low=True):
        half_h = w_height/2.0
        t_width = self.pa.fftd.count
        glEnable(GL_TEXTURE_2D)

        tex_id_n = 0
        for block in range(0, t_width, 256):
            b_width = 256 if block+256 <= t_width else (t_width-block)
            b_width = (4-(b_width % 4))+b_width if b_width % 4 != 0 else b_width

            tex_offset = (float(block)/t_width)*(w_width*scale)
            tex_width = (float(b_width)/t_width)*(w_width*scale)

            if 0-tex_width < offset+tex_offset < w_width:
                if its:
                    glColor4f(1, 1, 1, 0.8*a)
                    Texture.draw_texture_block(half_h, half_h, tex_width, offset, tex_offset, self.tex_ids_l[tex_id_n])
                    Texture.draw_texture_block(0, half_h, tex_width, offset, tex_offset, self.tex_ids_r[tex_id_n])
                if hits:
                    glColor4f(r, g, b, a)
                    Texture.draw_texture_block(half_h, half_h, tex_width, offset, tex_offset, self.tex_ids_hits_l[tex_id_n])
                    Texture.draw_texture_block(0, half_h, tex_width, offset, tex_offset, self.tex_ids_hits_r[tex_id_n])
                if high:
                    glColor4f(r, g, b, 0.4*a)
                    Texture.draw_texture_block(half_h, half_h, tex_width, offset, tex_offset, self.tex_ids_high_l[tex_id_n])
                    Texture.draw_texture_block(0, half_h, tex_width, offset, tex_offset, self.tex_ids_high_r[tex_id_n])
                if low:
                    glColor4f(1, 1, 1, 0.5*a)
                    Texture.draw_texture_block(half_h, half_h, tex_width, offset, tex_offset, self.tex_ids_low_l[tex_id_n])
                    Texture.draw_texture_block(0, half_h, tex_width, offset, tex_offset, self.tex_ids_low_r[tex_id_n])

            tex_id_n += 1

        glDisable(GL_TEXTURE_2D)

    def create_tex(self):
        t_width, t_height = len(self.pa.fftd.fft_l), len(self.pa.fftd.fft_l[0])
        for block in range(0, t_width-1, 256):
            b_width = 256 if block+256 <= t_width else (t_width-block)
            b_width_a = (4-(b_width % 4))+b_width if b_width % 4 != 0 else b_width

            bitmap_l = self.bitmap_gen_l(block, b_width_a, b_width, t_height)
            tex_id_l = Texture.upload_texture(b_width_a, t_height, bitmap_l)
            self.tex_ids_l += [tex_id_l]
            bitmap_r = self.bitmap_gen_r(block, b_width_a, b_width, t_height)
            tex_id_r = Texture.upload_texture(b_width_a, t_height, bitmap_r)
            self.tex_ids_r += [tex_id_r]

            bitmap_hits_l = self.bitmap_gen_hits_l(block, b_width_a, b_width, t_height)
            tex_id_hits_l = Texture.upload_texture(b_width_a, t_height, bitmap_hits_l)
            self.tex_ids_hits_l += [tex_id_hits_l]
            bitmap_hits_r = self.bitmap_gen_hits_r(block, b_width_a, b_width, t_height)
            tex_id_hits_r = Texture.upload_texture(b_width_a, t_height, bitmap_hits_r)
            self.tex_ids_hits_r += [tex_id_hits_r]

            bitmap_high_l = self.bitmap_gen_high_l(block, b_width_a, b_width, t_height)
            tex_id_high_l = Texture.upload_texture(b_width_a, t_height, bitmap_high_l)
            self.tex_ids_high_l += [tex_id_high_l]
            bitmap_high_r = self.bitmap_gen_high_r(block, b_width_a, b_width, t_height)
            tex_id_high_r = Texture.upload_texture(b_width_a, t_height, bitmap_high_r)
            self.tex_ids_high_r += [tex_id_high_r]

            bitmap_low_l = self.bitmap_gen_low_l(block, b_width_a, b_width, t_height)
            tex_id_low_l = Texture.upload_texture(b_width_a, t_height, bitmap_low_l)
            self.tex_ids_low_l += [tex_id_low_l]
            bitmap_low_r = self.bitmap_gen_low_r(block, b_width_a, b_width, t_height)
            tex_id_low_r = Texture.upload_texture(b_width_a, t_height, bitmap_low_r)
            self.tex_ids_low_r += [tex_id_low_r]

    def recreate_tex(self):
        t_width, t_height = len(self.pa.fftd.fft_l), len(self.pa.fftd.fft_l[0])
        tex_id_n = 0
        for block in range(0, t_width-1, 256):
            b_width = 256 if block+256 <= t_width else (t_width-block)
            b_width_a = (4-(b_width % 4))+b_width if b_width % 4 != 0 else b_width
            bitmap_l = self.bitmap_gen_l(block, b_width_a, b_width, t_height)
            bitmap_r = self.bitmap_gen_l(block, b_width_a, b_width, t_height)
            Texture.update_texture(b_width_a, t_height, bitmap_l, self.tex_ids_l[tex_id_n])
            Texture.update_texture(b_width_a, t_height, bitmap_r, self.tex_ids_r[tex_id_n])
            tex_id_n += 1

    def bitmap_gen_l(self, block, width_a, width, height):
        bitmap = create_string_buffer(height*width_a)

        for x in range(block, block+width):
            intensity = int((self.pa.its.intensities_l[x] / self.pa.its.max_l) * (height-1))
            for y in range(intensity):
                bitmap[y*width_a+(x-block)] = chr(200)

        return bitmap

    def bitmap_gen_r(self, block, width_a, width, height):
        bitmap = create_string_buffer(height*width_a)

        for x in range(block, block+width):
            intensity = int((self.pa.its.intensities_r[x] / self.pa.its.max_r) * (height-1))
            for y in range(intensity):
                bitmap[y*width_a+(x-block)] = chr(200)

        return bitmap

    def bitmap_gen_hits_l(self, block, width_a, width, height):
        bitmap = create_string_buffer(height*width_a)

        for x in range(block, block+width):
            if self.pa.its.hits_l[x] > 0:
                for y in range(self.pa.its.clip_low, self.pa.its.clip_high):
                    bitmap[y*width_a+(x-block)] = chr(200)

        return bitmap

    def bitmap_gen_hits_r(self, block, width_a, width, height):
        bitmap = create_string_buffer(height*width_a)

        for x in range(block, block+width):
            if self.pa.its.hits_r[x] > 0:
                for y in range(self.pa.its.clip_low, self.pa.its.clip_high):
                    bitmap[y*width_a+(x-block)] = chr(200)

        return bitmap

    def bitmap_gen_high_l(self, block, width_a, width, height):
        bitmap = create_string_buffer(height*width_a)

        for x in range(block, block+width):
            intensity = int(self.pa.its.hits_high_l[x] * (height-1))
            for y in range(intensity):
                bitmap[y*width_a+(x-block)] = chr(200)

        return bitmap

    def bitmap_gen_high_r(self, block, width_a, width, height):
        bitmap = create_string_buffer(height*width_a)

        for x in range(block, block+width):
            intensity = int(self.pa.its.hits_high_r[x] * (height-1))
            for y in range(intensity):
                bitmap[y*width_a+(x-block)] = chr(200)

        return bitmap

    def bitmap_gen_low_l(self, block, width_a, width, height):
        bitmap = create_string_buffer(height*width_a)

        for x in range(block, block+width):
            intensity = int(self.pa.its.hits_low_l[x] * (height-1))
            for y in range(intensity):
                bitmap[y*width_a+(x-block)] = chr(200)

        return bitmap

    def bitmap_gen_low_r(self, block, width_a, width, height):
        bitmap = create_string_buffer(height*width_a)

        for x in range(block, block+width):
            intensity = int(self.pa.its.hits_low_r[x] * (height-1))
            for y in range(intensity):
                bitmap[y*width_a+(x-block)] = chr(200)

        return bitmap


class ProbDensDisplay:
    def __init__(self, pa):
        self.tex_ids_l = []
        self.tex_ids_r = []
        self.pa = pa

    def draw(self, offset, scale, w_width, w_height, r, g, b, a=1.0):
        half_h = w_height/2.0
        t_width = self.pa.fftd.count
        glEnable(GL_TEXTURE_2D)
        glColor4f(r, g, b, a)

        tex_id_n = 0
        for block in range(0, t_width, 256):
            b_width = 256 if block+256 <= t_width else (t_width-block)
            b_width = (4-(b_width % 4))+b_width if b_width % 4 != 0 else b_width

            tex_offset = (float(block)/t_width)*(w_width*scale)
            tex_width = (float(b_width)/t_width)*(w_width*scale)

            if 0-tex_width < offset+tex_offset < w_width:
                Texture.draw_texture_block(half_h, half_h, tex_width, offset, tex_offset, self.tex_ids_l[tex_id_n])
                Texture.draw_texture_block(0, half_h, tex_width, offset, tex_offset, self.tex_ids_r[tex_id_n])

            tex_id_n += 1

        glDisable(GL_TEXTURE_2D)

    def create_tex(self):
        t_width, t_height = len(self.pa.fftd.fft_l), len(self.pa.fftd.fft_l[0])
        for block in range(0, t_width-1, 256):
            b_width = 256 if block+256 <= t_width else (t_width-block)
            b_width_a = (4-(b_width % 4))+b_width if b_width % 4 != 0 else b_width
            bitmap_l = self.bitmap_gen_l(block, b_width_a, b_width, t_height)
            bitmap_r = self.bitmap_gen_r(block, b_width_a, b_width, t_height)
            tex_id_l = Texture.upload_texture(b_width_a, t_height, bitmap_l)
            tex_id_r = Texture.upload_texture(b_width_a, t_height, bitmap_r)
            self.tex_ids_l += [tex_id_l]
            self.tex_ids_r += [tex_id_r]

    def recreate_tex(self):
        t_width, t_height = len(self.pa.fftd.fft_l), len(self.pa.fftd.fft_l[0])
        tex_id_n = 0
        for block in range(0, t_width-1, 256):
            b_width = 256 if block+256 <= t_width else (t_width-block)
            b_width_a = (4-(b_width % 4))+b_width if b_width % 4 != 0 else b_width
            bitmap_l = self.bitmap_gen_l(block, b_width_a, b_width, t_height)
            bitmap_r = self.bitmap_gen_l(block, b_width_a, b_width, t_height)
            Texture.update_texture(b_width_a, t_height, bitmap_l, self.tex_ids_l[tex_id_n])
            Texture.update_texture(b_width_a, t_height, bitmap_r, self.tex_ids_r[tex_id_n])
            tex_id_n += 1

    def bitmap_gen_l(self, block, width_a, width, height):
        bitmap = create_string_buffer(height*width_a)

        for x in range(block, block+width):
            i_scale = self.pa.pbd.densities[x][2]/self.pa.pbd.max
            node_y = (self.pa.pbd.densities[x][0]/(vaporw_compute.COMPUTE_SIZE/2.0))*height
            node_i = ((self.pa.pbd.densities[x][1]*i_scale)/(vaporw_compute.COMPUTE_SIZE/2.0))*height

            for y in range(int(node_y-node_i), int(node_y+node_i)):
                bitmap[y*width_a+(x-block)] = chr(200)

        return bitmap

    def bitmap_gen_r(self, block, width_a, width, height):
        bitmap = create_string_buffer(height*width_a)

        for x in range(block, block+width):
            i_scale = self.pa.pbd.densities[x][2]/self.pa.pbd.max
            node_y = (self.pa.pbd.densities[x][0]/(vaporw_compute.COMPUTE_SIZE/2.0))*height
            node_i = ((self.pa.pbd.densities[x][1]*i_scale)/(vaporw_compute.COMPUTE_SIZE/2.0))*height

            for y in range(int(node_y-node_i), int(node_y+node_i)):
                bitmap[y*width_a+(x-block)] = chr(200)

        return bitmap


class Display:
    in_audio = None
    out_audio = None
    marker_pos = 0
    playing = False

    fft_display = None
    its_display = None

    W_WIDTH = 600
    W_HEIGHT = 100

    scale = 1.0
    offset = 0
    view_grab = False
    view_grab_x = 0
    offset_temp = 0

    track = False

    survey_down = False
    survey_y = 0

    fft_overlay = True
    pdf_overlay = False
    its_overlay = False

    pa = vaporw_compute.ProcessedAudio

    def __init__(self, width, height, in_audio, out_audio):
        self.in_audio = in_audio
        self.out_audio = out_audio

        self.W_WIDTH = width
        self.W_HEIGHT = height

    def init(self):
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glColor3f(1.0, 1.0, 1.0)
        glLineWidth(2.0)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0.0, self.W_WIDTH, 0.0, self.W_HEIGHT)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        self.fft_display = FFTDisplay(self.pa)
        self.fft_display.create_tex()

        self.its_display = IntensityDisplay(self.pa)
        self.its_display.create_tex()

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
        if key == '0':
            self.fft_overlay = True if not self.fft_overlay else False
        # if key == '1':
        #    self.pdf_overlay = True if not self.pdf_overlay else False
        if key == '1':
            self.its_overlay = True if not self.its_overlay else False

    def motion(self, x, y):
        if self.view_grab:
            self.offset = self.offset_temp - (self.view_grab_x-x)
            self.offset = 0 if self.offset > 0 else self.offset

    def mouse(self, button, state, x, y):
        if button == GLUT_LEFT_BUTTON:
            if state == GLUT_DOWN:
                pos = (-self.offset+((float(x)/glutGet(GLUT_WINDOW_WIDTH))*self.W_WIDTH))/(self.W_WIDTH*self.scale)
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
                norm_loc = float(self.survey_y)/glutGet(GLUT_WINDOW_HEIGHT)
                norm_loc = (norm_loc*2.0)-1.0
                norm_loc = 1.0+norm_loc if norm_loc < 0 else norm_loc
                bin_loc = norm_loc*(vaporw_compute.COMPUTE_SIZE/2.0)
                print('%3.2f (%1.3f)' % (bin_loc, norm_loc))
            else:
                self.survey_down = False

    def mouse_wheel(self, wheel, direction, x, y):
        x = (float(x)/glutGet(GLUT_WINDOW_WIDTH))*self.W_WIDTH
        p_scale = self.scale
        self.scale *= (1.0+(direction/5.0))
        self.scale = numpy.clip(self.scale, 1.0, 100.0)
        i_scale = self.scale/p_scale

        self.offset -= ((x-self.offset)*i_scale)-(x-self.offset)
        self.offset = 0 if self.offset > 0 else self.offset

    def display(self):
        glClear(GL_COLOR_BUFFER_BIT)

        if self.fft_overlay:
            self.fft_display.draw(self.offset, self.scale, self.W_WIDTH, self.W_HEIGHT, 1, 1, 1)
        # if self.pdf_overlay:
        #    self.draw_tex(0, self.W_HEIGHT, self.pbd_tex, 1, 1, 1)
        if self.its_overlay:
            self.its_display.draw(self.offset, self.scale, self.W_WIDTH, self.W_HEIGHT, 1, 0, 1, 1, True, True)

        glColor3f(1.0, 1.0, 1.0)
        glBegin(GL_LINES)
        markerx = self.offset+(float(self.marker_pos)/self.pa.frames)*(self.W_WIDTH*self.scale)
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
        if self.playing:
            self.in_audio.setpos(self.marker_pos)
            data = self.in_audio.readframes(vaporw_compute.COMPUTE_SIZE)
            self.out_audio.write(data)
            self.marker_pos += vaporw_compute.COMPUTE_SIZE
            if self.marker_pos >= (self.pa.frames-vaporw_compute.COMPUTE_SIZE):
                self.marker_pos = 0
                self.playing = False

        if self.track:
            self.offset = (self.W_WIDTH/2) - (float(self.marker_pos)/self.pa.frames)*(self.W_WIDTH*self.scale)

        self.display()