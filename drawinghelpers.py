#!/usr/bin/env python3

'''
    Contains a helpder class and enums to make drawing text to the screen easier

    If DEBUG_BORDERS is True, the bounding box for each item will be drawn,
    to help debug object placement
'''

__author__ = 'Eric J. Harlan'
__license__ = "GPLv3"

from PIL import Image, ImageDraw, ImageFont
from enum import Enum

DEBUG_BORDERS = False

class VerticalAlignment(Enum):
    TOP = 1
    MIDDLE = 2
    BOTTOM = 3

class HorizontalAlignment(Enum):
    LEFT = 1
    CENTER = 2
    RIGHT = 3

class Text():
    '''
        Maintains PIL drawtext text and properties
    '''
    def __init__(self, canvas, text, font):
        self.canvas = canvas
        self.text = text
        self.font = font
        _, _, self.width, self.height = canvas.textbbox((0, 0), text, font= font)

    def coords(self):
        return (self.width, self.height)

    def write(self, start_coords
                        , end_coords=None
                        , h_align=HorizontalAlignment.LEFT
                        , v_align=VerticalAlignment.TOP
                        , fill=0):

        # Default drawing coordinates to start
        draw_x, draw_y = start_coords

        # Unpack coords
        start_x, start_y = start_coords

        if end_coords is None:
            end_x = start_x + self.width
            end_y = start_y + self.height
            end_coords = (end_x, end_y)
        else:
            end_x, end_y = end_coords

        # Ensure text fits
        # assert end_x - start_x >= self.width
        # assert end_y - start_y >= self.height

        # Determine drawing x coord
        if h_align == HorizontalAlignment.CENTER:
            draw_x = start_x + ((end_x - start_x - self.width) / 2)
        elif h_align == HorizontalAlignment.RIGHT:
            draw_x = end_x - self.width

        # Determine drawing y coord
        if v_align == VerticalAlignment.MIDDLE:
            draw_y = start_y + ((end_y - start_y - self.height) / 2)
        elif v_align == VerticalAlignment.BOTTOM:
            draw_y = end_y - self.height

        # Draw
        self.canvas.text((draw_x, draw_y)
            , self.text
            , font= self.font
            , fill= fill
        )

        # Debug Borders
        if DEBUG_BORDERS:
            self.canvas.rectangle((start_coords, end_coords), outline='black', fill=None)