import time
from wave_share import epd7in5_V2

epd = epd7in5_V2.EPD()
epd.init()
epd.Clear()
epd.sleep()