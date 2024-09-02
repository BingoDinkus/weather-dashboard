#!/usr/bin/env python3

'''
    The core of the program
    Is responsible for creating forecast and calendar objects,
    refreshing items as needed, and redrawing the screen.
'''

__author__ = 'Eric J. Harlan'
__license__ = "GPLv3"

import dashboard

import logging
from logging.config import fileConfig
from pathlib import Path
import os

# Set working directory to script location
os.chdir(Path(__file__).resolve().parent)

# Create logs directory if it's missing
Path('logs/').mkdir(exist_ok=True)

# Set up logger
logging_config_path = Path('logging_config.ini')
fileConfig(logging_config_path, disable_existing_loggers=False)
log = logging.getLogger()

def main():
    log.info('Starting application...')

    app = dashboard.Dashboard()
    app.run()

    log.debug('Exiting application')

if __name__ == '__main__':
    try:
        main()
    except:
        log.exception('Exception caught at the top level')
        raise