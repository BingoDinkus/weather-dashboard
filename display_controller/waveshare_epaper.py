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

    def display_image(self, image, sleep_display=True):
        if self.debug_mode:
            log.info('debug_mode = True, display will not be updated.')
        else:
            try:
                log.info('Pushing image to display...')

                log.info('Initializing screen...')
                driver_module = importlib.import_module(self.driver_module_name)
                epd = driver_module.EPD()
                epd.init()
                epd.Clear()

                epd.display(epd.getbuffer(image))
                time.sleep(2)
            except KeyboardInterrupt:
                log.info('Keyboard interrupt detected, exiting.')
                driver_module.epdconfig.module_exit(cleanup=True)
            except Exception as e:
                log.exception('Exception thrown when displaying image.')
            finally:
                if sleep_display:
                    log.info('Putting display to sleep')
                    epd.sleep()

    def clear(self):
        if self.debug_mode:
            log.info('debug_mode = True, display will not be cleared.')
        else:
            driver_module = importlib.import_module(self.driver_module_name)
            epd = driver_module.EPD()

            epd.init()
            epd.Clear()
            epd.sleep()
