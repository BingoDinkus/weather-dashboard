'''
    Derived from Display
    Responsible for handling interfacing with Waveshare ePaper displays
    Supported Models:
        epd7in5
        epd7in5_V2
'''

__author__ = 'Eric J. Harlan'
__license__ = "GPLv3"

from display_controller.display import *

import atexit
import importlib
import logging
import time

log = logging.getLogger(__name__)

# Dictionary with properties of supported display models
supported_models = {
    'epd7in5': {
        'width': 640,
        'height': 384,
        'driver_module': 'epd7in5'
    },
    'epd7in5_v2': {
        'width': 800,
        'height': 480,
        'driver_module': 'epd7in5_V2'
    }
}

class Waveshare_ePaper(Display):
    def __init__(self, model, debug_mode):
        model = model.casefold()

        if model not in supported_models:
            log.exception(f'{model} is not a supported display model')
            raise NotImplementedError(f'{model} is not a supported display model')

        super().__init__(
            brand= 'Waveshare',
            model= model,
            display_type= 'ePaper',
            width= supported_models[model]['width'],
            height= supported_models[model]['height'],
            debug_mode= debug_mode
        )

        if not debug_mode:
            # self.driver_module = importlib.import_module(f'display_controller.waveshare.{supported_models[model]["driver_module"]}')
            atexit.register(self.cleanup)

    def display_image(self, image, sleep_display=True):

        if self.debug_mode:
            log.info('debug_mode = True, display will not be updated.')
        else:
            log.info('Pushing image to display...')

            log.info('Initializing screen...')
            self.epd = self.driver_module.EPD()
            self.epd.init()
            self.epd.Clear()

            self.epd.display(self.epd.getbuffer(image))
            time.sleep(2)

            if sleep_display:
                log.info('Putting display to sleep')
                self.epd.sleep()

    def clear(self):
        if self.debug_mode:
            log.info('debug_mode = True, display will not be cleared.')
        else:
            self.epd.init()
            self.epd.Clear()
            self.epd.sleep()

    def cleanup(self):
        if self.debug_mode:
            log.info('debug_mode = True, clean-up not needed.')
        else:
            log.info('Running clean-up function')
            driver_module = importlib.import_module(f'display_controller.waveshare.{supported_models[model]["driver_module"]}')
            driver_module.epdconfig.module_exit(cleanup=True)