from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import colorsys

import vaporw_compute


class Display:
    W_WIDTH = 600
    W_HEIGHT = 100

    display_pa = vaporw_compute.ProcessedAudio

    def __init__(self, width, height):
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
        glutDisplayFunc(self.display)
        glutIdleFunc(self.display)
        self.init()
        glutMainLoop()

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
        sortedkeys = self.display_pa.pbd.densities.keys()
        sortedkeys.sort()
        for key in sortedkeys:
            display_intensity = self.display_pa.pbd.densities[key][1]/2.0
            # glVertex2f((float(key)/self.display_pa.frames)*self.W_WIDTH, bottom+(self.display_pa.pbd.densities[key][0]/512.0)+display_intensity)
            # glVertex2f((float(key)/self.display_pa.frames)*self.W_WIDTH, bottom+(self.display_pa.pbd.densities[key][0]/512.0)+display_intensity)
            glVertex2f((float(key)/self.display_pa.frames)*self.W_WIDTH, bottom+((self.display_pa.pbd.densities[key][0]/513.0)*height)+display_intensity*10)
            glVertex2f((float(key)/self.display_pa.frames)*self.W_WIDTH, bottom+((self.display_pa.pbd.densities[key][0]/513.0)*height)-display_intensity*10)
        glEnd()
        glDisable(GL_DEPTH_TEST)

    def display(self):
        glClear(GL_COLOR_BUFFER_BIT)
        self.draw_wfd(self.W_HEIGHT-(self.W_HEIGHT/2.0), self.W_HEIGHT/2.0)
        self.draw_pbd(0, self.W_HEIGHT/2.0)
        glFlush()
