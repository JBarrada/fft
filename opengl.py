from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import colorsys
import math
import numpy
from operator import itemgetter

W_WIDTH = 300
W_HEIGHT = 600

fft_data = []
peaks = []
avg = 0

main_color = (0, 0, 0)


def init():
    glClearColor(0.0, 0.0, 0.0, 0.0)
    glColor3f(1.0, 1.0, 1.0)
    glPointSize(4.0)
    glLineWidth(6.0)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0.0, W_WIDTH, 0.0, W_HEIGHT)


def draw_marker(pos, (r, g, b), width):
    glColor3f(r, g, b)
    ys = numpy.logspace(math.log10(W_HEIGHT), 0, len(fft_data))

    a = width*float(W_WIDTH/4)*2
    glVertex2f(W_WIDTH/2 + a, W_HEIGHT - ys[pos])
    glVertex2f(W_WIDTH/2 - a, W_HEIGHT - ys[pos])


def draw_text(x, y, text):
    glRasterPos2f(x, y)
    glutBitmapString(GLUT_BITMAP_9_BY_15, text)


def similar_peaks_sum(pos):
    global peaks, fft_data
    count = 0.0
    for pos_p, sustain, p_avg in peaks:
        if (pos - 10) > pos_p < (pos + 10):
            count += fft_data[pos_p]
    return count


def display():
    global fft_data, avg, main_color
    glClear(GL_COLOR_BUFFER_BIT)

    # glColor3f(main_color[0]/1, main_color[1]/1, main_color[2]/1)
    # glRectf(0, 0, 300, 600)

    if len(fft_data):
        glLineWidth(4.0)
        glBegin(GL_LINES)
        glColor3f(main_color[0]/10, main_color[1]/10, main_color[2]/10)
        glVertex2f((W_WIDTH/2.0) + avg*float(W_WIDTH/4), 0)
        glVertex2f((W_WIDTH/2.0) + avg*float(W_WIDTH/4), W_HEIGHT)
        glVertex2f((W_WIDTH/2.0) - avg*float(W_WIDTH/4), 0)
        glVertex2f((W_WIDTH/2.0) - avg*float(W_WIDTH/4), W_HEIGHT)

        # glColor3f(0.0, 0.0, 0.0)
        # ys = numpy.logspace(math.log10(W_HEIGHT), 0, len(fft_data))
        # for sample in range(len(fft_data)-1):
        #     x1 = fft_data[sample]*float(W_WIDTH/4)
        #     y1 = W_HEIGHT - ys[sample]
        #     x2 = fft_data[sample+1]*float(W_WIDTH/4)
        #     y2 = W_HEIGHT - ys[sample+1]
        #     glVertex2f((W_WIDTH/2.0) + x1, y1)
        #     glVertex2f((W_WIDTH/2.0) + x2, y2)
        #     glVertex2f((W_WIDTH/2.0) - x1, y1)
        #     glVertex2f((W_WIDTH/2.0) - x2, y2)
        glEnd()

    if len(peaks):
        glLineWidth(40.0)
        glBegin(GL_LINES)
        try:
            max_sustain = max(peaks, key=itemgetter(1))[1]
        except Exception as e:
            pass

        most_sum = 1.0
        for pos, sustain, p_avg in peaks:
            sum_ = similar_peaks_sum(pos)
            if sum_ > most_sum:
                most_sum = sum_
                main_color = colorsys.hsv_to_rgb(sustain/float(max_sustain), 1.0, 1.0)

        for pos, sustain, p_avg in peaks:
            # sum_ = similar_peaks_sum(pos)
            draw_marker(pos, colorsys.hsv_to_rgb(sustain/float(max_sustain), 1.0, 1.0), p_avg)
        glEnd()

    if len(peaks):
        max_sustain = max(peaks, key=itemgetter(1))[1]
        draw_text(0, W_HEIGHT-15, str(max_sustain))
    glFlush()


def start_window():
    glutInit()
    glutInitWindowSize(W_WIDTH, W_HEIGHT)
    glutCreateWindow("!!!")
    glutInitDisplayMode(GLUT_SINGLE | GLUT_RGB)
    glutDisplayFunc(display)
    glutIdleFunc(display)
    init()
    glutMainLoop()
