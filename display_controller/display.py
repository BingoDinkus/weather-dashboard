'''
    A simple class to abstract out screen commands,
    making it easier to control different screen models
'''

__author__ = 'Eric J. Harlan'
__license__ = "GPLv3"

from abc import ABC, abstractmethod
import logging

log = logging.getLogger(__name__)

class Display(ABC):
    '''
        Base class for the display.
        Hardware specific classes inherit from this class.
    '''

    def __init__(self, brand, model, display_type, width, height, debug_mode=False):
        self.brand = brand
        self.model = model
        self.display_type = display_type
        self.width = width
        self.height = height

        self.debug_mode = debug_mode

    def __repr__(self):
        return (
            f'Display Brand: {self.brand}\n'
            f'Display Model: {self.model}\n'
            f'Display Type: {self.display_type}\n'
            f'Width: {self.width} px\n'
            f'Height: {self.height} px\n'
        )

    def __str__(self):
        if self.debug_mode:
            debug_str = 'in debug mode and will not actually draw to the display.'
        else:
            debug_str = 'not in debug mode and will draw to the display.'

        return (
            f'The display is a {self.brand} {self.model} ({self.width}×{self.height}) {self.display_type} display. '
            f'It is currently {debug_str}'
        )

    @abstractmethod
    def display_image(self, image):
        ''' To be implemented by derived class '''
        pass

    @abstractmethod
    def clear(self):
        ''' To be implemented by derived class '''
        pass